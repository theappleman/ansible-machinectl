#!/bin/bash

hosts=$1
shift

playbook=$(mktemp -p .)
echo -e "---\n- hosts: $hosts\n  roles:" > $playbook
for role in $@; do echo "  - $role"; done >> $playbook
ansible-playbook -v $playbook
