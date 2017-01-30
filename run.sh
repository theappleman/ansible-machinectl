#!/bin/bash

while getopts c:e:vKs opt; do
	case $opt in
	e)	exargs="$exargs -e $OPTARG"
		;;
	c)	transport="-c $OPTARG"
		;;
	K|s|v)	exargs="$exargs -$opt"
		;;
	esac
done

shift $((OPTIND-1))
hosts=$1
shift

playbook=$(mktemp -p .)
echo -e "---\n- hosts: $hosts\n  roles:" > $playbook
for role in $@; do echo "  - $role"; done >> $playbook
ansible-playbook $exargs $transport $playbook
rm "$playbook"
