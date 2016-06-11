# -*- coding: utf-8 -*-
""" ymir.util

    Mostly AWS utility functions
"""

import os
import time
import shutil
import socket
from functools import wraps

from fabric import colors
import boto.ec2
from boto.provider import ProfileNotFoundError
from boto.exception import EC2ResponseError
from fabric import api
from fabric.contrib.files import exists as remote_exists

from ymir import data as ydata
from .backports import TemporaryDirectory

NOOP = lambda *args, **kargs: None

remote_path_exists = remote_exists
__all__ = [x.__name__ for x in [TemporaryDirectory, NOOP]]


def report(label, msg, *args, **kargs):
    """ 'print' shortcut that includes some color and formatting """
    if 'section' in kargs:
        print '-' * 80
    template = '\x1b[31;01m{0}:\x1b[39;49;00m {1} {2}'
    # if Service subclasses are embedded directly into fabfiles, there
    # is a need for a lot of private variables to control the namespace
    # fabric publishes as commands.
    label = label.replace('_', '')
    print template.format(label, msg, args or '')


def require_running_instance(fxn):
    """ NB: only for use with Service instance methods! """
    @wraps(fxn)
    def newf(self, *args, **kargs):
        cm_data = self._status()
        if cm_data['status'] == 'running':
            return fxn(self, *args, **kargs)
        else:
            self.report(
                "need an instance to run `{0}` command".format(fxn.__name__))
            self.report("no instance found!")
            return None
    return newf


def list_dir(dir_=None):
    """ returns a list of files in a directory (dir_) as absolute paths """
    dir_ = dir_ or api.env.cwd
    if not dir_.endswith('/'):
        dir_ += '/'
    string_ = api.run("for i in %s*; do echo $i; done" % dir_)
    files = string_.replace("\r", "").split("\n")
    return files


def shell(conn=None, **namespace):
    conn = conn or get_conn()
    try:
        from smashlib import embed
        embed(user_ns=namespace)
    except ImportError as e:
        print 'you need smashlib or ipython installed to run the shell!'
        print "original error: " + str(e)
        raise


def mosh(ip, username='ubuntu', pem=None):
    """ connect to remote host using mosh """
    assert ip is not None
    pem = '-i ' + pem if pem else ''
    cmd = 'mosh --ssh="ssh {pem}" {user}@{host}'.format(
        pem=pem, user=username, host=ip)
    with api.settings(warn_only=True):
        return api.local(cmd)


def ssh(ip, username='ubuntu', port='22', pem=None):
    """ connect to remote host using ssh """
    assert ip is not None
    if ':' in ip:
        ip, port = ip.split(':')
    cmd = "ssh -p {2} -l {0} {1}".format(username, ip, port)
    if pem is not None:
        cmd += ' -i {0}'.format(pem)
    with api.settings(warn_only=True):
        api.local(cmd)


def ssh_ctx(ip, user='ubuntu', pem=None):
    """ context manager for use with fabric """
    assert ip is not None
    ctx = dict(user=user, host_string=ip)
    if pem is not None:
        ctx.update(key_filename=pem)
    return api.settings(**ctx)


def get_instance_by_id(id, conn):
    """ returns the id for the instance """
    tmp = conn.get_only_instances([id])
    if not tmp:
        return
    else:
        # WARNING: do NOT use STATUS_DEAD here,
        #          block_while_terminating depends
        #          on this working as written
        if tmp[0].update() not in ['terminated']:
            return tmp


def has_gem(name):
    """ tests whether localhost has a gem by the given name """
    with api.quiet():
        x = api.local('gem list|grep {0}'.format(name), capture=True)
    error = x.return_code != 0
    return not error


def get_conn(key_name=None, region='us-east-1'):
    """ get ec2 connection for aws API """
    try:
        conn = boto.ec2.connect_to_region(
            region, profile_name=os.environ['AWS_PROFILE'])
    except (KeyError, boto.exception.NoAuthHandlerFound):
        err = ("ERROR: no AWS credentials could be found.\n  "
               "Set AWS_PROFILE environment variable, or "
               "use ~/.boto, then try again")
        raise SystemExit(err)
    except (ProfileNotFoundError,) as exc:
        err = ("ERROR: found AWS_PROFILE {0}, but boto raises "
               "ProfileNotFound.  Set AWS_PROFILE environment "
               "variable, or use ~/.boto, then try again.  Original"
               " Exception follows: {0}").format(exc)
        raise SystemExit(err)
    if key_name is not None:
        keypair = conn.get_key_pair(key_name)
        if keypair is None:
            msg = "WARNING: could not retrieve default keypair '{0}'!!"
            msg = msg.format(key_name)
            print msg
    return conn


def show_instances(conn):
    """ """
    for i, tags in get_tags(None, conn).items():
        print i
        for k in tags:
            print '  ', k, tags[k]


def get_instance_by_name(name, conn):
    """ returns the id for the instance """
    for i, tags in get_tags(None, conn).items():
        if tags.get('Name') == name and tags['status'] not in ydata.STATUS_DEAD:
            return conn.get_only_instances([i.id])[0]


def get_tags(instance, conn):
    """ returns { instance_id: instance_tags } """
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


def _block_while_pending(instance):
    """ """
    # Check up on its status every so often
    status = instance.update()
    while status == 'pending':
        print '  polling reservation [status is "pending"]'
        time.sleep(4)
        status = instance.update()


def _block_while_terminating(instance, conn):
    """ """
    print '  terminating instance:', instance
    assert get_instance_by_id(instance.id, conn) is not None
    conn.terminate_instances([instance.id])
    time.sleep(2)
    while get_instance_by_id(instance.id, conn):
        print '  polling for terminate completion'
        time.sleep(3)
    print '  terminated successfully'


def catch_ec2_error(fxn):
    """ """
    try:
        fxn()
    except EC2ResponseError as e:
        print colors.red('failed:') + str([e, fxn])
    else:
        print ydata.OK


def get_keypair_names(conn=None):
    """ return all keypair names associated with current $AWS_PROFILE """
    conn = conn or get_conn()
    return [k.name for k in conn.get_all_key_pairs()]


def get_or_guess_service_json_file(args=None):
    """ """
    service_json_file = os.environ.get(
        'YMIR_SERVICE_JSON',
        os.path.join(os.getcwd(), 'service.json'))
    if not os.path.exists(service_json_file):
        raise SystemExit("no service.json found")
    assert os.path.exists(service_json_file)
    return service_json_file


def unexpand(path):
    """ the opposite of os.path.expanduser """
    home = os.environ.get('HOME')
    if home:
        path = path.replace(home, '~')
    return path


def is_port_open(host, port):
    """ used by ymir.checks """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((host, int(port)))
    return result == 0

# http://stackoverflow.com/questions/1868714/how-do-i-copy-an-entire-directory-of-files-into-an-existing-directory-using-pyth


def copytree(src, dst, symlinks=False, ignore=None):
    """ shutil.copytree is broken/weird """
    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copytree(s, d, symlinks, ignore)
        else:
            if not os.path.exists(d) or \
                    os.stat(src).st_mtime - os.stat(dst).st_mtime > 1:
                shutil.copy2(s, d)
