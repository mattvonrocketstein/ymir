# -*- coding: utf-8 -*-
""" ymir.service
"""
import os
import time
import pprint
import socket
import urlparse
import shutil
import webbrowser
import tempfile
import logging
import boto
# from retrying import retry

import fabric
from fabric.colors import blue
from fabric.colors import yellow
from fabric.contrib.files import exists

from fabric import api
from fabric.api import (
    cd, lcd, local, put,
    quiet, settings, run)

from ymir import util
from ymir import checks
from ymir.base import Reporter
from ymir.caching import cached
from ymir.schema import default_schema
from ymir.validation.mixin import ValidationMixin

NOOP = lambda *args, **kargs: None

# capture warnings because Fabric and
# it's dependencies can be pretty noisy
logger = logging.getLogger(__name__)
logging.captureWarnings(True)


def catch_network_error(exc):
    if isinstance(exc, fabric.exceptions.NetworkError):
        util.report('NetworkError', 'sleeping and retrying')
        return True


class FabricMixin(object):
    FABRIC_COMMANDS = [
        'check', 'create', 'get',
        'logs', 'mosh',
        'provision', 'put',
        'reboot', 'run',
        's3',
        'service',
        'setup',
        'shell',
        'show', 'show_facts', 'show_instances',
        'ssh',
        'status',
        'supervisor', 'supervisorctl',
        'sync_eips',
        'sync_elastic_ips',
        # 'sync_volumes',
        'tail', 'test', 'terminate',
        'sync_tags'
    ]

    @util.require_running_instance
    def terminate(self, force=False):
        """ terminate this service (delete from ec2) """
        instance = self._instance
        if force:
            return self.conn.terminate_instances(
                instance_ids=[instance.id])
        else:
            msg = ("This will terminate the instance {0} ({1}) and can "
                   "involve data loss.  Are you sure? [y/n] ")
            answer = None
            while answer not in ['y', 'n']:
                answer = raw_input(msg.format(instance, self.NAME))
            if answer == 'y':
                self.terminate(force=True)

    @util.require_running_instance
    def put(self, src, dest, *args, **kargs):
        """ thin wrapper around fabric's scp command
            just to use this service ssh context
        """
        owner = kargs.pop('owner', None)
        if owner:
            kargs['use_sudo'] = True
        with self.ssh_ctx():
            result = api.put(src, dest, *args, **kargs)
        if owner:
            api.sudo('chown {0}:{0} "{1}"'.format(owner, dest))
        return result

    def get(self, fname, local_path='.'):
        """ thin wrapper around fabric's scp command
            just to use this service ssh context
        """
        with self.ssh_ctx():
            return api.get(fname, local_path=local_path, use_sudo=True)

    @util.require_running_instance
    def mosh(self):
        """ connect to this service with mosh """
        self.report('connecting with mosh')
        service_data = self._template_data()
        util.mosh(self.status()['ip'],
                  username=service_data['username'],
                  pem=service_data['pem'])

    @util.require_running_instance
    def ssh(self):
        """ connect to this service with ssh """
        self.report('connecting with ssh')
        service_data = self._template_data()
        util.ssh(self._status()['ip'],
                 username=service_data['username'],
                 pem=service_data['pem'],)

    def show(self):
        """ open health-check webpages for this service in a browser """
        self.report('showing webpages')
        for check_name in self.HEALTH_CHECKS:
            check, url = self.HEALTH_CHECKS[check_name]
            self._show_url(url.format(**self._template_data()))

    def create(self, force=False):
        """ create new instance of this service ('force' defaults to False)"""
        self.report('creating ec2 instance', section=True)
        conn = self.conn
        i = self._get_instance()
        if i is not None:
            msg = '  instance already exists: {0} ({1})'
            msg = msg.format(i, i.update())
            self.report(msg)
            if force:
                self.report('  force is True, terminating it & rebuilding')
                util._block_while_terminating(i, conn)
                # might need to block and wait here
                return self.create(force=False)
            self.report('  force is False, refusing to rebuild it')
            return

        service_data = self._template_data()
        # HACK: deal with unfortunate vpc vs. ec2-classic differences
        reservation_extras = service_data.get('reservation_extras', {}).copy()

        # set security group stuff in reservation extras
        sg_names = service_data['security_groups']
        if not sg_names:
            err = ('without `security_groups` in service.json, '
                   'cannot create instance reservation')
            raise SystemExit(err)
        self.report(
            "service description uses {0} as a security groups".format(sg_names))
        tmp = {}
        sgs = dict([[sg.id, sg.name] for sg in conn.get_all_security_groups()])
        for sg_name in sg_names:
            if sg_name not in sgs.values():
                err = "could not find {0} amongst security groups at {1}"
                err = err.format(sg_names, sgs.values())
                raise SystemExit(err)
            else:
                _id = [_id for _id in sgs if sgs[_id] == sg_name][0]
                self.report("  sg '{0}' is id {1}".format(sgs[_id], _id))
                tmp[_id] = sgs[_id]
        reservation_extras['security_group_ids'] = tmp.keys()

        reservation = conn.run_instances(
            image_id=service_data['ami'],
            key_name=service_data['key_name'],
            instance_type=service_data['instance_type'],
            **reservation_extras)

        instance = reservation.instances[0]
        self.report('  no instance found, creating it now.')
        self.report('  reservation-id:', instance.id)

        util._block_while_pending(instance)
        status = instance.update()
        if status == 'running':
            self.report('  instance is running.')
            self.report('  setting tag for "Name": {0}'.format(self.NAME))
            instance.add_tag("Name", self.NAME)
        else:
            self.report('Weird instance status: ', status)
            return None

        time.sleep(5)
        self.report("Finished with creation.  Now run `fab setup`")

    @util.require_running_instance
    def check(self, name=None):
        """ reports health for this service """
        self.report('checking health')
        # include relevant sections of status results
        # for x in 'status eb_health eb_status'.split():
        #    if x in data:
        #        out['aws://'+x] = ['read', data[x]]
        health_checks = []
        names = [name] if name is not None else self._service_data[
            'health_checks'].keys()
        for check_name, (_type, url_t) in self._service_data['health_checks'].items():
            if names and check_name not in names:
                continue
            check_obj = checks.Check(
                url_t=url_t, check_type=_type, name=check_name)
            health_checks.append(check_obj)
        for check_obj in health_checks:
            check_obj.run(self)
        self._display_checks(health_checks)

    def test(self):
        """ runs integration tests for this service """
        self.report('running integration tests')
        data = self._status()
        if data['status'] == 'running':
            return self._test_data(data)
        else:
            self.report('no instance is running for this'
                        ' service, start (or create) it first')

    def _validate_puppet_librarian(self):
        errs = []
        metadata = os.path.join(
            self._ymir_service_root, 'puppet', 'metadata.json')
        if not os.path.exists(metadata):
            errs.append('{0} does not exist!'.format(metadata))
        else:
            if util.has_gem('metadata-json-lint'):
                cmd_t = 'metadata-json-lint {0}'
                with quiet():
                    x = local(cmd_t.format(metadata), capture=True)
                error = x.return_code != 0
                if error:
                    errs.append('could not validate {0}'.format(metadata))
                    errs.append(x.stderr.strip())
            else:
                errs.append(
                    'cannot validate.  '
                    '"gem install metadata-json-lint" first')
        return errs


class AbstractService(Reporter, FabricMixin, ValidationMixin):
    _schema = None
    ELASTIC_IPS = default_schema.get_default('elastic_ips')
    YMIR_DEBUG = default_schema.get_default('ymir_debug')
    SERVICE_DEFAULTS = {}
    _ymir_service_root = None
    HEALTH_CHECKS = {}
    INTEGRATION_CHECKS = {}

    @property
    def _service_data(self):
        return self._template_data()

    def service(self, command):
        """ run `sudo service <cmd>` on the remote host"""
        with self.ssh_ctx():
            run('sudo service {0}'.format(command))

    def supervisorctl(self, command):
        """ run `sudo supervisorctl <cmd>` on the remote host """
        with self.ssh_ctx():
            run('sudo supervisorctl {0}'.format(command))
    supervisor = supervisorctl

    def tail(self, filename):
        """ tail a file on the service host """
        with self.ssh_ctx():
            run('tail -f ' + filename)

    def logs(self, *args):
        """ list the known log files for this service"""
        if not args:
            self.list_log_files()

    def list_log_files(self):
        with self.ssh_ctx():
            for remote_dir in self._service_data['log_dirs']:
                print util.list_dir(remote_dir)

    def fabric_install(self):
        """ publish certain service-methods into the fabfile
            namespace. this essentially is responsible for
            dynamically creating fabric commands.
        """
        import fabfile
        for x in self.FABRIC_COMMANDS:
            try:
                tmp = getattr(fabfile, x)
            except AttributeError:
                setattr(fabfile, x, getattr(self, x))
            else:
                err = ('Service definition "{0}" attempted'
                       ' to publish method "{1}" as a fabric '
                       'command, but "{1}" is already present '
                       'in globals with value "{2}"').format(
                    self.__class__.__name__, x, str(tmp))
                self.report("ERROR:")
                raise SystemExit(err)

    def __call__(self):
        """ ---------------------------------------------------- """
        pass

    def _report_name(self):
        return super(AbstractService, self)._report_name()

    def __init__(self, conn=None, service_root=None, ):
        """"""
        self.conn = conn or util.get_conn()
        self._ymir_service_root = service_root

    def _bootstrap_dev(self):
        """ """
        self.report("installing git & build-essentials")
        with settings(warn_only=True):
            r1 = run('sudo apt-get install -y git build-essential > /dev/null')
        if r1.return_code != 0:
            self.report(
                'bad return code bootstrapping dev.. waiting and trying again')
            time.sleep(35)
            self._bootstrap_dev()
        self._install_puppet()

    def _remove_system_package(self, pkg_name, quiet=True):
        """ FIXME: only works with ubuntu/debian """
        with api.shell_env(DEBIAN_FRONTEND='noninteractive'):
            api.sudo('apt-get -y remove {0} {1}'.format(
                pkg_name, '> /dev/null' if quiet else ''))

    def _install_puppet(self):
        self.report("installing puppet")

        def decompress(x):
            """ unwraps tarball, removing the original file if it was successful """
            if not api.run('tar -zxf "{0}"'.format(x)).failed:
                api.run('rm "{0}"'.format(x))

        def doit():
            """ see https://docs.puppetlabs.com/puppet/3.8/reference/install_tarball.html """
            run_install = lambda: api.sudo('ruby install.rb')
            download = lambda x: api.run(
                'wget -O {0} {1}'.format(
                    os.path.basename(x), x))

            download('http://downloads.puppetlabs.com/facter/facter-1.7.5.tar.gz')
            decompress('facter-1.7.5.tar.gz')
            with api.cd('facter-1.7.5'):
                run_install()

            download('https://downloads.puppetlabs.com/puppet/puppet-3.4.3.tar.gz')
            decompress('puppet-3.4.3.tar.gz')
            with api.cd('puppet-3.4.3'):
                run_install()

            download('https://downloads.puppetlabs.com/hiera/hiera-1.3.0.tar.gz')
            decompress('hiera-1.3.0.tar.gz')
            with api.cd('hiera-1.3.0'):
                run_install()
        self.report("installing puppet pre-reqs")
        api.run('sudo apt-get install -y ruby-dev ruby-json > /dev/null')
        # required for puppet --parser=future
        api.sudo('gem install rgen')

        with api.quiet():
            with api.settings(warn_only=True):
                puppet_version = api.run('puppet --version')
        puppet_installed = not puppet_version.failed
        if puppet_installed:
            puppet_version = puppet_version.strip().split('.')
            puppet_version = map(int, puppet_version)
            self.report("puppet is already installed")
        else:
            puppet_version = None
            self.report("puppet not installed")
            doit()
        if puppet_version and puppet_version != [3, 4, 3]:
            self.report(
                "bad puppet version @ {0}, attempting uninstall".format(puppet_version))
            pkgs = 'puppet facter hiera puppet-common'.split()
            for pkg in pkgs:
                self._remove_system_package(pkg)
            doit()

    def _get_ubuntu_version(self):
        """ """
        self.report("detecting ubuntu version:")
        try:
            with api.quiet():
                v = run('cat /etc/lsb-release|grep DISTRIB_RELEASE')
            result = v.strip().split('=')[-1]
            self.report("  version {0}".format(result))
            return map(int, result.split('.'))
        except Exception as e:
            self.report(blue("not ubuntu! ") + str(e))
            return []

    def report(self, msg, *args, **kargs):
        """ 'print' shortcut that includes some color and formatting """
        label = self._report_name()
        return util.report(label, msg, *args, **kargs)

    def status(self):
        """ shows IP, ec2 status/tags, etc for this service """
        self.report('checking status', section=True)
        result = self._status()
        for k, v in result.items():
            self.report('  {0}: {1}'.format(k, v))
        return result

    def _status(self):
        """ retrieves service status information.
            use this instead of self.status() if you want to quietly
            retrieve information for use without actually displaying it
        """
        instance = util.get_instance_by_name(self.NAME, self.conn)
        result = dict(
            instanceance=None, ip=None,
            private_ip=None, tags=[],
            status='terminated?',)
        if instance:
            result.update(
                dict(
                    instance=instance,
                    tags=instance.tags,
                    status=instance.update(),
                    ip=instance.ip_address,
                    private_ip=instance.private_ip_address,
                ))
        return result

    def _bootstrap_puppet(self, force=False):
        """ puppet itself is already installed at this point,
            this sets up the provisioning dependencies
        """
        def _init_puppet(_dir):
            if not force and exists(os.path.join(_dir, 'modules'), use_sudo=True):
                self.report("  puppet-librarian has already processed modules")
                return
            self.report("  puppet-librarian will install dependencies")
            with cd(_dir):
                run('librarian-puppet init')
                run('librarian-puppet install --verbose')
        self.report("  bootstrapping puppet dependencies on remote host")
        util._run_puppet(
            'puppet/modules/ymir/install_librarian.pp',
            debug=self.YMIR_DEBUG)
        _init_puppet("puppet")

    def setup(self):
        """ setup service (operation should be after 'create', before 'provision')"""
        return self._setup(failures=0)

    # @retry(
    #    retry_on_exception=catch_network_error,
    #    wait_fixed=5000, stop_max_attempt_number=3)
    def _setup(self, failures=0):
        self.report('setting up')
        cm_data = self._status()
        if cm_data['status'] == 'running':
            try:
                self.setup_ip(cm_data['ip'])
            except fabric.exceptions.NetworkError as e:
                if failures > 5:
                    self.report("CRITICAL: encountered 5+ network failures")
                    self.report("  Is the security group setup correctly?")
                    self.report("  Is the internet turned on??")
                    raise SystemExit(1)
                else:
                    self.report(str(e))
                    self.report("network error, sleeping and retrying")
                    time.sleep(7)
                    self._setup(failures=failures + 1)
        else:
            self.report(
                'No instance is running for this Service, create it first.')
            self.report(
                'If it was recently created, wait while and then try again')

    @property
    @cached('service._instance', 60 * 20)
    def _instance(self):
        """ return the aws instance """
        return self._get_instance(strict=True)

    def _get_instance(self, strict=False):
        conn = self.conn
        i = util.get_instance_by_name(self.NAME, conn)
        if strict and i is None:
            err = "Could not acquire instance! Is the name '{0}' correct?"
            err = err.format(self.NAME)
            self.report(err)
            raise SystemExit(1)
        return i

    def ssh_ctx(self):
        service_data = self._template_data()
        return util.ssh_ctx(
            self._status()['ip'],
            user=service_data['username'],
            pem=service_data['pem'])

    @util.require_running_instance
    def sync_tags(self):
        """ update aws instance tags from service.json `tags` field """
        self.report('updating instance tags: ')
        json = self._template_data(simple=True)
        tags = dict(
            description=json.get('service_description', ''),
            org=json.get('org_name', ''),
            app=json.get('app_name', ''),
            env=json.get("env_name", ''),
        )
        for tag in json.get('tags', []):
            tags[tag] = 'true'
        for tag in tags:
            if not tags[tag]:
                tags.pop(tag)
        self.report('  {0}'.format(tags.keys()))
        self._instance.add_tags(tags)

    def _restart_supervisor(self):
        self.report('  restarting everything')
        retries = 3
        cmd = "sudo /etc/init.d/supervisor restart"
        restart = lambda: run(cmd).return_code
        with settings(warn_only=True):
            result = restart()
            count = 0
            while result != 0 and count < retries:
                msg = ('failed to restart supervisor.'
                       '  trying again [{0}]').format(count)
                print msg
                result = restart()
                count += 1

    def _compress_local_puppet_code(self):
        """ returns an absolute path to a temporary file
            containing puppet code for this service.
            NB: caller is responsible for deletion
        """
        with lcd(self._ymir_service_root):
            pfile = tempfile.mktemp(suffix='.tgz')
            # build a local tarball to copy and unzip on the remote side
            api.local('tar -czf {0} puppet/ '.format(pfile))
        return pfile

    def provision(self, fname=None):
        """ provision this service """
        self.report('provisioning {0}'.format(fname or ''))
        if fname != 'None':
            data = self._status()
            if data['status'] == 'running':
                self._provision_ip(data['ip'], fname=fname)
            else:
                self.report('no instance is running for this Service, '
                            'is the service created?  use "fab status" '
                            'to check again')
                return False

    def _provision_ip(self, ip, fname=None):
        """ """
        self.report('provisioning', section=True)
        self._clean_tmp_dir()
        if fname is not None:
            if fname not in self.PROVISION_LIST:
                err = ('ERROR: Provisioning a single file requires that '
                       'the file should be mentioned in service.json, '
                       'but "{0}" was not found.').format(fname)
                raise SystemExit(err)
            provision_list = [fname]
        else:
            provision_list = self.PROVISION_LIST
        with self.ssh_ctx():
            with lcd(self._ymir_service_root):
                self.report("Provision list for this service:")
                pprint.pprint(provision_list, indent=2)
                # if clean==True, in the call below, the puppet deps
                # which were installed in the `setup` phase would be
                # destroyed.  not what is wanted for provisioning!
                self.copy_puppet(clean=False)
                for provision_item in provision_list:
                    if '://' in provision_item:
                        err = 'provision-protocol names may not include _.'
                        assert '_' not in provision_item.split('://')[0], err
                    provisioner = urlparse.urlparse(provision_item).scheme
                    if provisioner == '':
                        # for backwards compatability, puppet is the default
                        provisioner = 'puppet'
                        provision_instruction = provision_item
                    else:
                        provision_instruction = provision_item[
                            len(provisioner) + len('://'):]
                    self.report('provision_list[{0}]:'.format(
                        provision_list.index(provision_item)))
                    self._run_provisioner(provisioner, provision_instruction)
        self.report("Finished with provision.")
        self.report("You might want to restart services "
                    " using `fab service` or `fab supervisor`")

    def _run_provisioner(self, provisioner_name, provision_instruction, ):
        self.report(' {0}'.format(
            blue(provisioner_name + "://") + provision_instruction))
        try:
            provision_fxn = getattr(
                self, '_provision_{0}'.format(provisioner_name))
        except AttributeError:
            self.report(
                "Fatal: no sucher provisioner `{0}`".format(provisioner_name))
        return provision_fxn(provision_instruction)

    def _provision_puppet(self, provision_item):
        """ runs puppet on remote host.  puppet files must already have been copied """
        service_data = self._template_data()
        return util._run_puppet(
            provision_item,
            parser=service_data['puppet_parser'],
            facts=self.facts,
        )

    def _provision_local(self, provision_instruction):
        """ runs a shell command on the local host,
            for the purposes of provisioning the remote host.
        """
        cmd = provision_instruction.format(**self._template_data())
        self.report("  translated to: {0}".format(cmd))
        return local(cmd)

    def _clean_tmp_dir(self):
        """ necessary because puppet librarian is messy """
        self.report("  .. cleaning puppet tmp dir")
        tdir = os.path.join(self._ymir_service_root, 'puppet', '.tmp')
        if os.path.exists(tdir):
            # ~/puppet/.tmp should be nixed
            shutil.rmtree(tdir)

    def _update_sys_packages(self):
        """ must be run with ssh_ctx() """
        self.report(" .. updating remote system package list")
        run('sudo apt-get update > /dev/null')

    def setup_ip(self, ip):
        self.sync_tags()
        self.sync_buckets()
        self.sync_eips()
        self.report('installing puppet & puppet deps', section=True)
        self._clean_tmp_dir()
        with self.ssh_ctx():
            with lcd(self._ymir_service_root):
                self._update_sys_packages()
                self._bootstrap_dev()
                self.copy_puppet()
                self._bootstrap_puppet(force=True)
                for setup_item in self.SETUP_LIST:
                    self.report(' .. setup_list[{0}]: "{1}"'.format(
                        self.SETUP_LIST.index(setup_item),
                        setup_item
                    ))
                    util._run_puppet(
                        setup_item,
                        puppet_dir='puppet',
                        facts=self.facts,
                        debug=self.YMIR_DEBUG,)

        self.report("Setup complete.  Now run `fab provision`")

    @property
    def facts(self):
        """ """
        json = self._template_data(simple=True)
        service_defaults = json['service_defaults']
        service_defaults.update(
            dict(supervisor_user=json['supervisor_user'],
                 supervisor_pass=json['supervisor_pass'],
                 supervisor_port=json['supervisor_port']))
        for fact in service_defaults:
            tmp = service_defaults[fact]
            if isinstance(tmp, basestring) and ('{' in tmp or '}' in tmp):
                raise SystemExit(
                    "facts should not contain mustaches: {0}".format(tmp))
        return service_defaults

    def s3(self):
        """ show summary of s3 information for this service """
        buckets = self.sync_buckets(quiet=True).items()
        if not buckets:
            self.report("this service is not using S3 buckets")
        for bname, bucket in buckets:
            keys = [k for k in bucket]
            self.report("  {0} ({1} items) [{2}]".format(
                bname, len(keys), bucket.get_acl()))
            for key in keys:
                print ("  {0} (size {1}) [{2}]".format(
                    key.name, key.size, key.get_acl()))

    @property
    def _s3_conn(self):
        return boto.connect_s3()

    def sync_buckets(self, quiet=False):
        report = self.report if not quiet else NOOP
        if self._service_data['s3_buckets']:
            report('setting up buckets for this service')
        else:
            self.report("no s3 buckets detected in service-definition")
        conn = self._s3_conn
        tmp = {}
        for name in self.S3_BUCKETS:
            report("  setting up s3 bucket: {0}".format(name))
            tmp[name] = conn.create_bucket(name, location=self.S3_LOCATION)
        return tmp

    def sync_eips(self, quiet=False):
        """ synchronizes elastic IPs with service.json data """
        report = self.report if not quiet else lambda *args, **kargs: None
        service_instance_id = self._status()['instance'].id
        if not self.ELASTIC_IPS:
            report('no elastic IPs detected in service definition')
            return
        addresses = [x for x in self.conn.get_all_addresses(
        ) if x.public_ip in self.ELASTIC_IPS]
        for aws_address in addresses:
            report(" Address: {0}".format(aws_address))
            if aws_address.instance_id is None:
                report("   -> currently unassigned.  associating with this instance")
                aws_address.associate(instance_id=service_instance_id)
            elif aws_address.instance_id == service_instance_id:
                report("   -> already associated with this service")
            else:
                report("   -> assigned to another instance {0}! (that seems bad)".format(
                    aws_address.instance_id))
    sync_elastic_ips = sync_eips

    def run(self, command):
        """ run command on service host """
        with self.ssh_ctx():
            run(command)

    def copy_puppet(self, clean=True):
        """ copy puppet code to remote host (refreshes any dependencies) """
        service_data = self._template_data()
        with self.ssh_ctx():
            remote_user_home = '/home/' + service_data['username']
            pfile = self._compress_local_puppet_code()
            msg = '  flushing remote puppet codes and refreshing'
            self.report(msg)
            try:
                put(pfile, remote_user_home)
                with api.cd(remote_user_home):
                    if clean:
                        # this undoes `ymir setup` phase, ie the installation
                        # of puppet deps mentioned in metadata.json.
                        api.run('rm -rf puppet')
                    api.run(
                        'tar -zxf {0} && rm "{0}"'.format(os.path.basename(pfile)))
            finally:
                api.local('rm "{0}"'.format(pfile))

    @util.require_running_instance
    def reboot(self):
        """ TODO: blocking until reboot is complete? """
        self.report('rebooting service')
        with self.ssh_ctx():
            run('sudo reboot')

    def _host(self, data=None):
        """ todo: move to beanstalk class """
        data = data or self._status()
        return data.get(
            'eb_cname',
            data.get('ip'))

    def _show_url(self, url):
        url = url.format(**self._template_data(simple=False))
        self.report("showing: {0}".format(url))
        webbrowser.open(url)

    # TODO: cache for when simple is false
    def to_json(self, simple=False):
        """ this is used to compute the equivalent of service.json if
            there IS no service.json (ie the developer is using a python
            class definition and class variables)
        """
        raise Exception("deprecated")

    # TODO: cache for when simple is false
    def _template_data(self, simple=False):
        """ reflects the template information back into itself """

        template_data = self.to_json(simple=simple)
        template_data.update(**self.SERVICE_DEFAULTS)
        for k, v in template_data['service_defaults'].items():
            if isinstance(v, basestring):
                template_data['service_defaults'][
                    k] = v.format(**template_data)
        return template_data

    """ def _test_data(self, data):
        #run integration tests given 'status' data
        out = {}
        self.check_data(data)
        for check_name  in self.INTEGRATION_CHECKS:
            check_type, url = self.INTEGRATION_CHECKS[check_name]
            _url, result = self._run_check(check_type, url)
            out[_url] = [check_name, check_type, result]
        self._display_checks(out) """

    def _display_checks(self, checks):
        for check_obj in checks:
            self.report(' [{0}] [?{1}] -- {2} {3}'.format(
                yellow(check_obj.name),
                blue(check_obj.check_type),
                check_obj.url_t,
                check_obj.msg))

    def shell(self):
        """ """
        return util.shell(
            conn=self.conn, Service=self, service=self)

    def show_facts(self):
        """ show facts (puppet key-values available to templates)"""
        self.report("facts (template variables) available to puppet code:")
        facts = sorted([[k, v] for k, v in self.facts.items()])
        for k, v in facts:
            print ' ', k, '=>', v

    def show_instances(self):
        """ show all ec2 instances """
        util.show_instances(conn=self.conn)

    @staticmethod
    def is_port_open(host, port):
        """ TODO: refactor into ymir.utils. this is used by ymir.checks """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, int(port)))
        return result == 0
