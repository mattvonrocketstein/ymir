""" ymir.service.base
"""
import os
import time
import socket
import pprint
import urlparse
import webbrowser
import logging
import boto

import fabric
from fabric import api
from fabric.colors import blue

from ymir import util
from ymir import checks
from ymir.base import Reporter
from ymir.util import puppet
from ymir.puppet import PuppetMixin
from ymir.caching import cached
from ymir import data as ydata

NOOP = lambda *args, **kargs: None

# capture warnings because Fabric and
# it's dependencies can be pretty noisy
logger = logging.getLogger(__name__)
logging.captureWarnings(True)


class FabricMixin(object):
    FABRIC_COMMANDS = [
        'check', 'create', 'get',
        'integration_test', 'logs', 'mosh',
        'provision', 'put',
        'reboot', 'run',
        's3', 'service', 'setup',
        'shell', 'show', 'show_facts',
        'ssh', 'status',
        'supervisor', 'supervisorctl',
        'sync_eips', 'sync_elastic_ips',
        'sync_tags',
        'tail', 'terminate',
    ]

    def status(self):
        """ shows IP, ec2 status/tags, etc for this service """
        self.report('checking status', section=True)
        result = self._status()

        for k, v in result.items():
            self.report('  {0}: {1}'.format(k, v))
        return result

    @util.require_running_instance
    def sync_tags(self):
        """ update aws instance tags from service.json `tags` field """
        self.report('updating instance tags: ')
        json = self.template_data(simple=True)
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

    @util.require_running_instance
    def terminate(self, force=False):
        """ terminate this service (delete from ec2) """
        instance = self._instance
        self.report("{0} slated for termination.".format(instance))
        if force:
            return self.conn.terminate_instances(
                instance_ids=[instance.id])
        else:
            msg = ("This will terminate the instance {0} ({1}) and can "
                   "involve data loss.  Are you sure? [y/n] ")
            answer = None
            while answer not in ['y', 'n']:
                answer = raw_input(msg.format(
                    instance, self._service_data['name']))
            if answer == 'y':
                self.terminate(force=True)

    @util.require_running_instance
    def tail(self, filename):
        """ tail a file on the service host """
        with self.ssh_ctx():
            api.run('tail -f ' + filename)

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

    @util.require_running_instance
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
        service_data = self.template_data()
        util.mosh(self.status()['ip'],
                  username=self._username,
                  pem=service_data['pem'])

    @property
    def _username(self):
        """ username data is accessible only as a property because
            it must overridden for i.e. vagrant-based services
        """
        return self.template_data()['username']

    @util.require_running_instance
    def ssh(self):
        """ connect to this service with ssh """
        self.report('connecting with ssh')
        service_data = self.template_data()
        util.ssh(self._status()['ip'],
                 username=self._username,
                 pem=service_data['pem'],)

    @util.require_running_instance
    def show(self):
        """ open health-check webpages for this service in a browser """
        self.report('showing webpages')
        health_checks = self.template_data()['health_checks']
        for check_name in health_checks:
            check, url = health_checks[check_name]
            self._show_url(url.format(**self.template_data()))

    @util.require_running_instance
    def check(self, name=None):
        """ reports health for this service """
        self.report('checking health')
        # TODO: include relevant sections of status results
        # for x in 'status eb_health eb_status'.split():
        #    if x in data:
        #        out['aws://'+x] = ['read', data[x]]
        names = [name] if name is not None else self._service_data[
            'health_checks'].keys()
        service_health_checks = self._service_data['health_checks']
        for check_name, (_type, url_t) in service_health_checks.items():
            if check_name in names:
                check_obj = checks.Check(
                    url_t=url_t, check_type=_type, name=check_name)
                check_obj.run(self)

    def integration_test(self):
        """ runs integration tests for this service """
        self.report('running integration tests')
        data = self._status()
        if data['status'] == 'running':
            return self._test_data(data)
        else:
            self.report('no instance is running for this'
                        ' service, start (or create) it first')

    def copy_puppet(self, clean=True, puppet_dir='puppet', lcd=None):
        """ copy puppet code to remote host (refreshes any dependencies) """
        lcd = lcd or self._ymir_service_root
        with self.ssh_ctx():
            remote_user_home = '/home/' + self._username
            pfile = self._compress_local_puppet_code(puppet_dir, lcd=lcd)
            msg = '  flushing remote puppet codes and refreshing'
            self.report(msg)
            try:
                api.put(pfile, remote_user_home)
                with api.cd(remote_user_home):
                    if clean:
                        # this undoes `ymir setup` phase, ie the installation
                        # of puppet deps mentioned in metadata.json.
                        api.run('rm -rf "{0}"'.format(puppet_dir))
                    api.run(
                        'tar -zxf {0} && rm "{0}"'.format(os.path.basename(pfile)))
            finally:
                api.local('rm "{0}"'.format(pfile))

    @util.require_running_instance
    def reboot(self):
        """ TODO: blocking until reboot is complete? """
        self.report('rebooting service')
        with self.ssh_ctx():
            api.run('sudo reboot')

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


class PackageMixin(object):
    """ """
    _require_pacapt_already_run = False

    def _require_pacapt(self):
        """ installs pacapt (a universal front-end for apt/yum/dpkg)
            on the remote server if it does not already exist there

            see: https://github.com/icy/pacapt
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
        with api.shell_env(DEBIAN_FRONTEND='noninteractive'):
            return api.sudo('pacapt --noconfirm -Sy {0}'.format(quiet)).succeeded
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
        # """ FIXME: only works with ubuntu/debian """
        # with api.shell_env(DEBIAN_FRONTEND='noninteractive'):
        #    return api.sudo('apt-get -y remove {0} {1}'.format(
        #        pkg_name, '> /dev/null' if quiet else ''))


class AbstractService(Reporter, PuppetMixin, PackageMixin, FabricMixin):
    _schema = None
    _ymir_service_root = None
    _status_computed = False

    def __str__(self):  # pragma:nocover
        """ """
        try:
            return "<Service:{0}>".format(self._report_name())
        except:
            return super(AbstractService, self).__str__()

    __repr__ = __str__

    @property
    def _service_data(self):
        return self.template_data()

    def service(self, command):
        """ run `sudo service <cmd>` on the remote host"""
        with self.ssh_ctx():
            api.run('sudo service {0}'.format(command))

    def supervisorctl(self, command):
        """ run `sudo supervisorctl <cmd>` on the remote host """
        with self.ssh_ctx():
            api.run('sudo supervisorctl {0}'.format(command))
    supervisor = supervisorctl

    def logs(self, *args):
        """ lists the known log files for this service"""
        if not args:
            self.list_log_files()

    def list_log_files(self):
        """ """
        with self.ssh_ctx():
            for file_or_dir in self._service_data['logs']:
                if util.remote_path_exists(file_or_dir):
                    result = api.sudo(
                        'ls -l {0}'.format(file_or_dir), capture=True).strip()
                    self.report(" + {0}".format(str(result)))
                else:
                    self.report(" - {0}".format(file_or_dir))

    def fabric_install(self):
        """ publish certain service-methods into the fabfile
            namespace. this method is responsible for
            dynamically creating fabric commands, and should
            only be called from inside fabfiles
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

    def __init__(self, conn=None, service_root=None, ):
        """"""
        self.conn = conn or util.get_conn()
        self._ymir_service_root = service_root

    def _bootstrap_dev(self):
        """ """
        self.report("installing git & build-essentials")
        with api.settings(warn_only=True):
            results = [
                self._install_system_package('git', quiet=True),
                self._install_system_package('build-essential', quiet=True)]
        if not all(results):
            self.report(
                'bad return code bootstrapping dev.. waiting and trying again')
            time.sleep(35)
            self._bootstrap_dev()
        self._install_puppet()

    def report(self, msg, *args, **kargs):
        """ 'print' shortcut that includes some color and formatting """
        label = self._report_name()
        return util.report(label, msg, *args, **kargs)

    def _status(self):
        """ retrieves service status information.
            use this instead of self.status() if you want to quietly
            retrieve information for use without actually displaying it
        """
        tdata = self._service_data
        if not self._status_computed and self._debug_mode:
            self.report("handshaking with AWS..")
        name = tdata['name']
        instance = util.get_instance_by_name(name, self.conn)
        result = dict(
            instance=None, ip=None,
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
        self._status_computed = result
        return result

    def setup(self):
        """ setup service (operation should be after
            'create', before 'provision') """
        return self._setup(failures=0)

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
        name = self.template_data()['name']
        i = util.get_instance_by_name(name, conn)
        if strict and i is None:
            err = "Could not acquire instance! Is the name '{0}' correct?"
            err = err.format(name)
            self.report(err)
            raise SystemExit(1)
        return i

    def ssh_ctx(self):
        service_data = self.template_data()
        return util.ssh_ctx(
            self._status()['ip'],
            user=self._username,
            pem=service_data['pem'])

    def _restart_supervisor(self):
        self.report('  restarting everything')
        retries = 3
        cmd = "sudo /etc/init.d/supervisor restart"
        restart = lambda: api.run(cmd).return_code
        with api.settings(warn_only=True):
            result = restart()
            count = 0
            while result != 0 and count < retries:
                msg = ('failed to restart supervisor.'
                       '  trying again [{0}]').format(count)
                print msg
                result = restart()
                count += 1

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

        service_data = self.template_data()
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
            self.report('  setting tag for "Name": {0}'.format(
                self._service_data['name']))
            instance.add_tag("Name", self._service_data['name'])
        else:
            self.report('Weird instance status: ', status)
            return None

        time.sleep(5)
        self.report("Finished with creation.  Now run `fab setup`")

    def provision(self, fname=None, **kargs):
        """ provision this service """
        self.report('provisioning {0}'.format(fname or ''))
        if fname != 'None':
            data = self._status()
            if data['status'] == 'running':
                self._provision_ip(data['ip'], fname=fname, **kargs)
            else:
                self.report('no instance is running for this Service, '
                            'is the service created?  use "fab status" '
                            'to check again')
                return False

    def _provision_ip(self, ip, fname=None, force=False, **kargs):
        """ `force` must be True to provision with arguments not
            mentioned in service's provision_list """

        self.report('provisioning', section=True)
        self._clean_puppet_tmp_dir()
        if fname is not None:
            if not force and fname not in self.PROVISION_LIST:
                err = ('ERROR: Provisioning a single file requires that '
                       'the file should be mentioned in service.json, '
                       'but "{0}" was not found.').format(util.unexpand(fname))
                raise SystemExit(err)
            provision_list = [fname]
        else:
            provision_list = self.template_data()['provision_list']
        with self.ssh_ctx():
            with api.lcd(self._ymir_service_root):
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
                    self._run_provisioner(
                        provisioner, provision_instruction, **kargs)
        self.report("Finished with provision.")
        self.report("You might want to restart services "
                    " using `fab service` or `fab supervisor`")

    def _run_provisioner(self, provisioner_name, provision_instruction, **kargs):
        self.report(' {0}'.format(
            blue(provisioner_name + "://") + provision_instruction))
        try:
            provision_fxn = getattr(
                self, '_provision_{0}'.format(provisioner_name))
        except AttributeError:
            self.report(
                "Fatal: no sucher provisioner `{0}`".format(provisioner_name))
        return provision_fxn(provision_instruction, **kargs)

    def _provision_local(self, provision_instruction):
        """ runs a shell command on the local host,
            for the purposes of provisioning the remote host.
        """
        cmd = provision_instruction.format(**self.template_data())
        self.report("  translated to: {0}".format(cmd))
        return api.local(cmd)

    @property
    def _debug_mode(self):
        return self.template_data()['ymir_debug']

    def setup_ip(self, ip):
        """ """
        self.report('installing puppet & puppet deps', section=True)
        self._clean_puppet_tmp_dir()
        with self.ssh_ctx():
            with api.lcd(self._ymir_service_root):
                self._update_sys_packages()
                self._bootstrap_dev()
                self.copy_puppet(clean=True)
                self._bootstrap_puppet(force=True)
                setup_list = self.template_data()['setup_list']
                for setup_item in setup_list:
                    self.report(' .. setup_list[{0}]: "{1}"'.format(
                        setup_list.index(setup_item),
                        setup_item
                    ))
                    puppet.run_puppet(
                        setup_item,
                        puppet_dir='puppet',
                        facts=self.facts,
                        debug=self._debug_mode,)

        self.report("Setup complete.  Now run `fab provision`")

    @property
    def facts(self):
        """ """
        json = self.template_data(simple=True)
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

    @property
    def _s3_conn(self):
        return boto.connect_s3()

    def sync_buckets(self, quiet=False):
        report = self.report if not quiet else NOOP
        buckets = self._service_data['s3_buckets']
        report("synchronizing s3 buckets")
        if buckets:
            report('  buckets to create: {0}'.format(buckets))
        else:
            self.report("  no s3 buckets mentioned in service-definition")
        conn = self._s3_conn
        tmp = {}
        for name in buckets:
            report("  setting up s3 bucket: {0}".format(name))
            tmp[name] = conn.create_bucket(name, location=self.S3_LOCATION)
        return tmp

    def sync_eips(self, quiet=False):
        """ synchronizes elastic IPs with service.json data """
        report = self.report if not quiet else lambda *args, **kargs: None
        report("synchronizing elastic ip's")
        service_instance_id = self._status()['instance'].id
        eips = self.template_data()['elastic_ips']
        if not eips:
            report('  no elastic IPs mentioned in service-definition')
            return
        addresses = [x for x in self.conn.get_all_addresses()
                     if x.public_ip in eips]
        for aws_address in addresses:
            report(" Address: {0}".format(aws_address))
            if aws_address.instance_id is None:
                report("   -> currently unassigned.  "
                       "associating with this instance")
                aws_address.associate(instance_id=service_instance_id)
            elif aws_address.instance_id == service_instance_id:
                report("   -> already associated with this service")
            else:
                report("   -> assigned to another instance {0}! (that seems bad)".format(
                    aws_address.instance_id))
    sync_elastic_ips = sync_eips

    def sudo(self, *args, **kargs):
        with self.ssh_ctx():
            api.sudo(*args, **kargs)

    def run(self, command):
        """ run command on service host """
        with self.ssh_ctx():
            api.run(command)

    def _host(self, data=None):
        """ """
        data = data or self._status()
        return data.get('ip')

    def _show_url(self, url):
        url = url.format(**self.template_data(simple=False))
        self.report("showing: {0}".format(url))
        webbrowser.open(url)

    # TODO: cache for when simple is false
    def template_data(self, simple=False):
        """ reflects the template information back into itself """

        template_data = self.to_json(simple=simple)
        template_data.update(**self.SERVICE_DEFAULTS)
        for k, v in template_data['service_defaults'].items():
            if isinstance(v, basestring):
                template_data['service_defaults'][
                    k] = v.format(**template_data)
        return template_data
    _template_data = template_data

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

    @staticmethod
    def is_port_open(host, port):
        """ TODO: refactor into ymir.utils. this is used by ymir.checks """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, int(port)))
        return result == 0
