# -*- coding: utf-8 -*-
""" ymir.puppet

    Defines a puppet mixin for the base ymir service service class
"""
import re
import os
import glob
import shutil
import functools

from fabric import api
from fabric.contrib.files import exists
from ymir.util import puppet as util_puppet
from ymir import data as ydata

GIT_ROLE = 'geerlingguy.git'

# if/when puppet build happens, it more or less follows the instructions here:
#   https://docs.puppetlabs.com/puppet/3.8/reference/install_tarball.html
PUPPET_VERSION = [3, 4, 3]


def noop_if_no_puppet_support(fxn):
    """ """
    @functools.wraps(fxn)
    def newf(self, *args, **kargs):
        if not self._supports_puppet:
            return
        return fxn(self, *args, **kargs)
    return newf


class PuppetMixin(object):

    """ """

    @property
    def _supports_puppet(self):
        """ use _service_json here, it's a simple bool and not templated  """
        if not hasattr(self, '_supports_puppet_cache'):
            self._supports_puppet_cache = self._service_json[
                'ymir_build_puppet']
            icon = ydata.SUCCESS if self._supports_puppet_cache else ydata.FAIL
            self.report(icon + "ymir puppet support enabled?")
        return self._supports_puppet_cache

    @property
    def _puppet_metadata(self):
        return os.path.join(self._puppet_dir, 'metadata.json')

    @property
    def _puppet_dir(self):
        pdir = os.path.join(self._ymir_service_root, 'puppet')
        return pdir

    @property
    def _puppet_templates(self):
        return self._get_puppet_templates()

    def _get_puppet_templates(self):
        """ return puppet template files relative to working directory """
        return glob.glob(
            os.path.join(self._puppet_dir, 'modules', '*', 'templates', '*'))

    def _get_puppet_template_vars(self):
        """ returns a dictionary of { puppet_file : [..,template_vars,..]}"""
        out = {}
        for f in self._puppet_templates:
            with open(f, 'r') as fhandle:
                content = fhandle.read()
                out[f] = [x for x in re.findall('<%= @(.*?) %>', content)]
        return out

    @noop_if_no_puppet_support
    def copy_puppet(self, clean=True, puppet_dir='puppet', lcd=None):
        """ copy puppet code to remote host (refreshes any dependencies) """
        lcd = lcd or self._ymir_service_root
        # remote_user_home = '/home/' + self._username
        self.report('  flushing remote puppet code and refreshing')
        return self._rsync(
            src=os.path.join(lcd, puppet_dir, '*'),
            dest=os.path.join('~', puppet_dir),
            delete=clean,
        )

    @noop_if_no_puppet_support
    def _clean_puppet_tmp_dir(self):
        """ necessary because puppet librarian is messy,
            and these temporary files can interfere with
            validation
        """
        tdir = os.path.join(self._ymir_service_root, 'puppet', '.tmp')
        if os.path.exists(tdir):
            shutil.rmtree(tdir)
        self.report(ydata.SUCCESS + "cleaned puppet-librarian tmp dir")

    def _provision_puppet(self, provision_item, puppet_dir='puppet', extra_facts={}):
        """ runs puppet on remote host.  puppet files must already have been copied """
        service_data = self.template_data()
        facts = self.facts
        facts.update(**extra_facts)
        with self._rvm_ctx():
            return util_puppet.run_puppet(
                provision_item,
                parser=service_data['puppet_parser'],
                facts=facts,
                debug=self._debug_mode,
                puppet_dir=puppet_dir,)

    @property
    def _using_rvm(self):
        with api.quiet():
            has_rvm = api.run('which rvm').succeeded
        return has_rvm

    def _rvm_ctx(self, ruby_version='system'):
        if self._using_rvm:  # ruby version was old so ymir installed another ruby side-by-side
            prefix = "rvm use " + ruby_version
        else:
            prefix = "true"
        return api.prefix(prefix)

    @noop_if_no_puppet_support
    def _setup_puppet_deps(self, force=False):
        """ puppet itself is already installed at this point,
            this sets up the provisioning dependencies
        """
        def sync_puppet_librarian(_dir):
            found_modules = exists(os.path.join(
                _dir, 'modules'), use_sudo=True)
            if not force and found_modules:
                msg = "puppet-librarian has already processed modules and `force` was unset"
                self.report(ydata.SUCCESS + msg)
                return
            if not found_modules:
                msg = "puppet-librarian hasn't run yet, modules dir is missing"
                self.report(ydata.FAIL + msg)
            if force:
                msg = "update for puppet-librarian will be enforced"
                self.report(ydata.SUCCESS + msg)
            with api.cd(_dir):
                with self._rvm_ctx("1.9.3"):
                    api.run('librarian-puppet clean')
                    api.run('librarian-puppet install {0}'.format(
                        '--verbose' if self._debug_mode else ''))
                msg = "puppet-librarian finished updating puppet modules"
                self.report(ydata.SUCCESS + msg)
        self.report('installing puppet & puppet deps', section=True)
        if not self._supports_puppet:
            return
        self._install_puppet()
        self._install_ruby()
        self._install_git()
        with api.quiet():
            has_gem = api.run("gem --version").succeeded
        if not has_gem:
            self.report(
                ydata.FAIL + "`gem` not found but ruby was already installed!")
            raise SystemExit(1)
        with api.quiet():
            has_librarian = api.run(
                "gem list | grep -c librarian-puppet").succeeded
        if not has_librarian:
            self.report(ydata.FAIL + "puppet librarian not found")
            with self._rvm_ctx("1.9.3"):
                if self._using_rvm:
                    api.sudo('gem install puppet --no-ri --no-rdoc')
                api.sudo('gem install librarian-puppet --no-ri --no-rdoc')
        else:
            self.report(ydata.SUCCESS + "puppet librarian already installed")

        sync_puppet_librarian("puppet")

    def _install_ruby(self):
        """ installs ruby on the remote service,
            requiring at least version 1.9.  if not found,
            ruby_version: 2.2.3 will be installed
        """
        with api.quiet():
            has_ruby = api.run("ruby --version")
        ruby_version = has_ruby.succeeded and has_ruby.split()[1]
        has_ruby = has_ruby.succeeded
        if not has_ruby or not (ruby_version.startswith('1.9') or ruby_version.startswith('2')):
            self.report(
                ydata.FAIL + "ruby is missing or old: " + str(ruby_version))
            self._provision_ansible_role(
                "rvm_io.rvm1-ruby", rvm1_rubies=['ruby-1.9.3'])
            self.sudo("rvm default system")
            self.run("rvm default system")
            self.report(ydata.SUCCESS +
                        "finished installing new ruby with rvm")
        else:
            msg = "ruby is present on the remote side.  version={0}"
            self.report(ydata.SUCCESS + msg.format(ruby_version))

    def _install_git(self):
        """ installs git on the remote service """
        with api.quiet():
            has_git = api.run("git --version").succeeded
        if not has_git:
            self.report(ydata.FAIL + "git is missing, installing it")
            with api.hide("output"):
                self._apply_ansible_role(GIT_ROLE)
            self.report(ydata.SUCCESS + "git was installed")
        else:
            self.report(ydata.SUCCESS + "remote side already has git")

    def _install_puppet(self):
        """ """
        def build_puppet():
            cmd = "git clone https://github.com/hashicorp/puppet-bootstrap.git"
            self.report("checking for bootstrap scripts")
            if not os.path.exists(
                os.path.join(
                    self._ansible_dir,
                    'puppet-bootstrap')):
                with api.lcd(self._ansible_dir):
                    api.local(cmd)
            self._provision_ansible_playbook("ansible/puppet.yml")

        with api.quiet():
            puppet_version = api.run('puppet --version')
        puppet_installed = not puppet_version.failed
        if puppet_installed:
            puppet_version = puppet_version.strip().split('.')
            puppet_version = map(int, puppet_version)
            msg = "puppet is already installed, version is {0}"
            self.report(ydata.SUCCESS + msg.format(puppet_version))
        else:
            puppet_version = None
            msg = "puppet not installed, building it from scratch"
            self.report(ydata.FAIL + msg)
            return build_puppet()

        if puppet_version and puppet_version < PUPPET_VERSION:
            self.report(ydata.FAILED +
                        "puppet version is older than what is suggested")
