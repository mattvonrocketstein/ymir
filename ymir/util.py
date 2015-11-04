""" ymir.util

    Mostly AWS utility functions
"""

import shutil
import os, time
import boto.ec2

from fabric.api import settings, run, shell_env, env

from ymir.data import STATUS_DEAD

def list_dir(dir_=None):
    """returns a list of files in a directory (dir_) as absolute paths"""
    dir_ = dir_ or env.cwd
    if not dir_.endswith('/'):
        dir_+='/'
    string_ = run("for i in %s*; do echo $i; done" % dir_)
    files = string_.replace("\r","").split("\n")
    return files

def _run_puppet(_fname, parser=None, debug=False, puppet_dir=None, facts={}):
    """ must be run within a fabric ssh context """
    _facts = {}
    for fact_name, val in facts.items():
        if not fact_name.startswith('FACTER_'):
            _facts['FACTER_' + fact_name] = val
        else:
            _facts[fact_name] = val
    with shell_env(**_facts):
        # sudo -E preserves the invoking enviroment,
        # thus we are able to pass through the facts
        #run("sudo -E echo FACTER_naxos_fae_env")
        run("sudo -E puppet apply {parser} {debug} --modulepath={pdir}/modules {fname}".format(
            parser=('--parser '+parser) if parser else '',
            debug='--debug' if debug else '',
            pdir=puppet_dir or os.path.dirname(_fname),
            fname=_fname))

def shell(conn=None, **namespace):
    conn = conn or get_conn()
    try:
        from smashlib import embed; embed(user_ns=namespace)
    except ImportError,e:
        print 'you need smashlib or ipython installed to run the shell!'
        raise

def connect(ip, username='ubuntu', pem=None):
    cmd = "ssh -l {0} {1}".format(username, ip)
    if pem is not None:
        cmd += ' -i {0}'.format(pem)
    with settings(warn_only=True):
        local(cmd)

def ssh_ctx(ip, user='ubuntu', pem=None):
    """ context manager for use with fabric """
    ctx = dict(user=user, host_string=ip)
    if pem is not None:
        ctx.update(key_filename=pem)
    return settings(**ctx)

def get_instance_by_id(id, conn):
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

from fabric.api import quiet, local

def has_gem(name):
    """ TODO: move to goulash """
    with quiet():
        x = local('gem list|grep {0}'.format(name), capture=True)
    error = x.return_code != 0
    return not error

def get_conn(key_name=None, region='us-east-1'):
    #print 'creating ec2 connection'
    try:
        conn = boto.ec2.connect_to_region(region, profile_name=os.environ['AWS_PROFILE'])
    except (KeyError, boto.exception.NoAuthHandlerFound):
        err = ("ERROR: no AWS credentials could be found.\n  "
               "Set AWS_PROFILE environment variable, or use ~/.boto, then try again")
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
        if tags.get('Name') == name and tags['status'] not in STATUS_DEAD:
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

# TODO: move to goulash
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

def working_dir_is_ymir():
    return '.ymir' in os.listdir(os.getcwd())
