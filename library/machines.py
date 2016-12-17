#!/usr/bin/env python

from ansible.module_utils.basic import *
import subprocess as sp
import os

class Machine():
    def __init__(self, module):
        self.module = module

    def _is_present(self, name):
        try:
            output = sp.check_output(["machinectl", "list-images", "--no-legend"])
            for line in output.split("\n"):
                words = line.split(" ")
                if name == words[0]:
                    return True
            return False
        except sp.CalledProcessError:
            return False

    def _is_pkg_installed(self):
        # This is a little backwards...
        os.environ['ROOT'] = os.path.join("/","var", "lib", "machines", self.module.params['name'])
        import portage
        if portage.db[portage.root]['vartree'].dbapi.match(self.module.params['pkg']) == []:
            return False
        else:
            return True

    def _is_running(self, name):
        try:
            sp.check_output(["machinectl", "show", name])
            return True
        except sp.CalledProcessError:
            return False

    def start(self):
        try:
            sp.check_output(["machinectl", "start", self.module.params['name']])
            return True
        except sp.CalledProcessError:
            return False

    def poweroff(self):
        try:
            sp.check_output(["machinectl", "poweroff", self.module.params['name']])
            return True
        except sp.CalledProcessError:
            return False

    def terminate(self):
        try:
            sp.check_output(["machinectl", "terminate", self.module.params['name']])
            return True
        except sp.CalledProcessError:
            return False

    def clone(self):
        try:
            sp.check_output([
                "machinectl",
                "clone",
                self.module.params['source'],
                self.module.params['name']
            ])
            sp.check_output([
                "systemd-machine-id-setup",
                "--root",
                os.path.join(
                    "/",
                    "var",
                    "lib",
                    "machines",
                    self.module.params['name']
                )
            ])
            return True
        except sp.CalledProcessError:
            return False

    def remove(self):
        try:
            sp.check_output(["machinectl", "remove", self.module.params['name']])
            return True
        except sp.CalledProcessError:
            return False

    def install(self):
        if self._is_pkg_installed():
            self.changed = False
            self.output = ""
            return True
        else:
            try:
                self.output = sp.check_output(["systemd-run", "--service-type=oneshot", "-M", self.module.params['name'], "/usr/bin/emerge", "-u", self.module.params['pkg'] ], stderr=sp.STDOUT)
                self.changed = True
                return True
            except sp.CalledProcessError as e:
                self.output = e.output
                self.changed = True
                return False

    def run(self):
        try:
            cmd = ["systemd-run", "--service-type=oneshot", "-M", self.module.params['name']]
            [cmd.append(word) for word in self.module.params['cmd'].split(" ")]
            self.output = sp.check_output(cmd, stderr=sp.STDOUT)
            return True
        except sp.CalledProcessError as e:
            self.output = e.output
            return False

def main():
    module = AnsibleModule(
        argument_spec = dict(
            name    = dict(required=True),
            mode    = dict(default="container", choices=["pkg","container","exec", "run"]),
            state   = dict(default="present", choices=['present', 'running', 'absent', 'stopped', 'terminated'], aliases=['ensure']),
            source  = dict(required=False, aliases=['clone']),
            pkg     = dict(required=False),
            cmd     = dict(required=False),
        ),
        supports_check_mode=True
    )

    machine = Machine(module)

    if module.params['mode'] == "container":
        if module.params['state'] == "present":
            if machine._is_present(module.params['name']):
                module.exit_json()
            elif module.check_mode:
                    module.exit_json(msg="Container {} needs to be created".format(module.params['name']),changed=True)
            elif module.params['source']:
                if machine.clone():
                    module.exit_json(changed=True, msg="Container {} created from {}".format(module.params['name'], module.params['source']))
                else:
                    module.fail_json(msg="Container {} could not be created".format(module.params['name']))
            else:
                module.fail_json(msg="Container {} needs to be created".format(module.params['name']),changed=True)

        elif module.params['state'] == "running":
            if machine._is_running(module.params['name']):
                module.exit_json(changed=False)
            elif module.check_mode:
                module.exit_json(changed=True)
            elif machine.start():
                module.exit_json(changed=True)
            else:
                module.fail_json(changed=False, msg="Could not start container {}".format(module.params['name']))

        elif module.params['state'] == "stopped":
            if machine._is_running(module.params['name']):
                if module.check_mode:
                    module.exit_json(changed=True)
                elif machine.poweroff():
                    module.exit_json(changed=True)
                else:
                    module.fail_json(changed=False, msg="Could not poweroff container {}".format(module.params['name']))
            else:
                module.exit_json(changed=False)

        elif module.params['state'] == "terminated":
            if machine._is_running(module.params['name']):
                if module.check_mode:
                    module.exit_json(changed=True)
                elif machine.terminate():
                    module.exit_json(changed=True)
                else:
                    module.fail_json(changed=False, msg="Could not terminate container {}".format(module.params['name']))
            else:
                module.exit_json(changed=False)

        elif module.params['state'] == "absent":
            if machine._is_present(module.params['name']):
                if module.check_mode:
                    module.exit_json(changed=True)
                elif machine.remove():
                    module.exit_json(changed=True)
                else:
                    module.fail_json(msg="Could not remove container {}".format(module.params['name']))
            else:
                module.exit_json(changed=False)

    elif module.params['mode'] == "pkg":
        if module.check_mode:
            if machine._is_pkg_installed():
                module.exit_json(msg="Package {} is installed in container {}".format(module.params['pkg'],module.params['name']))
            else:
                module.fail_json(msg="Package {} is not installed in container {}".format(module.params['pkg'],module.params['name']))
        elif machine.install():
            module.exit_json(msg="Package {} installed in {}".format(module.params['pkg'],module.params['name']), output=machine.output, changed=machine.changed)
        else:
            module.fail_json(msg="Error installing package {} in {}".format(module.params['pkg'],module.params['name']), output=machine.output)

        module.fail_json(msg="Unknown state option: {}".format(module.params['state']))

    elif module.params['mode'] == "run":
        if module.check_mode:
            module.fail_json(msg="not implemented")
        elif machine.run():
            module.exit_json(msg="Command run container {} successful: {}".format(module.params['name'], module.params['cmd']), output=machine.output)
        else:
            module.fail_json(msg="Command run in container {} unsuccessful: {}".format(module.params['name'],module.params['cmd']), output=machine.output)

        module.fail_json(msg="Unknown state option: {}".format(module.params['state']))



    module.fail_json(msg="Unknown mode option: {}".format(module.params['mode']))

if __name__ == '__main__':
    main()
