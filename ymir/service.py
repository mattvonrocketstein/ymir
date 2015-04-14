""" ymir.service
"""
import os, time
import socket
import shutil, webbrowser
import logging

import boto

import fabric
from fabric.colors import blue
from fabric.contrib.files import exists
from fabric.api import lcd, settings, run, put, cd

from ymir import util
from ymir import checks
from ymir.base import Reporter
from ymir.util import show_instances
from ymir.data import DEFAULT_SUPERVISOR_PORT

logging.captureWarnings(True)

class AbstractService(Reporter):
    S3_BUCKETS      = []

    # not DRY, see also:
    #  puppet/modules/ymir/templates/ymir_motd.erb
    #  puppet/modules/ymir/templates/supervisord.conf
    SUPERVISOR_USER = ''
    SUPERVISOR_PASS = ''
    SUPERVISOR_PORT = '9001'
    SERVICE_DEFAULTS = {}

    INSTANCE_TYPE   = 't1.micro'
    SERVICE_ROOT    = None
    PEM             = None
    USERNAME        = None
    SECURITY_GROUPS = None
    APP_NAME        = None
    ORG_NAME        = None
    ENV_NAME        = None

    HEALTH_CHECKS = {}
    INTEGRATION_CHECKS = {}

    FABRIC_COMMANDS = [ 'status', 'ssh', 'create',
                        'setup', 's3', 'shell',
                        'provision', 'show', 'check',
                        'run', 'test', 'show_instances' ]

    def fabric_install(self):
        import fabfile
        for x in self.FABRIC_COMMANDS:
            try:
                tmp = getattr(fabfile, x)
            except AttributeError:
                setattr(fabfile,x,getattr(self,x))
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
        return super(AbstractService, self)._report_name() + \
                   ' Service'


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
        run('sudo apt-get install -y git build-essential')
        run('sudo apt-get install -y puppet ruby-dev')


    def report(self, msg, *args, **kargs):
        """ 'print' shortcut that includes some color and formatting """
        if 'section' in kargs:
            print '-'*80
        template = '\x1b[31;01m{0}:\x1b[39;49;00m {1} {2}'
        name = self._report_name()
        # if Service subclasses are embedded directly into fabfiles, there
        # is a need for a lot of private variables to control the namespace
        # fabric publishes as commands.
        name = name.replace('_', '')
        print template.format(
            name,
            msg, args or '')

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
        self.report("  bootstrapping puppet on remote host")
        util._run_puppet('puppet/modules/ymir/install_librarian.pp')
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
            self.report('no instance is running for this Service, create it first')

    def provision(self):
        """ provision this service """
        self.report('provisioning')
        data = self._status()
        if data['status']=='running':
            return self.provision_ip(data['ip'])
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
        data = self._status()
        for check_name in self.HEALTH_CHECKS:
            check, url = self.HEALTH_CHECKS[check_name]
            self._show_url(url.format(**self._template_data()))

    def create(self, force=False):
        """ create new instance of this service ('force' defaults to False)"""
        self.report('creating', section=True)
        conn = self.conn
        i = util.get_instance_by_name(self.NAME, conn)
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

        reservation = conn.run_instances(
            image_id=self.AMI,
            key_name=self.KEY_NAME,
            instance_type=self.INSTANCE_TYPE,
            security_groups = self.SECURITY_GROUPS,
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
        try:
            self.setup()
        except fabric.exceptions.NetworkError:
            time.sleep(4)
            self.setup()
        self.provision()

    def ssh_ctx(self):
        return util.ssh_ctx(
            self._status()['ip'],
            user=self.USERNAME,
            pem=self.PEM)

    def provision_ip(self, ip):
        self.report('installing build-essentials & puppet', section=True)
        tdir = os.path.join(self.SERVICE_ROOT, 'puppet', '.tmp')
        if os.path.exists(tdir):
            #'<root>/puppet/.tmp should be nixed'
            shutil.rmtree(tdir)
        with util.ssh_ctx(ip, user=self.USERNAME, pem=self.PEM):
            with lcd(self.SERVICE_ROOT):
                put('puppet', '/home/'+self.USERNAME)
                self.report("custom config for this Service: ",
                            self.PROVISION_LIST, section=True)
                for relative_puppet_file in self.PROVISION_LIST:
                    util._run_puppet(relative_puppet_file)
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

    def s3(self):
        """ show summary of s3 information for this service"""
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
        #from smashlib import embed; embed()

    @property
    def _s3_conn(self):
        return boto.connect_s3()

    def _setup_buckets(self, quiet=False):
        conn = self._s3_conn
        tmp = {}
        report = self.report if not quiet else lambda *args, **kargs: None
        for name in self.S3_BUCKETS:
            report("setting up s3 bucket: {0}".format(name))
            tmp[name] = conn.create_bucket(name, location=self.S3_LOCATION)
        return tmp

    def run(self, command):
        """ run command on service host """
        with util.ssh_ctx(
            self._status()['ip'],
            user=self.USERNAME,
            pem=self.PEM):
            run(command)

    def copy_puppet(self):
        """ copy puppet code to remote host (refreshes any dependencies) """
        with util.ssh_ctx(
            self._status()['ip'],
            user=self.USERNAME,
            pem=self.PEM):
            with lcd(self.SERVICE_ROOT):
                self.report('  flushing remote puppet codes and refreshing')
                run("rm -rf puppet")
                put('puppet', '/home/' + self.USERNAME)
                self._bootstrap_puppet(force=True)

    def setup_ip(self, ip):
        self.report('setting up any s3 buckets this service requires',
                    section=True)
        self._setup_buckets()
        self.report('installing build-essentials & puppet', section=True)
        tdir = os.path.join(self.SERVICE_ROOT, 'puppet', '.tmp')
        if os.path.exists(tdir):
            #'<root>/puppet/.tmp should be nixed'
            shutil.rmtree(tdir)
        with util.ssh_ctx(ip, user=self.USERNAME, pem=self.PEM):
            with lcd(self.SERVICE_ROOT):
                run('sudo apt-get update')
                self._bootstrap_dev()
                self.copy_puppet()
                for setup_item in self.SETUP_LIST:
                    self.report('setup_list[{0}] "{1}"'.format(
                        self.SETUP_LIST.index(setup_item),
                        setup_item
                        ))
                    util._run_puppet(setup_item)

    def reboot(self):
        """ TODO: blocking until reboot is complete? """
        self.report('rebooting service')
        data = self._status()
        if data['status'] == 'running':
            with util.ssh_ctx(data['ip'], user=self.USERNAME, pem=self.PEM):
                run('sudo reboot')
        else:
            self.report("service does not appear to be running")

    def check(self):
        """ reports health for this service """
        self.report('checking health')
        data = self._status()
        if data['status'] == 'running':
            return self.check_data(data)
        else:
            self.report('no instance is running for this'
                        ' Service, create it first')

    def test(self):
        """ runs integration tests for this service """
        self.report('running integration tests')
        data = self._status()
        if data['status'] == 'running':
            return self._test_data(data)
        else:
            self.report('no instance is running for this'
                        ' Service, start (or create) it first')

    def _host(self, data=None):
        """ todo: move to beanstalk class """
        data = data or self._status()
        return data.get(
            'eb_cname',
            data.get('ip'))

    def _show_url(self, url):
        data = self._status()
        url = url.format(host=self._host(data), ip=data['ip'])
        self.report("showing: {0}".format(url))
        webbrowser.open(url)

    def to_json(self,simple=False):
        out = [x for x in dir(self.__class__) if x==x.upper()]
        out = [ [x.lower(), getattr(self.__class__,x)] for x in out ]
        out = dict(out)
        if not simple:
            data = self._status()
            out.update(dict(host=self._host(data), ip=data['ip'],))
        return out

    def _template_data(self):
        template_data = self.to_json()
        #raise Exception, template_data['service_defaults']
        template_data.update(**self.SERVICE_DEFAULTS)
        return template_data

    def _run_check(self, check_type, url):
        """ """
        data = self._template_data()
        url = url.format(**data)
        try:
            check = getattr(checks, check_type)
        except AttributeError:
            err = 'Not sure how to run "{0}" check on {1}: '.format(
                check_type, url)
            raise SystemExit(err)
        else:
            _url, message = check(self, url)
            return _url, message

    def _test_data(self, data):
        """ run integration tests given 'status' data """
        out = {}
        ip = data['ip']
        self.check_data(data)
        for check_name  in self.INTEGRATION_CHECKS:
            check_type, url = self.INTEGRATION_CHECKS[check_name]
            _url, result = self._run_check(check_type, url)
            out[_url] = [check_type, result]
        self._display_checks(out)


    def _display_checks(self, check_data):
        #from smashlib import embed; embed()
        for url in check_data:
            check_type, msg = check_data[url]
            self.report(' .. {0} {1} -- {2}'.format(
                blue('[?{0}]'.format(check_type)),
                url, msg))

    def check_data(self, data):
        out = {}
        ip = data['ip']
        # include relevant sections of status results
        for x in 'status eb_health eb_status'.split():
            if x in data:
                out['aws://'+x] = ['read', data[x]]
        for check_name in self.HEALTH_CHECKS:
            check_type, url = self.HEALTH_CHECKS[check_name]
            _url, result = self._run_check(check_type, url)
            out[_url] = [check_type, result]
        self._display_checks(out)

    def shell(self):
        return util.shell(conn=self.conn, Service=self)

    def show_instances(self):
        """ show all ec2 instances """
        show_instances(conn=self.conn)

    @staticmethod
    def is_port_open(host, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, int(port)))
        return result == 0

    def _validate_sgs(self):
        import time
        time.sleep(10)
        from boto.exception import EC2ResponseError
        try:
            rs = self.conn.get_all_security_groups(self.SECURITY_GROUPS)
        except EC2ResponseError:
            return "could not find security groups: "\
                   + str(self.SECURITY_GROUPS)


    def _validate_keypairs(self):
        errors = []
        if not os.path.exists(os.path.expanduser(self.PEM)):
            errors.append('  ERROR: pem file is not present: ' + self.PEM)
        keys = [k.name for k in util.get_conn().get_all_key_pairs()]
        if self.KEY_NAME not in keys:
            errors.append('  ERROR: aws keypair not found: ' + self.KEY_NAME)
        return errors or None
