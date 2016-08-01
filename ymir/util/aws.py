# -*- coding: utf-8 -*-
""" ymir.util.aws
    boto helpers for doing various AWS stuff
"""
import os
import time

import boto.ec2
from boto.exception import EC2ResponseError
from boto.provider import ProfileNotFoundError
from fabric import colors

from ymir import data as ydata
from ._report import eprint


def get_instance_by_id(id, conn):
    """ return the instance for the given ID """
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
    """ get ec2 connection for aws API """
    region = os.environ.get('AWS_REGION', region)
    try:
        conn = boto.ec2.connect_to_region(
            region,
            profile_name=os.environ['AWS_PROFILE'])
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
            eprint(msg)
    return conn


def show_instances(conn=None):
    """ shows all AWS instances on the given connection """
    conn = conn or get_conn()
    results = get_tags(None, conn).items()
    for i, tags in results:
        if i:
            eprint(i)
        for k in tags:
            eprint('  ', k, tags[k])
    if not results:
        eprint("nothing to show")


def get_instance_by_name(name, conn):
    """ returns the id for the given instance """
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
        eprint('  polling reservation [status is "pending"]')
        time.sleep(4)
        status = instance.update()


def _block_while_terminating(instance, conn):
    """ """
    eprint('  terminating instance:', instance)
    assert get_instance_by_id(instance.id, conn) is not None
    conn.terminate_instances([instance.id])
    time.sleep(2)
    while get_instance_by_id(instance.id, conn):
        eprint('  polling for terminate completion')
        time.sleep(3)
    eprint('  terminated successfully')


def catch_ec2_error(fxn):
    """ """
    try:
        fxn()
    except EC2ResponseError as e:
        eprint(colors.red('failed:') + str([e, fxn]))
    else:
        eprint(ydata.OK)


def get_keypair_names(conn=None):
    """ return all keypair names associated with current $AWS_PROFILE """
    conn = conn or get_conn()
    return [k.name for k in conn.get_all_key_pairs()]
