""" ymir:

    this is a module containing utility functions/classes for working
    with EC2 leveraging a combination of fabric, boto, & puppet.

    TODO: support elastic IP's
"""
import os, time
import socket
import shutil, webbrowser
import fabric
import boto.ec2
import requests

from fabric.contrib.files import exists
from fabric.api import lcd, local, settings, run, put, cd

import logging
logging.captureWarnings(True)

# begin data
################################################################################

DEBUG = False
DEFAULT_SUPERVISOR_PORT = 9001 # supervisor WUI port
PROJECT_ROOT = os.path.dirname(__file__)
STATUS_DEAD = ['terminated', 'shutting-down']

# begin ec2 utility functions
################################################################################

class Util(object):
    """ this class basically masquerades as a module,
        every function could be a staticmethod
    """
    def _run_puppet(self, _fname):
        """ must be run within a fabric ssh context """
        run("sudo puppet apply {0} --modulepath={1}/modules {2}".format(
            '--debug' if DEBUG else '',
            os.path.dirname(_fname),
            _fname))

    def shell(self, conn=None, **namespace):
        conn = conn or util.get_conn()
        try:
            from smashlib import embed; embed(user_ns=namespace)
        except ImportError:
            print 'you need smashlib or ipython installed to run the shell'

    def connect(self, ip, username='ubuntu', pem=None):
        cmd = "ssh -l {0} {1}".format(username, ip)
        if pem is not None:
            cmd += ' -i {0}'.format(pem)
        with settings(warn_only=True):
            local(cmd)

    def ssh_ctx(self, ip, user='ubuntu', pem=None):
        """ context manager for use with fabric """
        ctx = dict(user=user, host_string=ip)
        if pem is not None:
            ctx.update(key_filename=pem)
        return settings(**ctx)

    def get_instance_by_id(self, id, conn):
        """ returns the id for the instance"""
        tmp = conn.get_only_instances([id])
        if not tmp:
            return
        else:
            # WARNING: do NOT use STATUS_DEAD here,
            #          block_while_terminating depends
            #          on this working as written
            if tmp[0].update() not in ['terminated']:
                return tmp

    def get_conn(self, key_name=None, region='us-east-1'):
        #print 'creating ec2 connection'
        conn = boto.ec2.connect_to_region("us-east-1")
        if key_name is not None:
            keypair = conn.get_key_pair(key_name)
            if keypair is None:
                print "WARNING: could not retrieve default keypair '{0}'!!".format(key_name)
        return conn

    def show_instances(self, conn):
        for i, tags in util.get_tags(None, conn).items():
            print i
            for k in tags:
                print '  ', k, tags[k]

    def get_instance_by_name(self, name, conn):
        """ returns the id for the instance"""
        for i, tags in util.get_tags(None, conn).items():
            if tags.get('Name') == name and tags['status'] not in STATUS_DEAD:
                return conn.get_only_instances([i.id])[0]

    def get_tags(self, instance, conn):
        """ returns { instance_id: instance_tags }"""
        assert conn is not None
        if instance is None:
            reservations = conn.get_only_instances()
        else:
            reservations = conn.get_only_instances([instance.id])
        out = {}
        for inst in reservations:
            tags = inst.tags.copy()
            tags.update(status=inst.update())
            out[inst] = tags
        return out

    def _block_while_pending(self, instance):
        # Check up on its status every so often
        status = instance.update()
        while status == 'pending':
            print '  polling reservation [status is "pending"]'
            time.sleep(4)
            status = instance.update()

    def _block_while_terminating(self, instance, conn):
        print '  terminating instance:', instance
        assert util.get_instance_by_id(instance.id, conn) is not None
        conn.terminate_instances([instance.id])
        time.sleep(2)
        while util.get_instance_by_id(instance.id, conn):
            print '  polling for terminate completion'
            time.sleep(3)
        print '  terminated successfully'

util = Util()


class AbstractStack(object):

    WEBPAGES = ['supervisor']
    INSTANCE_TYPE = 't1.micro'
    STACK_ROOT = None
    PEM = None
    USERNAME = None
    SECURITY_GROUPS = None

    def __init__(self, conn=None):
        self.conn = conn or util.get_conn()
        assert self.STACK_ROOT is not None, 'subclassers must override STACK_ROOT'
        assert self.PEM is not None, 'subclassers must override PEM'
        assert self.USERNAME is not None, 'subclassers must override USERNAME'
        assert self.SECURITY_GROUPS is not None, 'subclassers must override SECURITY_GROUPS'

    def _bootstrap_dev(self):
        run('sudo apt-get install -y git build-essential')
        run('sudo apt-get install -y puppet ruby-dev')

    def report(self, msg, *args, **kargs):
        if 'section' in kargs:
            print '-'*80
        template = '\x1b[31;01m{0}-Stack:\x1b[39;49;00m {1} {2}'
        print template.format(self.__class__.__name__, msg, args or '')

    def status(self):
        self.report('checking status', section=True)
        result = self._status()
        for k,v in result.items():
            self.report('  {0}: {1}'.format(k,v))
        return result

    def _status(self):
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
        self.report('setting up')
        cm_data = self.status()
        if cm_data['status']=='running':
            self.setup_ip(cm_data['ip'])
        else:
            self.report('no instance is running for this stack, create it first')

    def provision(self):
        self.report('provisioning')
        data = self.status()
        if data['status']=='running':
            return self.provision_ip(data['ip'])
        else:
            self.report('no instance is running for this stack, create it first')

    def ssh(self):
        self.report('connecting with ssh')
        cm_data = self.status()
        if cm_data['status'] == 'running':
            util.connect(cm_data['ip'], username='ubuntu', pem=self.PEM)
        else:
            self.report("no instance found")

    def show(self):
        self.report('showing webpages')
        data = self.status()
        for page in self.WEBPAGES:
            webbrowser.open(data[page])

    def create(self, force=False):
        self.report('creating', section=True)
        conn = self.conn
        i = util.get_instance_by_name(self.NAME, conn)
        if i is not None:
            self.report('  instance already exists: {0} ({1})'.format(i, i.update()))
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
        return util.ssh_ctx(self._status()['ip'], user=self.USERNAME, pem=self.PEM)

    def provision_ip(self, ip):
        self.report('installing build-essentials & puppet', section=True)
        tdir = os.path.join(self.STACK_ROOT, 'puppet', '.tmp')
        if os.path.exists(tdir):
            #'<root>/puppet/.tmp should be nixed'
            shutil.rmtree(tdir)
        with util.ssh_ctx(ip, user=self.USERNAME, pem=self.PEM):
            with lcd(self.STACK_ROOT):
                put('puppet', '/home/ubuntu')
                self.report("custom config for this stack: ",
                            self.PUPPET, section=True)
                for relative_puppet_file in self.PUPPET:
                    util._run_puppet(relative_puppet_file)
                print '  restarting everything'
                retries = 3
                restart = lambda: run("sudo /etc/init.d/supervisor restart").return_code
                with settings(warn_only=True):
                    result = restart()
                    count = 0
                    while result!=0 and count<retries:
                        msg = 'failed to restart supervisor.  trying again [{0}]'
                        msg = msg.format(count)
                        print msg
                        result = restart()
                        count += 1

    def setup_ip(self, ip):
        self.report('installing build-essentials & puppet', section=True)
        tdir = os.path.join(self.STACK_ROOT, 'puppet', '.tmp')
        if os.path.exists(tdir):
            #'<root>/puppet/.tmp should be nixed'
            shutil.rmtree(tdir)
        with util.ssh_ctx(ip, user=self.USERNAME, pem=self.PEM):
            with lcd(self.STACK_ROOT):
                run('sudo apt-get update')
                self.report('  flushing remote puppet codes and refreshing')
                run("rm -rf puppet")
                put('puppet', '/home/ubuntu')
                self._bootstrap_dev()
                self._bootstrap_puppet(force=True)
                util._run_puppet(self.PUPPET_SETUP)

    def check(self):
        self.report('checking health')
        data = self._status()
        if data['status']=='running':
            return self.check_ip(data['ip'], data)
        else:
            self.report('no instance is running for this stack, create it first')

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
        return util.shell(conn=self.conn, stack=self)

    @staticmethod
    def is_port_open(host, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        result = sock.connect_ex((host, port))
        return result == 0
