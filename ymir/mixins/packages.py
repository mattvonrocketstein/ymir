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
                    "(an OS-agnostic package manager)")
        with api.quiet():
            remote_missing_pacapt = api.run('ls /usr/bin/pacapt').failed
        if remote_missing_pacapt:
            self.report(
                ydata.FAIL + "  pacapt does not exist, installing it now")
            local_pacapt_path = os.path.join(
                os.path.dirname(ydata.__file__), 'pacapt')
            self.put(local_pacapt_path, '/usr/bin', use_sudo=True)
        else:
            self.report(ydata.SUCCESS + " pacapt is already present")
        api.sudo('chmod o+x /usr/bin/pacapt')
        self._require_pacapt_already_run = True

    def _update_system_packages(self, quiet=True):
        """ does not use ansible, hopefully this makes caching easier so
            updates are faster.  still, this should probably be refactored
            or deprecated because it's the only reason pacapt is still needed.
        """
        self._require_pacapt()
        quiet = '> /dev/null' if quiet else ''
        self.report("updating system packages, this might take a while.")
        canary = '/tmp/.ymir_package_update'
        max_age = 360
        age_test = "[[ `date +%s -r {0}` -gt `date +%s --date='{1} min ago'` ]]"
        with api.quiet():
            need_update = api.sudo(age_test.format(canary, max_age)).failed
        if not need_update:
            msg = "packages were updated less than {0} minutes ago"
            self.report(ydata.SUCCESS + msg.format(max_age))
            return True
        with api.shell_env(DEBIAN_FRONTEND='noninteractive'):
            with api.settings(warn_only=True):
                # return code is "100" for centos
                result = api.sudo(
                    '/usr/bin/pacapt --noconfirm -Sy {0}'.format(quiet)).succeeded
            api.sudo('touch {0}'.format(canary))
            return result
    _update_sys_packages = _update_system_packages

    def _install_system_package(self, pkg_name, quiet=False):
        """ """
        with api.settings(warn_only=True):
            success = self._provision_apt(pkg_name)
            if not success:
                success = self._provision_yum(pkg_name)
        return success

    def _pkg_provisioner(self, pkg_name, ansible_module_name, state='present'):
        """ """
        cmd = '--become --module-name {0} -a "name={1} state={2}"'
        cmd = cmd.format(
            ansible_module_name, pkg_name, state)
        with api.settings(warn_only=True):
            return self._provision_ansible(cmd)

    def _pkgs_provision(self, pkg_names, ansible_module_name, state='present'):
        pkg_names = pkg_names.split(',')
        results = []
        for pkg in pkg_names:
            results.append(
                self._pkg_provisioner(pkg, ansible_module_name, state=state))
        return all(results)

    def _provision_yum(self, pkg_names):
        """ """
        return self._pkg_provisioner(pkg_names, 'yum')

    def _provision_apt(self, pkg_names):
        """ """
        return self._pkg_provisioner(pkg_names, 'apt')

    def _remove_system_package(self, pkg_name):
        """ """
        success = self._pkg_provisioner(pkg_name, "apt", state="absent")
        if not success:
            self._pkg_provisioner(pkg_name, "yum", state="absent")
