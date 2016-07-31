# -*- coding: utf-8 -*-
""" ymir._ansible

    Defines a ansible mixin for the base ymir service service class
"""
import os
import json

from fabric import api
from fabric.colors import yellow
from peak.util.imports import lazyModule
from ymir import util
from ymir import data as ydata

yapi = lazyModule('ymir.api')

ANSIBLE_BASE_ARGS = (
    '{debug} -u {user} '
    '--private-key "{pem}" '
    # '--extra-vars "host_key_checking=False," '
    '--ssh-extra-args "-p {port}" '
    '--sftp-extra-args "-P {port}" '
    '--inventory-file {inventory} '
    '--module-path "{module_path}" '
)
ANSIBLE_CMD = ('ansible all ' + ANSIBLE_BASE_ARGS + ' {command}')

# requires ansible-role from pypi, but this is guaranteed
# to be installed because it is listed in ymir's setup.py
ANSIBLE_ROLE_CMD = ('ansible-role {role_name} all ' + ANSIBLE_BASE_ARGS)

ANSIBLE_PLAYBOOK_CMD = ('ansible-playbook ' + ANSIBLE_BASE_ARGS + '{command}')

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
        ansible_dir = os.path.join(
            self._ymir_service_root, 'ansible')
        if not os.path.exists(ansible_dir):
            api.local("mkdir -p {0}".format(ansible_dir))
        return ansible_dir

    @property
    def _ansible_roles_dir(self):
        """ """
        role_dir = os.path.join(self._ansible_dir, 'roles')
        if not os.path.exists(role_dir):
            api.local('mkdir -p {0}'.format(role_dir))
        return role_dir

    def _require_role(self, role_name):
        """ """
        return util._ansible.require_ansible_role(
            role_name,
            self._ansible_roles_dir, report=self.report
        )

    def _provision_ansible_role(self, role_name):
        """ this provisioner applies a single ansible role.  this is more
            complicated than it sounds because there's no way to do this
            without a playbook, and so a temporary playbook is created just
            for this purpose.

            To pass ansible variables through to the role, you can use kwargs
            to this function.

            see also:
              https://groups.google.com/forum/#!topic/ansible-project/h-SGLuPDRrs
        """
        return self._apply_ansible_role(role_name)

    def _apply_ansible_role(self, role_name, **env):
        """ """
        with self._ansible_ctx():
            result = api.local(
                ANSIBLE_ROLE_CMD.format(
                    role_name=role_name,
                    role_env=json.dumps(env),
                    **self._ansible_env))
            return result.succeeded

    @util.declare_operation
    def setup_ansible(self):
        """ refreshes (local) ansible roles from ansible/requirements.yml """
        reqs_file = self._ansible_requirements_file
        if reqs_file is None:
            msg = "no ansible requirements found, nothing to refresh"
            self.report(ydata.FAIL + msg)
            return
        self.report("refreshing local ansible requirements:")
        self.report("  requirements: {0}".format(
            yellow(util.unexpand(reqs_file))))
        self.report("  role-dir: {0}".format(
            yellow(util.unexpand(self._ansible_roles_dir))))
        with api.settings(api.hide('everything')):
            with api.lcd(self._ansible_dir):
                result = api.local(ANSIBLE_GALAXY_CMD.format(
                    reqs_file=reqs_file,
                    role_dir=self._ansible_roles_dir))
                if result.succeeded:
                    self.report(
                        ydata.SUCCESS + "ansible-galaxy requirements up to date")

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
        debug = '-vvv' if self._debug_mode else ''
        return debug

    @property
    def _ansible_inventory_script(self):
        """ """
        script = os.path.join(
            self._ansible_dir, 'ymir_inventory.py')
        if not os.path.exists(script):
            # this can happen if ymir directory structure
            # was not created with `ymir init`
            script = os.path.join(
                ydata.SKELETON_DIR,
                'ansible',
                'ymir_inventory.py')
            if not os.path.exists(script):
                # should never happen
                err = 'Ansible inventory script is missing!'
                raise SystemExit(err)
        return script

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
            ansible dynamic inventory will be incorrect.
            see also:
              https://github.com/ansible/ansible/blob/devel/lib/ansible/constants.py
        """
        return api.shell_env(
            YMIR_SERVICE_JSON=self.service_json_file,
            ANSIBLE_REMOTE_PORT=self._port,
            # ANSIBLE_TRANSPORT='paramiko',
            ANSIBLE_HOST_KEY_CHECKING="False",
            ANSIBLE_DEPRECATION_WARNINGS="False",
            ANSIBLE_TIMEOUT="60",
        )

    def _provision_ansible(self, cmd):
        """ handler for provision-list entries prefixed with `ansible://` """
        with self._ansible_ctx():
            return api.local(ANSIBLE_CMD.format(command=cmd, **self._ansible_env)).succeeded

    def _provision_ansible_playbook(self, cmd):
        """ handler for provision-list entries prefixed with
            `ansible_playbook://` or `ansible-playbook://`
        """
        with self._ansible_ctx():
            return api.local(ANSIBLE_PLAYBOOK_CMD.format(
                command=cmd, **self._ansible_env)).succeeded
