# -*- coding: utf-8 -*-
""" ymir.service.base
"""
import os
import time
import socket
import pprint
import urlparse
import webbrowser
import logging

import fabric
from fabric import api
from fabric.colors import blue, yellow

from ymir import util
from ymir.base import Reporter
from ymir.util import puppet
from ymir.puppet import PuppetMixin
from ymir.caching import cached
from ymir import data as ydata


# capture warnings because Fabric and
# it's dependencies can be pretty noisy
logger = logging.getLogger(__name__)
logging.captureWarnings(True)

# disable stricthostkey checking everywhere in fabric
api.env.disable_known_hosts = True


class FabricMixin(object):
    FABRIC_COMMANDS = [
        'check', 'create', 'get',
        'integration_test', 'logs',
        'provision', 'put',
        'reboot', 'run',
        'service', 'setup',
        'shell', 'show', 'show_facts',
        'ssh', 'status',
        'supervisor', 'supervisorctl',
        'tail',
    ]

    def status(self):
        """ shows IP, ec2 status/tags, etc for this service """
        self.report('checking status', section=True)
        result = self._status()

        for k, v in result.items():
            self.report('  {0}: {1}'.format(k, v))
        return result

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

    def ssh(self):
        """ connect to this service with ssh """
        self.report('connecting with ssh')
        util.ssh(
            self._host,
            username=self._username,
            pem=self._pem,
            port=self._port,)

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
        checks = self.template_data()['health_checks']
        names = [name] if name is not None else checks.keys()
        service_health_checks = checks
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

    @util.require_running_instance
    def reboot(self):
        """ TODO: blocking until reboot is complete? """
        self.report('rebooting service')
        with self.ssh_ctx():
            api.run('sudo reboot')


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
            for file_or_dir in self.template_data()['logs']:
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

    def __init__(self, service_root=None, ):
        """ """
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
        tdata = self._service_json  # NOT template_data(), that's cyclic
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
        """ """
        return util.ssh_ctx(
            ':'.join([self._host, self._port]),
            user=self._username,
            pem=self._pem,)

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
        name = self.template_data()['name']
        if status == 'running':
            self.report('  instance is running.')
            self.report('  setting tag for "Name": {0}'.format(
                name))
            instance.add_tag("Name", name)
        else:
            self.report('Weird instance status: ', status)
            return None

        time.sleep(5)
        self.report("Finished with creation.  Now run `fab setup`")

    def provision(self, fname=None, **kargs):
        """ provision this service """
        self.report('preparing to provision: {0}'.format(
            yellow(fname or '(everything)')))
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
                msg = ('\n  ' + pprint.pformat(provision_list, indent=2)) if \
                    provision_list else "(empty)"
                self.report("Provision list for this service: " + msg)
                # if clean==True, in the call below, the puppet deps
                # which were installed in the `setup` phase would be
                # destroyed.  not what is wanted for provisioning!
                self.copy_puppet(clean=False)
                for provision_item in provision_list:
                    protocol, instruction = self._split_instruction(
                        provision_item)
                    # if '://' in provision_item:
                    #    err = 'provision-protocol names may not include _.'
                    #    assert '_' not in provision_item.split('://')[0], err
                    # provisioner = urlparse.urlparse(provision_item).scheme
                    # if provisioner == '':
                    #    # for backwards compatability, puppet is the default
                    #    provisioner = 'puppet'
                    #    provision_instruction = provision_item
                    # else:
                    #    provision_instruction = provision_item[
                    #        len(provisioner) + len('://'):]
                    self.report('provision_list[{0}]:'.format(
                        provision_list.index(provision_item)))
                    self._run_provisioner(
                        protocol, instruction, **kargs)
        self.report("Finished with provision.")
        self.report("You might want to restart services "
                    " using `fab service` or `fab supervisor`")

    def _split_instruction(self, instruction):
        """ here, `instruction` is an item from either setup_list or provision_list
        """
        protocol = urlparse.urlparse(instruction).scheme
        if protocol == '':
            # for backwards compatability, puppet is the default
            protocol = 'puppet'
            raw_instruction = instruction
        else:
            raw_instruction = instruction[
                len(protocol) + len('://'):]
        return protocol, raw_instruction

    def _run_provisioner(self, provisioner_name, provision_instruction, **kargs):
        self.report(' {0}'.format(
            blue(provisioner_name + "://") + provision_instruction))
        try:
            provision_fxn = getattr(
                self, '_provision_{0}'.format(provisioner_name))
        except AttributeError:
            self.report(
                "Fatal: no sucher provisioner `{0}`".format(provisioner_name))
            raise SystemExit()
        else:
            cmd = provision_instruction.format(**self.template_data())
            if cmd != provision_instruction:
                self.report("  translated to: {0}".format(cmd))
            return provision_fxn(cmd, **kargs)

    def _provision_remote(self, cmd):
        return self.run(cmd)

    def _provision_local(self, cmd):
        """ runs a shell command on the local host,
            for the purposes of provisioning the remote host.
        """
        return api.local(cmd)

    @property
    def _debug_mode(self):
        """ use _service_json here, it's a simple bool and not templated  """
        return self._service_json['ymir_debug']

    def setup_ip(self, ip):
        """ """
        self._clean_puppet_tmp_dir()
        with self.ssh_ctx():
            with api.lcd(self._ymir_service_root):
                self._update_sys_packages()
                self._bootstrap_dev()
                self.copy_puppet(clean=True)  # NOOP if puppet isn't supported
                # NOOP if puppet isn't supported
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
        for fact in service_defaults:
            tmp = service_defaults[fact]
            if isinstance(tmp, basestring) and ('{' in tmp or '}' in tmp):
                raise SystemExit(
                    "facts should not contain mustaches: {0}".format(tmp))
        return service_defaults

    def sudo(self, *args, **kargs):
        with self.ssh_ctx():
            api.sudo(*args, **kargs)

    def run(self, command):
        """ run command on service host """
        with self.ssh_ctx():
            api.run(command)

    @property
    def _port(self):
        """ """
        return self._service_json['port']

    @property
    def _host(self):
        """ """
        return self._status().get('ip')

    def _show_url(self, url):
        url = url.format(**self.template_data(simple=False))
        self.report("showing: {0}".format(url))
        webbrowser.open(url)

    def template_data(self):
        """ a last phase of reflection, for data that's potentially
            only available just-in-time.
        """
        tmp = self._service_json.copy()
        tmp.update(
            username=self._username,
            pem=self._pem,
            host=self._host,
            port=self._port,
        )
        plist = [cmd.format(**tmp) for cmd in tmp['provision_list']]
        slist = [cmd.format(**tmp) for cmd in tmp['setup_list']]
        tmp['provision_list'] = plist
        tmp['setup_list'] = slist
        return tmp

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
