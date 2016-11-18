#!/bin/sh
# {{ ansible_managed }}
# ORACLE_SID - define custom database name
# ORACLE_SYSPASS - define custom sys password
# ORACLE_STOP - stop Oracle after create DB (for safe docker commit)

set -e

DB_NAME=${ORACLE_SID:-{{oracle_db_name}}}

sysctl -p || echo pass

echo "$(ip -f inet addr show eth0 |grep -Po 'inet \K[\d.]+') oracle" >> /etc/hosts

if [ -e {{ ora_user_env.ORACLE_BASE }}/oradata/${DB_NAME} ]; then
  /etc/init.d/oracle start
else
  cd /tmp/ansible-oracle/tests
  ansible-playbook test_oracle_install-{{oracle_version}}.yml -e "oracle_install_db=False oracle_install_time_update=True oracle_create_dbca=True oracle_db_name=$DB_NAME ${ORACLE_SYSPASS:+oracle_db_syspass=$ORACLE_SYSPASS}"
  if [ -n "${ORACLE_STOP}" ]; then
    /etc/init.d/oracle stop
    exit 0
  fi
fi

if [ $# == 0 ]; then
  tail -f {{oracle_path}}/oracle/diag/rdbms/${DB_NAME,,}/${DB_NAME}/trace/alert_${DB_NAME}.log
else
  exec "$@"
fi
