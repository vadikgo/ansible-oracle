# Oracle for Ansible

This role downloads, installs and configures Oracle Database 11g Release 2 for
CentOS 6. The included tasks are a rough port of an internal shell script, which
was itself a rough port of Oracle's installation instructions and
recommendations.

## Requirements

- CentOS 6.7+
- Ansible 2.1
- Oracle Database 11gR2 [installation content](http://www.oracle.com/technetwork/database/enterprise-edition/downloads/112010-linx8664soft-100572.html)

## Variables

See the [default variables](defaults/main.yml), which are extensively
commented.

## Example

```
- hosts: oracle
  pre_tasks:
    - name: ensure packages required are installed
      yum: pkg={{item}} state=present
      with_items:
        - bc
        - libselinux-python
        - sudo
    - name: enable sudo tty
      lineinfile: dest=/etc/sudoers state=present regexp="^Defaults    requiretty$" line="Defaults    !requiretty"
    - name: Set /dev/shm size
      shell: mount -o remount,size=$(free -m|awk '/^Mem/ {print $2}')m /dev/shm
      when: ansible_connection != 'docker'
  roles:
    - ansible-oracle
  vars:
    oracle_path: /u01
    oracle_db_name: DB1
    oracle_db_home: oracle_db_home
    oracle_db_pass: OracleUs3r
    oracle_db_syspass: Oracle4dmin
    oracle_installer_uri: http://192.168.10.111:8000
    #oracle_installer_uri: http://10.21.25.212:8000/ora11204
    oracle_db_mem: 1024
    oracle_installer: [p13390677_112040_Linux-x86-64_1of7.zip, p13390677_112040_Linux-x86-64_2of7.zip]
    oracle_latest_patches:
        - { file_name: patch/p21948347_112040_Linux-x86-64.zip, number: "21948347" }
        - { file_name: patch/p21972320_112040_Linux-x86-64.zip, number: "21972320", apply: napply -skip_subset -skip_duplicate }
        - { file_name: patch/p22139245_112040_Linux-x86-64.zip, number: "22139245" }
    oracle_opatch: opatch/p6880880_112000_Linux-x86-64.zip
    oracle_opatch_version: 11.2.0.3.12
```

## TODO

 - fix TZ update
