#!/usr/bin/env python

from ansible.module_utils.basic import *
import subprocess as sp

class BtrFS():
    def __init__(self, module):
        self.module = module

    def _is_subv(self, path):
        try:
            sp.check_call(["btrfs", "subvolume", "show", path])
            return True
        except sp.CalledProcessError as e:
            self.module.fail_json(msg=e)
            return False

    def _create_subv(self, path):
        try:
            sp.check_call(["btrfs", "subvolume", "create", path])
            return True
        except sp.CalledProcessError:
            return False

    def _remove_subv(self, path):
        try:
            sp.check_call(["btrfs", "subvolume", "delete", path])
            return True
        except sp.CalledProcessError:
            return False


def main():
    module = AnsibleModule(
        argument_spec = dict(
            name    = dict(required=True, aliases=['path']),
            state   = dict(default="present", choices=['present', 'absent'], aliases=['ensure']),
        ),
        supports_check_mode=True
    )

    btrfs = BtrFS(module)

    if module.params['state'] == "present":
        if btrfs._is_subv(module.params['name']):
            module.exit_json()
        else:
            if module.check_mode:
                module.exit_json(changed=True)
            else:
                if btrfs._create_subv(module.params['name']):
                    module.exit_json(changed=True)
                else:
                    module.fail_json(msg="Not able to create subvolume {}".format(module.params['name']))
    elif module.params['state'] == "absent":
        if not btrfs._is_subv(module.params['name']):
            module.fail_json(msg="{} is not a subvolume".format(module.params['name']), changed=False)
        else:
            if module.check_mode:
                module.exit_json(changed=True)
            else:
                if btrfs._remove_subv(module.params['name']):
                    module.exit_json(changed=True)
                else:
                    module.fail_json(msg="Not able to remove subvolume {}".format(module.params['name']))

    module.fail_json(msg="Unknown state parameter: {}".format(module.params['state']))

    #if module.check_mode:
    #    module.exit_json(changed=False)

    #path_subvols = sp.check_output(["btrfs", "subv", "list", module.params['name']])
    #path_split = [i.split(" ") for i in path_subvols.split("\n")]

    #module.exit_json(subvols=path_subvols, split=path_split)


if __name__ == '__main__':
    main()
