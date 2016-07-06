# -*- coding: utf-8 -*-
""" ymir.puppet

    Defines a puppet mixin for the base ymir service service class
"""
import re
import os
import glob
import shutil
import tempfile
import functools

from fabric import api
from fabric.contrib.files import exists
from fabric.contrib.project import rsync_project
from ymir.util import puppet as util_puppet
from ymir import data as ydata

RUBY_ROLE = "JhovaniC.ruby"
GIT_ROLE = 'geerlingguy.git'

# if/when puppet build happens, it more or less follows the instructions here:
#   https://docs.puppetlabs.com/puppet/3.8/reference/install_tarball.html
PUPPET_VERSION = [3, 4, 3]
PUPPET_URL = 'http://downloads.puppetlabs.com'
FACTER_TARBALL_URL = '{0}/facter/facter-1.7.5.tar.gz'.format(PUPPET_URL)
PUPPET_TARBALL_URL = '{0}/puppet/puppet-4.0.0.tar.gz'.format(PUPPET_URL)
HIERA_TARBALL_URL = '{0}/hiera/hiera-1.3.0.tar.gz'.format(PUPPET_URL)
PUPPET_TARBALL_FILE = PUPPET_TARBALL_URL.split('/')[-1]
PUPPET_TARBALL_UNCOMPRESS_DIR = PUPPET_TARBALL_FILE.replace('.tar.gz', '')
FACTER_TARBALL_FILE = FACTER_TARBALL_URL.split('/')[-1]
FACTER_TARBALL_UNCOMPRESS_DIR = FACTER_TARBALL_FILE.replace('.tar.gz', '')
HIERA_TARBALL_FILE = HIERA_TARBALL_URL.split('/')[-1]
HIERA_TARBALL_UNCOMPRESS_DIR = HIERA_TARBALL_FILE.replace('.tar.gz', '')


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

    @property
    def _puppet_template_vars(self):
        return self._get_puppet_template_vars()

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

    def _has_rsync(self):
        """ answers whether the remote side has rsync """
        with api.quiet():
            return api.run('rsync --version').succeeded

    def _require_rsync(self):
        """ """
        has_rsync = self._has_rsync()
        if not has_rsync:
            self.report(
                ydata.FAIL + "remote side is missing rsync.  installing it")
            common = "--become -a 'name=rsync state=present'"
            with api.quiet():
                success = self._provision_ansible(common + " -m apt ")
                if not success:
                    self._provision_ansible("-m yum")
        else:
            self.report(ydata.SUCCESS + "remote side already has rsync")

    @noop_if_no_puppet_support
    def copy_puppet(self, clean=True, puppet_dir='puppet', lcd=None):
        """ copy puppet code to remote host (refreshes any dependencies) """
        lcd = lcd or self._ymir_service_root
        remote_user_home = '/home/' + self._username
        with self.ssh_ctx():
            self.report('  flushing remote puppet codes and refreshing')
            self._require_rsync()
            with api.hide("output"):
                rsync_project(
                    os.path.join(remote_user_home, puppet_dir),
                    local_dir=os.path.join(lcd, puppet_dir, '*'),
                    ssh_opts="-o StrictHostKeyChecking=no",
                    delete=clean,
                    exclude=[
                        '.git', 'backups', 'venv',
                        '.vagrant', '*.pyc', ],)
            self.report(ydata.SUCCESS + "sync finished")

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

    def _compress_local_puppet_code(self, puppet_dir='puppet/', lcd=None):
        """ returns an absolute path to a temporary file
            containing puppet code for this service.
            NB: caller is responsible for deletion
        """
        assert lcd is not None
        with api.lcd(lcd):
            pfile = tempfile.mktemp(suffix='.tgz')
            # build a local tarball to copy and unzip on the remote side
            api.local('tar -czf {0} {1} '.format(pfile, puppet_dir))
        return pfile

    def _provision_puppet(self, provision_item, puppet_dir='puppet', extra_facts={}):
        """ runs puppet on remote host.  puppet files must already have been copied """
        service_data = self.template_data()
        facts = self.facts
        facts.update(**extra_facts)
        return util_puppet.run_puppet(
            provision_item,
            parser=service_data['puppet_parser'],
            facts=facts,
            debug=self._debug_mode,
            puppet_dir=puppet_dir,
        )

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
            api.sudo('gem install librarian-puppet')
        else:
            self.report(ydata.SUCCESS + "puppet librarian already installed")

        sync_puppet_librarian("puppet")

    def _install_ruby(self):
        """ installs ruby on the remote service """
        with api.quiet():
            has_ruby = api.run("ruby --version")
        ruby_version = has_ruby.succeeded and has_ruby.split()[1]
        has_ruby = has_ruby.succeeded
        if not has_ruby or not (ruby_version.startswith('1.9') or ruby_version.startswith('2')):
            self.report(ydata.FAIL + "ruby is missing or old")
            with api.quiet():
                self._provision_ansible(
                    "-m setup -m yum -a 'name=ruby state=absent'")
                self._provision_ansible(
                    "-m setup -m apt -a 'name=ruby state=absent'")
            self.report(ydata.SUCCESS + "flushed old ruby")
            self.report("installing new ruby")
            with api.hide("output"):
                self._apply_ansible_role(
                    RUBY_ROLE,
                    ruby_install_from_source=True,)
            self.report(ydata.SUCCESS + "finished installing new ruby")
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
        def decompress(x):
            """ helper to unwrap tarball, removing the
                original file if it was successful
            """
            if not api.run('tar -zxf "{0}"'.format(x)).failed:
                api.run('rm "{0}"'.format(x))

        def build_puppet():
            with api.hide('output'):
                self._apply_ansible_role("azavea.build-essential")
            self._install_ruby()
            run_install = lambda: api.sudo('ruby install.rb')
            download = lambda x: api.run(
                'wget -O {0} {1}'.format(os.path.basename(x), x))

            work_to_do = [
                [FACTER_TARBALL_URL, FACTER_TARBALL_FILE,
                    FACTER_TARBALL_UNCOMPRESS_DIR],
                [HIERA_TARBALL_URL, HIERA_TARBALL_FILE,
                    HIERA_TARBALL_UNCOMPRESS_DIR],
                [PUPPET_TARBALL_URL, PUPPET_TARBALL_FILE,
                    PUPPET_TARBALL_UNCOMPRESS_DIR],
            ]
            self.report("installing puppet pre-reqs")
            self._install_ruby()
            # rgen is required for puppet --parser=future,
            # but the command below only installs it if it's not already found
            api.sudo('{ gem list|grep rgen; } || gem install rgen')

            for url, tarball, _dir in work_to_do:
                with api.hide("output"):
                    download(url)
                decompress(tarball)
                with api.cd(_dir):
                    run_install()

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
            msg = "bad puppet version @ {0}, attempting uninstall"
            self.report(ydata.FAIL + msg.format(puppet_version))
            pkgs = 'puppet facter hiera puppet-common'.split()
            for pkg in pkgs:
                self._remove_system_package(pkg, quiet=False)
            return build_puppet()
