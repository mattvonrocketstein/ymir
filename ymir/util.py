"""
"""
import os, time
import boto.ec2
from fabric.api import local, settings, run
from ymir.data import STATUS_DEAD, DEBUG

def _run_puppet(_fname):
    """ must be run within a fabric ssh context """
    run("sudo puppet apply {0} --modulepath={1}/modules {2}".format(
        '--debug' if DEBUG else '',
        os.path.dirname(_fname),
        _fname))

def shell(conn=None, **namespace):
    conn = conn or get_conn()
    try:
        from smashlib import embed; embed(user_ns=namespace)
    except ImportError:
        print 'you need smashlib or ipython installed to run the shell'

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

def get_conn(key_name=None, region='us-east-1'):
    #print 'creating ec2 connection'
    conn = boto.ec2.connect_to_region("us-east-1")
    if key_name is not None:
        keypair = conn.get_key_pair(key_name)
        if keypair is None:
            print "WARNING: could not retrieve default keypair '{0}'!!".format(key_name)
    return conn

def show_instances(conn):
    for i, tags in get_tags(None, conn).items():
        print i
        for k in tags:
            print '  ', k, tags[k]

def get_instance_by_name(name, conn):
    """ returns the id for the instance"""
    for i, tags in get_tags(None, conn).items():
        if tags.get('Name') == name and tags['status'] not in STATUS_DEAD:
            return conn.get_only_instances([i.id])[0]

def get_tags(instance, conn):
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

def _block_while_pending(instance):
    # Check up on its status every so often
    status = instance.update()
    while status == 'pending':
        print '  polling reservation [status is "pending"]'
        time.sleep(4)
        status = instance.update()

def _block_while_terminating(instance, conn):
    print '  terminating instance:', instance
    assert get_instance_by_id(instance.id, conn) is not None
    conn.terminate_instances([instance.id])
    time.sleep(2)
    while get_instance_by_id(instance.id, conn):
        print '  polling for terminate completion'
        time.sleep(3)
    print '  terminated successfully'
