# -*- coding: utf-8 -*-
""" ymir._ansible

    Defines a ansible mixin for the base ymir service service class
"""
import os
import json

from fabric import api
from fabric.colors import yellow

from ymir import util

ANSIBLE_CMD = (
    'ansible all {debug} -u {user} '
    '--private-key "{pem}" '
    '-e "host_key_checking=False," '
    '--ssh-extra-args "-p {port}" '
    '--sftp-extra-args "-P {port}" '
    '-i {inventory} '
    '-M "{module_path}" {command}')

ANSIBLE_PLAYBOOK_CMD = (
    'ansible-playbook {debug} -u {user} '
    '--private-key "{pem}" '
    '-e "host_key_checking=False," '
    '--ssh-extra-args "-p {port}" '
    '--sftp-extra-args "-P {port}" '
    '-i {inventory} '
    '-M "{module_path}" {command}')

ANSIBLE_GALAXY_CMD = (
    'ansible-galaxy install '
    '-p {role_dir} '
    '-r {reqs_file}')


class AnsibleMixin(object):

    """ """

    @util.declare_operation
    def ansible_inventory(self):
        """ display the inventory for use with ansible """
        data = self.template_data()
        print json.dumps({
            data['name']: dict(
                hosts=[data['host']],
                vars=self.facts)})

    @property
    def _ansible_dir(self):
        """ """
        return os.path.join(
            self._ymir_service_root, 'ansible')

    @property
    def _ansible_roles_dir(self):
        """ """
        role_dir = os.path.join(self._ansible_dir, 'roles')
        return role_dir

    def _setup_ansible_requirements(self):
        """ during setup, stuff from ansible-galaxy will be
            fetched if there exists a requirements file
            at <service_root>/ansible/requirements.yml
        """
        reqs_file = self._ansible_requirements_file
        if reqs_file is None:
            self.report("no ansible requirements found, nothing to refresh")
            return
        self.report("refreshing local ansible requirements:")
        self.report("  {0}".format(
            yellow(util.unexpand(reqs_file))))
        with api.lcd(self._ansible_dir):
            api.local(ANSIBLE_GALAXY_CMD.format(
                reqs_file=reqs_file,
                role_dir=self._ansible_roles_dir))

    @property
    def _ansible_requirements_file(self):
        """ """
        simple_reqs = os.path.join(
            self._ansible_dir,
            'requirements.txt')
        simple_reqs = simple_reqs if os.path.exists(simple_reqs) else None
        yaml_reqs = os.path.join(
            self._ansible_dir,
            'requirements.yml')
        yaml_reqs = yaml_reqs if os.path.exists(yaml_reqs) else None
        return simple_reqs or yaml_reqs or None

    @property
    def _ansible_debug(self):
        """ debug flags used with ansible are
            tied to the main `ymir_debug` entry
            in service.json files
        """
        debug = '-vvvv' if self._debug_mode else ''
        return debug

    @property
    def _ansible_inventory_script(self):
        """ """
        return os.path.join(
            self._ansible_dir, 'ymir_inventory.py')

    @property
    def _ansible_env(self):
        """ common vars used for ansible, ansible-galaxy, and
            ansible-playbook invocation
        """
        return dict(
            port=self._port, user=self._username, pem=self._pem,
            debug=self._ansible_debug,
            inventory=util.unexpand(self._ansible_inventory_script),
            module_path=util.unexpand(self._ansible_dir))

    def _ansible_ctx(self):
        """ context manager for all ansible invocations.
            namely the inventory script must be invoked with the
            same service-json as ymir is using, otherwise the
            ansible dynamic inventory will be incorrect
        """
        return api.shell_env(YMIR_SERVICE_JSON=self.service_json_file)

    def _provision_ansible(self, cmd):
        """ handler for provision-list entries prefixed with `ansible://` """
        with self._ansible_ctx():
            api.local(ANSIBLE_CMD.format(command=cmd, **self.ansible_env))

    def _provision_ansible_playbook(self, cmd):
        """ handler for provision-list entries prefixed with
            `ansible_playbook://` or `ansible-playbook://`
        """
        with self._ansible_ctx():
            api.local(ANSIBLE_PLAYBOOK_CMD.format(
                command=cmd, **self._ansible_env))
