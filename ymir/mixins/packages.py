# -*- coding: utf-8 -*-
""" ymir.mixins.packages
"""
import os
from fabric import api
from ymir import data as ydata


class PackageMixin(object):
    """ To be linux-base agnostic, services should NOT call apt or yum directly.

        Actually.. services should not be installing packages directly because
        one of the CAP languages is used, but, to build puppet on the remote
        side we do need to add system packages first.

        Pacapt is used as a universal front-end for the backend
        package manager.  See: https://github.com/icy/pacapt
    """
    _require_pacapt_already_run = False

    def _require_pacapt(self):
        """ installs pacapt (a universal front-end for apt/yum/dpkg)
            on the remote server if it does not already exist there
        """
        if self._require_pacapt_already_run:
            return  # optimization hack: let's only run once per process
        self.report("checking remote side for pacapt "
                    "(an OS-agnostic package managemer)")
        with api.quiet():
            remote_missing_pacapt = api.run('ls /usr/bin/pacapt').failed
        if remote_missing_pacapt:
            self.report("pacapt does not exist, installing it now")
            local_pacapt_path = os.path.join(
                os.path.dirname(ydata.__file__), 'pacapt')
            self.put(local_pacapt_path, '/usr/bin', use_sudo=True)
            api.sudo('chmod o+x /usr/bin/pacapt')
        self._require_pacapt_already_run = True

    def _update_system_packages(self, quiet=True):
        """ """
        self._require_pacapt()
        quiet = '> /dev/null' if quiet else ''
        self.report("updating system packages, this might take a while.")
        canary = '/tmp/.ymir_package_update'
        max_age = 5
        with api.shell_env(warn_only=True):
            need_update = api.sudo('[ $(date +%s -r ' + canary + ') -lt $(date +%s --date="' + str(
                max_age) + ' min ago") ] ', shell='/bin/bash').succeeded
        if not need_update:
            self.report("  packages were updated recently, skipping")
            return True
        with api.shell_env(DEBIAN_FRONTEND='noninteractive'):
            result = api.sudo(
                'pacapt --noconfirm -Sy {0}'.format(quiet)).succeeded
            api.sudo('touch {0}'.format(canary))
            return result
    _update_sys_packages = _update_system_packages

    def _install_system_package(self, pkg_name, quiet=False):
        """ FIXME: only works with ubuntu/debian """
        self._require_pacapt()
        quiet = '> /dev/null' if quiet else ''
        with api.shell_env(DEBIAN_FRONTEND='noninteractive'):
            return api.sudo('pacapt --noconfirm -S {0} {1}'.format(
                pkg_name, quiet)).succeeded

    def _remove_system_package(self, pkg_name, quiet=True):
        self._require_pacapt()
        quiet = '> /dev/null' if quiet else ''
        return api.sudo('pacapt -R {0} {1}'.format(pkg_name, quiet)).succeeded
