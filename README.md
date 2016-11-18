# Oracle for Ansible

This role downloads, installs and configures Oracle Database 11/12 for
CentOS 6/7. The included tasks are a rough port of an internal shell script, which
was itself a rough port of Oracle's installation instructions and
recommendations.

## Requirements

- CentOS 6/7
- Ansible 2.2
- Oracle Database 11/12

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
    oracle_installer_uri: http://10.21.25.212/ora11204
    oracle_db_mem: 1024
    oracle_installer: [p13390677_112040_Linux-x86-64_1of7.zip, p13390677_112040_Linux-x86-64_2of7.zip]
    oracle_latest_patches:
        - { file_name: patch/p21948347_112040_Linux-x86-64.zip, number: "21948347" }
        - { file_name: patch/p21972320_112040_Linux-x86-64.zip, number: "21972320", apply: napply -skip_subset -skip_duplicate }
        - { file_name: patch/p22139245_112040_Linux-x86-64.zip, number: "22139245" }
        - { file_name: patch/p22037014_112040_Linux-x86-64.zip, number: "22037014" } # DST25
    oracle_opatch: opatch/p6880880_112000_Linux-x86-64.zip
    oracle_opatch_version: 11.2.0.3.12
```

# Контейнеры Docker

Gitlab CI создает образы **oracledb:11.2** и **oracledb:12.1**. Это предустановленный Oracle без создания БД.

БД создается при старте контейнера, например:
```
docker run -t --privileged --shm-size 1GB --name oracle11 -h oracle11 oracledb:11.2
```

По-умолчанию имя создаваемой БД "db", пароль sysdba - "Oracle4dmin".

При помощи переменных ORACLE_SID и ORACLE_SYSPASS можно задать имя создаваемой БД и пароль sysdba:
```
docker run -t --privileged --shm-size 1GB --name oracle11 -h oracle11 -e "ORACLE_SID=DB1" -e "ORACLE_SYSPASS=TopSecret123" oracledb:11.2
```

Если задать специальную переменную ORACLE_STOP, с непустым значением, то после создания БД сервер будет остановлен и контейнер остановится. Это необходимо, например, для дальнейшего сохранения состояния контейнера.
```
docker run -t --privileged --shm-size 1GB --name oracle11 -h oracle11 -e "ORACLE_STOP=yes" oracledb:11.2
```

Так-же, Gitlab CI создает контейнеры с уже созданной БД "db" и паролем sysdba "Oracle4dmin". Для запуска можно выполнить команды:

```
docker run --privileged --shm-size 1GB  -it oracledb_db:11.2 bash
docker run --privileged --shm-size 1GB  -it oracledb_db:12.1 bash
```
