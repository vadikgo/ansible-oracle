    #!/usr/bin/python
# -*- coding: utf-8 -*-
import requests
import os
import time
import paramiko
import socket

try:
    import json
except ImportError:
    import simplejson as json

DOCUMENTATION = '''
---
module: sbt_os_server
short_description: Create/Delete server in SBT Openstack
description:
    - Create/Delete server in SBT Openstack
options:
    vmname:
        description:
            - server name
        required: true
        default: null
    state:
        description:
            - Server state present (default) / absent
        required: false
        choices: [ "present", "absent" ]
        default: "present"
    username:
        description:
            - username for the module to use auth
        required: false
        default: null
    password:
        description:
            - password for the module to use auth
        required: false
        default: null
    validate_certs:
        description:
          - If C(no), SSL certificates will not be validated.  This should only
            set to C(no) used on personally controlled sites using self-signed
            certificates.
        required: false
        default: 'no'
        choices: ['yes', 'no']
'''
EXAMPLES = '''
- name: Start server in sbt openstack
  sbt_os_server:
    vmname: ansible_vm1
    state: present
    project_name: "CI_test"
    username: "{{lookup('env','OS_USERNAME')}}"
    password: "{{lookup('env','OS_PASSWORD')}}"
    image_name: RHEL-6.7.qcow2
    flavor_name: m8.tiny
    keyname: Jenkins190
    validate_certs: no
'''

def main():
    module = AnsibleModule(
        argument_spec=dict(
            vmname = dict(required=True),
            state = dict(required=False, choices=['present', 'absent'], default='present'),
            username = dict(required=False, default=os.getenv('OS_USERNAME')),
            password = dict(required=False, default=os.getenv('OS_PASSWORD')),
            domain = dict(required=False, default='sberbank'),
            project_name = dict(required=False, default='CI_test'),
            keyname = dict(required=False, default=None),
            network_name = dict(required=False, default='instance-net'),
            image_name = dict(required=False, default='RHEL-6.7'),
            flavor_name = dict(required=False, default='m8.tiny'),
            auth_url = dict(required=False, default="https://mos-mc-4-1-13j.ca.sbrf.ru:5000/v3/auth/tokens"),
            nova_url = dict(required=False, default="https://mos-mc-4-1-13j.ca.sbrf.ru:8774/v2"),
            glance_url = dict(required=False, default="https://mos-mc-4-1-13j.ca.sbrf.ru:9292/v2"),
            neutron_url = dict(required=False, default="https://mos-mc-4-1-13j.ca.sbrf.ru:9696/v2.0/networks"),
            validate_certs = dict(required=False, default=True, type='bool'),
            wait_ssh = dict(required=False, default=True, type='bool')
        ),
        supports_check_mode=False
    )

    vmname = module.params["vmname"]
    state = module.params["state"]
    username = module.params["username"]
    password = module.params["password"]
    domain = module.params["domain"]
    project_name = module.params["project_name"]
    keyname = module.params["keyname"]
    network_name = module.params["network_name"]
    image_name = module.params["image_name"]
    flavor_name = module.params["flavor_name"]
    auth_url = module.params["auth_url"]
    nova_url = module.params["nova_url"]
    glance_url = module.params["glance_url"]
    neutron_url = module.params["neutron_url"]
    validate_certs = module.params["validate_certs"]
    wait_ssh = module.params["wait_ssh"]

    auth_payload =   { "auth": {
                  "identity": {
                    "methods": ["password"],
                    "password": {
                      "user": {
                        "name": username,
                        "domain": { "name": domain },
                        "password": password
                      }
                    }
                  },
                  "scope": {
                    "project": {
                      "name": project_name,
                      "domain": { "name": domain }
                    }
                  }
                }
                }

    # get token
    r = requests.post(auth_url, data=json.dumps(auth_payload),   headers={'Content-Type': 'application/json'},
                verify=validate_certs)
    if r.status_code != 201:
        module.fail_json(changed=True, msg="Fail to get auth token with error code {0}".format(r.status_code))

    project_id = r.json()['token']['project']['id']
    token = r.headers['X-Subject-Token']

    auth_headers = {'Content-Type': 'application/json',
                'Accept': 'application/json',
                'X-Auth-Project-Id': project_name,
                'X-Auth-Token': token}
    def get_id_by_name(url, name_list, name, id='id'):
        r = requests.get(url, headers=auth_headers, verify=validate_certs)
        objects_ids = [obj[id] for obj in r.json()[name_list] if obj['name'] == name]
        return None if objects_ids == [] else objects_ids[0]

    #print json.dumps(r.json(), sort_keys=True, indent=4)

    server_id = get_id_by_name("{0}/{1}/servers".format(nova_url,project_id), 'servers', vmname)

    if state.lower() == 'absent':
        # delete server
        if server_id != None:
            r = requests.delete("{0}/{1}/servers/{2}".format(nova_url, project_id, server_id),
                        headers=auth_headers, verify=validate_certs)
            if r.status_code != 204:
                module.fail_json(changed=True, msg="Fail to delete server {0} with error code {1}".format(vmname, r.status_code))
            module.exit_json(changed=True, msg="Server %s deleted" % vmname)
        module.exit_json(changed=False, msg="Server %s does not exist" % vmname)

    image_ref = get_id_by_name("{0}/images".format(glance_url), 'images', image_name)
    if image_ref == None:
        module.fail_json(changed=True, msg="Image name %s not found" % image_name)

    flavor_ref = get_id_by_name("{0}/{1}/flavors".format(nova_url, project_id), 'flavors', flavor_name)
    if flavor_ref == None:
        module.fail_json(changed=True, msg="Flavor name %s not found" % flavor_name)

    network_uuid = get_id_by_name(neutron_url, 'networks', network_name)
    if network_uuid == None:
        module.fail_json(changed=True, msg="Network name %s not found" % network_name)


    admin_pass = ''
    changed = False
    if server_id == None:
        # create server
        server_payload = {"server":
                      {"name": vmname,
                       "imageRef": image_ref,
                       "flavorRef": flavor_ref,
                       "max_count": 1,
                       "min_count": 1,
                       "networks": [{"uuid": network_uuid}]
                      }
                    }
        if keyname != None:
            server_payload['server']["key_name"] = keyname
        # start server and get it's id
        r = requests.post("{0}/{1}/servers".format(nova_url,project_id),
                    data=json.dumps(server_payload), headers=auth_headers, verify=validate_certs)
        if r.status_code != 202:
            module.fail_json(changed=True, msg="Fail to start server {0} with error code {1}".format(vmname, r.status_code))
        server_id = r.json()['server']['id']
        admin_pass = r.json()['server']['adminPass']
        changed = True

    #print "wait until server started"
    for i in range(60):
        r = requests.get("{0}/{1}/servers/{2}".format(nova_url, project_id, server_id),
                    headers=auth_headers, verify=validate_certs)
        if r.json()['server']['status'] == 'ACTIVE':
            server_ip_addr = r.json()['server']['addresses'][network_name][0]['addr']
            if wait_ssh:
                #print "wait until accessible by ssh"
                for j in range(60):
                    try:
                        paramiko.client.SSHClient().connect(server_ip_addr, look_for_keys=False)
                    except socket.error:
                        time.sleep(10)
                        continue
                    except paramiko.ssh_exception.SSHException:
                        # Server not found in known_hosts
                        print "add to inventory"
                        # exit on success
                        pass
                    #print "ssh works!"
                    module.exit_json(changed=changed, msg="Server started with ssh", ip_address=server_ip_addr, admin_pass=admin_pass, hostname=vmname)
                module.fail_json(msg="SSH not accessible", ip_address=server_ip_addr, admin_pass=admin_pass)
            module.exit_json(changed=changed, msg="Server started", ip_address=server_ip_addr,
                            admin_pass=admin_pass, hostname=vmname)
        time.sleep(10)
    module.fail_json(msg="Server startup timeout", ip_address=server_ip_addr, admin_pass=admin_pass)

from ansible.module_utils.basic import *
from ansible.module_utils.urls import *
if __name__ == "__main__":
    main()
