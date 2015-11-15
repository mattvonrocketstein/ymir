""" ymir.service
"""
import os, time
import socket
import shutil, webbrowser
import tempfile
import logging

import boto


import fabric
from fabric.colors import blue
from fabric.colors import yellow
from fabric.contrib.files import exists
from fabric import api
from fabric.api import (
    cd, lcd, local, put,
    quiet, settings, run )

from ymir import util
from ymir import checks
from ymir.base import Reporter
from ymir.data import DEFAULT_SUPERVISOR_PORT
from ymir.schema import default_schema
from ymir.validation import ValidationMixin

# capture warnings because Fabric and
# it's dependencies can be pretty noisy
logger = logging.getLogger(__name__)
logging.captureWarnings(True)


class FabricMixin(object):
    FABRIC_COMMANDS = [
        'check', 'create', 'logs',
        'provision', 'run',
        'setup', 's3', 'shell',
        'status', 'ssh','show',
        'show_facts', 'show_instances',
        'tail', 'test', 'get', 'put',
        ]

    def put(self, *args):
        """ thin wrapper around fabric's scp command
            just to use this service ssh context
        """
        self.report(
            'putting "{0}" to remote'.format(
                args))
        with self.ssh_ctx():
            return api.put(*args)

    def get(self, fname):
        """ thin wrapper around fabric's scp command
            just to use this service ssh context
        """
        self.report(
            'getting "{0}" from remote'.format(
                fname))
        dest = os.path.basename(fname)
        with self.ssh_ctx():
            return api.get(fname, local_path='.', use_sudo=True)


    def provision(self, fname=None):
        """ provision this service """
        self.report('provisioning {0}'.format(fname or ''))
        data = self._status()
        if data['status']=='running':
            return self.provision_ip(data['ip'], fname=fname)
        else:
            self.report('no instance is running for this Service, '
                        'is the service created?  use "fab status" '
                        'to check again')

    def ssh(self):
        """ connect to this service with ssh """
        self.report('connecting with ssh')
        cm_data = self.status()
        if cm_data['status'] == 'running':
            util.connect(cm_data['ip'],
                         username=self.USERNAME,
                         pem=self.PEM)
        else:
            self.report("no instance found")

    def show(self):
        """ open health-check webpages for this service in a browser """
        self.report('showing webpages')
        #data = self._status()
        for check_name in self.HEALTH_CHECKS:
            check, url = self.HEALTH_CHECKS[check_name]
            self._show_url(url.format(**self._template_data()))

    def create(self, force=False):
        """ create new instance of this service ('force' defaults to False)"""
        self.report('creating', section=True)
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

        # HACK: deal with unfortunate vpc vs. ec2-classic differences
        reservation_extras = self.RESERVATION_EXTRAS.copy()

        if 'security_group_ids' in reservation_extras:
            # vpc-based (not ec2 classic style)
            pass
        else:
            reservation_extras['security_groups'] = self.SECURITY_GROUPS
        reservation = conn.run_instances(
            image_id=self.AMI,
            key_name=self.KEY_NAME,
            instance_type=self.INSTANCE_TYPE,
            **reservation_extras
            #security_groups = self.SECURITY_GROUPS,
            #block_device_mappings = [bdm]
            )

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

    def check(self):
        """ reports health for this service """
        self.report('checking health')
        data = self._status()
        if data['status'] == 'running':
            return self._check()
        else:
            self.report('no instance is running for this'
                        ' service, create it first')

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
            self.SERVICE_ROOT, 'puppet', 'metadata.json')
        if not os.path.exists(metadata):
            errs.append('{0} does not exist!'.format(metadata))
        else:
            if util.has_gem('metadata-json-lint'):
                cmd_t = 'metadata-json-lint {0}'
                with quiet():
                    x = local(cmd_t.format(metadata), capture=True)
                error = x.return_code!=0
                if error:
                    errs.append('could not validate {0}'.format(metadata))
                    errs.append(x.stderr.strip())
            else:
                errs.append(
                    'cannot validate.  '
                    '"gem install metadata-json-lint" first')
        return errs

class AbstractService(Reporter, FabricMixin, ValidationMixin):
    _schema         = None
    S3_BUCKETS      = default_schema.get_default('s3_buckets')
    ELASTIC_IPS      = default_schema.get_default('elastic_ips')

    # not DRY, see also:
    #  puppet/modules/ymir/templates/ymir_motd.erb
    #  puppet/modules/ymir/templates/supervisord.conf
    SUPERVISOR_USER = ''
    SUPERVISOR_PASS = ''
    SUPERVISOR_PORT = default_schema.get_default('supervisor_port')
    YMIR_DEBUG = default_schema.get_default('ymir_debug')
    SERVICE_DEFAULTS = {}
    LOGS = default_schema.get_default('logs')
    LOG_DIRS = default_schema.get_default('log_dirs')
    INSTANCE_TYPE   = 't1.micro'
    PUPPET_PARSER   = None
    SERVICE_ROOT    = None
    PEM             = None
    USERNAME        = None
    APP_NAME        = None
    ORG_NAME        = None
    ENV_NAME        = None
    SECURITY_GROUPS = None
    RESERVATION_EXTRAS = default_schema.get_default('reservation_extras')
    HEALTH_CHECKS = {}
    INTEGRATION_CHECKS = {}


    def list_log_files(self):
        with self.ssh_ctx():
            for remote_dir in self.LOG_DIRS:
                print util.list_dir(remote_dir)

    def tail(self, filename):
        """ tail a file on the service host """
        with self.ssh_ctx():
            run('tail -f '+filename)

    def logs(self, *args):
        """ list the known log files for this service"""
        if not args:
            self.list_log_files()

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
                setattr(fabfile, x, getattr(self,x))
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

    def __init__(self, conn=None):
        """"""
        self.conn = conn or util.get_conn()
        #required_class_vars = 'PEM USERNAME SECURITY_GROUPS SERVICE_ROOT'
        #required_class_vars =required_class_vars.split()
        #for var in required_class_vars:
        #    err = 'subclassers must override '+var
        #    assert getattr(self,var) is not None, err

    def _bootstrap_dev(self):
        """ """
        with settings(warn_only=True):
            r1 = run('sudo apt-get install -y git build-essential')
        if r1.return_code!=0:
            print 'bad return code bootstrapping dev.. waiting and trying again'
            import time
            time.sleep(5)
            self._bootstrap_dev()
        r2 = run('sudo apt-get install -y puppet ruby-dev > /dev/null')

    def report(self, msg, *args, **kargs):
        """ 'print' shortcut that includes some color and formatting """
        if 'section' in kargs:
            print '-' * 80
        template = '\x1b[31;01m{0}:\x1b[39;49;00m {1} {2}'
        name = self._report_name()
        # if Service subclasses are embedded directly into fabfiles, there
        # is a need for a lot of private variables to control the namespace
        # fabric publishes as commands.
        name = name.replace('_', '')
        print template.format(name, msg, args or '')

    def status(self):
        """ shows IP, ec2 status/tags, etc for this service """
        self.report('checking status', section=True)
        result = self._status()
        for k,v in result.items():
            self.report('  {0}: {1}'.format(k,v))
        return result

    def _status(self):
        """ retrieves service status information """
        inst = util.get_instance_by_name(self.NAME, self.conn)
        if inst:
            #addresses = [ a for a in self.conn.get_all_addresses() \
            #              if a.instance_id == inst.id]
            result = dict(
                instance=inst,
                supervisor='http://{0}:{1}@{2}:{3}/'.format(
                    self.SUPERVISOR_USER,
                    self.SUPERVISOR_PASS,
                    inst.ip_address,
                    DEFAULT_SUPERVISOR_PORT),
                tags=inst.tags,
                status=inst.update(),
                ip=inst.ip_address)
        else:
            result = dict(instance=None, ip=None, status='terminated?')
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
        """ setup service (operation should be after
        'create', before 'provision')"""
        self.report('setting up')
        cm_data = self._status()
        if cm_data['status'] == 'running':
            try:
                self.setup_ip(cm_data['ip'])
            except fabric.exceptions.NetworkError:
                self.report("timed out, retrying")
                self.setup()
        else:
            self.report('No instance is running for this Service, create it first.')
            self.report('If it was recently created, wait while and then try again')

    def _get_instance(self):
        conn = self.conn
        i = util.get_instance_by_name(self.NAME, conn)
        return i


    def ssh_ctx(self):
        return util.ssh_ctx(
            self._status()['ip'],
            user=self.USERNAME,
            pem=self.PEM)

    def _update_tags(self):
        self.report('updating instance tags')
        i = self._get_instance()
        json = self.to_json(simple=True)
        tags = dict(
            description = json['service_description'],)
        #tags.update(..)
        i.add_tags(tags)

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
        with lcd(self.SERVICE_ROOT):
            pfile = tempfile.mktemp(suffix='.tgz')
            # build a local tarball to copy and unzip on the remote side
            api.local('tar -czf {0} puppet/ '.format(pfile))
        return pfile

    def provision_ip(self, ip, fname=None):
        """ """
        self.report('installing build-essentials & puppet', section=True)
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
        remote_user_home = '/home/' + self.USERNAME
        with util.ssh_ctx(ip, user=self.USERNAME, pem=self.PEM):
            with lcd(self.SERVICE_ROOT):
                # if clean==True, in the call below, the puppet deps
                # which were installed in the `setup` phase would be
                # destroyed.  not what is wanted for provisioning!
                self.copy_puppet(clean=False)
                self.report("Provision list for this service: {0}".format(
                            provision_list), section=True)
                for relative_puppet_file in provision_list:
                    self.report('provision_list[{0}]: "{1}"'.format(
                        provision_list.index(relative_puppet_file),
                        relative_puppet_file))
                    util._run_puppet(
                        relative_puppet_file,
                        parser=self.PUPPET_PARSER,
                        facts=self.facts,
                        )
            self._restart_supervisor()

    def _clean_tmp_dir(self):
        """ necessary because puppet librarian is messy """
        tdir = os.path.join(self.SERVICE_ROOT, 'puppet', '.tmp')
        if os.path.exists(tdir):
            #'<root>/puppet/.tmp should be nixed'
            shutil.rmtree(tdir)

    def setup_ip(self, ip):
        self._update_tags()
        self._setup_buckets()
        self._setup_eips()
        self.report('installing build-essentials & puppet', section=True)
        self._clean_tmp_dir()
        with util.ssh_ctx(ip, user=self.USERNAME, pem=self.PEM):
            with lcd(self.SERVICE_ROOT):
                run('sudo apt-get update > /dev/null')
                self._bootstrap_dev()
                self.copy_puppet()
                self._bootstrap_puppet(force=True)
                for setup_item in self.SETUP_LIST:
                    self.report('setup_list[{0}]: "{1}"'.format(
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
        tmp  = self.SERVICE_DEFAULTS.copy()
        json = self._template_data(simple=True)
        tmp.update(
            dict(supervisor_user=json['supervisor_user'],
                 supervisor_pass=json['supervisor_pass'],
                 supervisor_port=json['supervisor_port']))
        return tmp

    def s3(self):
        """ show summary of s3 information for this service """
        buckets = self._setup_buckets(quiet=True).items()
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

    def _setup_buckets(self, quiet=False):
        report = self.report if not quiet else lambda *args, **kargs: None
        report('setting up any s3 buckets this service requires')
        conn = self._s3_conn
        tmp = {}
        for name in self.S3_BUCKETS:
            report("setting up s3 bucket: {0}".format(name))
            tmp[name] = conn.create_bucket(name, location=self.S3_LOCATION)
        return tmp

    def _setup_eips(self, quiet=False):
        report = self.report if not quiet else lambda *args, **kargs: None
        report('setting up any elastic IPs this service requires')
        tmp = {}
        for alloc_id in self.ELASTIC_IPS:
            report("setting up elastic IP: {0}".format(alloc_id))
            addr = self.conn.get_all_addresses(
                filters=dict(allocation_id=alloc_id)) + \
                self.conn.get_all_addresses(filters=dict())
            if not addr or len(addr)>1:
                err = "Expected exactly one EIP would match filter, got {0}"
                err = err.format(addr)
                raise SystemExit(err)
            addr = addr[0]
            status = self._status()
            instance_id = status['instance'].id
            if addr.instance_id is None:
                addr.associate(instance_id=instance_id)
                report(" + {0}: {1}".format(addr.allocation_id, addr))
            else:
                report(" - already assigned: {0}: {1}".format(
                    addr.allocation_id, addr))
        return tmp

    def run(self, command):
        """ run command on service host """
        with util.ssh_ctx(
            self._status()['ip'],
            user=self.USERNAME,
            pem=self.PEM):
            run(command)

    def copy_puppet(self, clean=True):
        """ copy puppet code to remote host (refreshes any dependencies) """
        with util.ssh_ctx(
            self._status()['ip'],
            user=self.USERNAME,
            pem=self.PEM):
            remote_user_home = '/home/' + self.USERNAME
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
                    api.run('tar -zxf {0} && rm "{0}"'.format(os.path.basename(pfile)))
            finally:
                api.local('rm "{0}"'.format(pfile))

    def reboot(self):
        """ TODO: blocking until reboot is complete? """
        self.report('rebooting service')
        data = self._status()
        if data['status'] == 'running':
            with util.ssh_ctx(data['ip'], user=self.USERNAME, pem=self.PEM):
                run('sudo reboot')
        else:
            self.report("service does not appear to be running")

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
        blacklist = 'fabric_commands'.split()
        out = [x for x in dir(self.__class__) if x==x.upper()]
        out = [ [x.lower(), getattr(self.__class__, x)] for x in out ]
        out = dict(out)
        if not simple:
            data = self._status()
            extra = dict(host=self._host(data), ip=data['ip'],)
            out.update(extra)
        [ out.pop(x, None) for x in blacklist ]
        return out

    # TODO: cache for when simple is false
    def _template_data(self, simple=False):
        """ reflects the template information back into itself """
        template_data = self.to_json(simple=simple)
        template_data.update(**self.SERVICE_DEFAULTS)
        for k,v in template_data['service_defaults'].items():
            if isinstance(v, basestring):
                template_data['service_defaults'][k] = v.format(**template_data)
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

    def _check(self):
        out = {}
        # include relevant sections of status results
        #for x in 'status eb_health eb_status'.split():
        #    if x in data:
        #        out['aws://'+x] = ['read', data[x]]
        health_checks = []
        for check_name, (_type, url_t) in self.HEALTH_CHECKS.items():
            check_obj = checks.Check(url_t=url_t, check_type=_type, name=check_name)
            health_checks.append(check_obj)
        for check_obj in health_checks:
            check_obj.run(self)
        self._display_checks(health_checks)

    def shell(self):
        return util.shell(
            conn=self.conn, Service=self, service=self)

    def show_facts(self):
        print self.facts

    def show_instances(self):
        """ show all ec2 instances """
        util.show_instances(conn=self.conn)

    @staticmethod
    def is_port_open(host, port):
        """ TODO: refactor into ymir.utils. this is used by ymir.checks """
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, int(port)))
        return result == 0
