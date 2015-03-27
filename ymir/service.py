""" ymir.service
"""
import os, time
import socket
import shutil, webbrowser

import boto
import fabric
import requests

from fabric.contrib.files import exists
from fabric.api import lcd, settings, run, put, cd

import logging
logging.captureWarnings(True)

from ymir import util
from ymir.data import DEFAULT_SUPERVISOR_PORT
from .base import Reporter

class AbstractService(Reporter):
    S3_BUCKETS      = []
    SUPERVISOR_USER = ''
    SUPERVISOR_PASS = ''
    INSTANCE_TYPE   = 't1.micro'
    SERVICE_ROOT    = None
    PEM             = None
    USERNAME        = None
    SECURITY_GROUPS = None
    WEBPAGES        = ['supervisor']
    FABRIC_COMMANDS = ['status', 'ssh', 'create', 'setup',
                       's3', 'provision', 'show', 'check']

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
        return super(AbstractService,self)._report_name() + \
                   +'-Service'

    def __init__(self, conn=None):
        self.conn = conn or util.get_conn()
        required_class_vars = 'PEM USERNAME SECURITY_GROUPS SERVICE_ROOT'
        required_class_vars =required_class_vars.split()
        for var in required_class_vars:
            err = 'subclassers must override '+var
            assert getattr(self,var) is not None, err

    def _bootstrap_dev(self):
        """ """
        run('sudo apt-get install -y git build-essential')
        run('sudo apt-get install -y puppet ruby-dev')

    def _report_name(self):
        return self.__class__.__name__+'-Service'

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
        util._run_puppet('puppet/install_librarian.pp')
        _init_puppet("puppet")

    def setup(self):
        """ setup service (operation should be after 'create', before 'provision')"""
        self.report('setting up')
        cm_data = self.status()
        if cm_data['status'] == 'running':
            self.setup_ip(cm_data['ip'])
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
            util.connect(cm_data['ip'], username='ubuntu', pem=self.PEM)
        else:
            self.report("no instance found")

    def show(self):
        """ open health-check webpages for this service in a browser """
        self.report('showing webpages')
        data = self._status()
        for page in self.WEBPAGES:
            webbrowser.open(data[page])

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
                put('puppet', '/home/ubuntu')
                self.report("custom config for this Service: ",
                            self.PUPPET, section=True)
                for relative_puppet_file in self.PUPPET:
                    util._run_puppet(relative_puppet_file)
                print '  restarting everything'
                retries = 3
                restart = lambda: run("sudo /etc/init.d/supervisor restart").return_code
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
            self.report("  {0} ({1} items)".format(bname, len(keys)))
            for key in keys:
                print ("  {0} (size {1})".format(
                    key.name, key.size))

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
                self.report('  flushing remote puppet codes and refreshing')
                run("rm -rf puppet")
                put('puppet', '/home/ubuntu')
                self._bootstrap_dev()
                self._bootstrap_puppet(force=True)
                util._run_puppet(self.PUPPET_SETUP)

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
        if data['status']=='running':
            return self.check_ip(data['ip'], data)
        else:
            self.report('no instance is running for this'
                        ' Service, create it first')

    def check_ip(self, ip, data):
        for x in self.WEBPAGES:
            try:
                resp = requests.get(data[x], timeout=2, verify=False)
            except requests.exceptions.ConnectionError,e:
                if 'timed out' in str(e):
                    msg = 'timed out'
                else:
                    msg = str(e)
            else:
                msg = str(resp.status_code)
            self.report(' .. "{0}": {1}'.format(x, msg))

    def shell(self):
        return util.shell(conn=self.conn, Service=self)

    @staticmethod
    def is_port_open(host, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, port))
        return result == 0
