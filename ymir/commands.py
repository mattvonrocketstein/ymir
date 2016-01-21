# -*- coding: utf-8 -*-
""" ymir.commands
"""

import os

import boto
import addict
import demjson

from fabric.colors import red, green
from fabric.contrib.console import confirm

from ymir import util
from ymir import api as yapi

from ymir.schema import SGFileSchema
from ymir.security_groups import sg_sync

OK = green('  ok')
YMIR_SRC = os.path.dirname(__file__)

import logging
logger = logging.getLogger(__name__)


def ymir_sg(args):
    def unpack_rule(r):
        return addict.Dict(
            ip_protocol=r[0],
            from_port=r[1],
            to_port=r[2],
            cidr_ip=r[3])

    def supports_ssh(_rules):
        """ FIXME: dumb heuristic """
        for _rule in _rules:
            _rule = unpack_rule(_rule)
            if _rule.to_port == 22:
                return True
        return False

    force = args.force
    fname = os.path.abspath(args.sg_json)
    if not os.path.exists(fname):
        err = 'security group json @ "{0}" does not exist'.format(fname)
        raise SystemExit(err)
    with open(fname) as fhandle:
        json = demjson.decode(fhandle.read())
    logger.debug("loaded json from {0}".format(fname))
    logger.debug(json)
    SGFileSchema(json)
    logger.debug("validated json from {0}".format(fname))

    # one last sanity check
    rules = [entry['rules'] for entry in json]
    if not force and not \
       any([supports_ssh(x) for x in rules]):
        raise SystemExit("No security group mentions ssh!  "
                         "Unless you pass --force "
                         "ymir assumes this is an error")
    for entry in json:
        name = entry['name']
        descr = entry['description']
        rules = entry['rules']
        sg_sync(name=name, description=descr, rules=rules,
                )


def ymir_shell(args):
    """ """
    service = yapi.load_service_from_json()
    user_ns = dict(
        conn=util.get_conn(),
        service=service)
    from smashlib import embed
    embed(user_ns=user_ns,)


def ymir_load(args, interactive=True):
    """ """
    raise RuntimeError(
        "this function is deprecated.  use ymir.load_service_from_json")


def ymir_init(args):
    """ responsible for executing the 'ymir init' command. """
    init_dir = os.path.abspath(args.init_dir)
    if os.path.exists(init_dir) and not args.force:
        err = ('this command is used to initialize a '
               'ymir project, the directory should'
               ' not already exist.')
        raise SystemExit(err)
    init_dir == os.getcwd()
    if os.path.exists(init_dir) and args.force:
        folder = init_dir
        for the_file in os.listdir(folder):
            file_path = os.path.join(folder, the_file)
            try:
                if os.path.isfile(file_path):
                    os.unlink(file_path)
            except Exception, e:
                print e
    skeleton_dir = os.path.join(YMIR_SRC, 'skeleton')
    if not os.path.exists(skeleton_dir):
        err = ('cannot find ymir skeleton project.  '
               'your ymir installation might be broken :(')
        raise SystemExit(err)
    print red('creating directory: ') + init_dir
    print red('copying ymir skeleton: '), skeleton_dir
    util.copytree(skeleton_dir, init_dir)


def ymir_keypair(args):
    """ """
    name = args.keypair_name
    ec2 = boto.connect_ec2()
    if not args.force:
        q = ('\nCreate new AWSkeypair "{0}" (the '
             'results will be saved to "{1}.pem" '
             'in the working directory)?\n\n')
        try:
            result = confirm(q.format(name, name))
        except KeyboardInterrupt:
            return
        if not result:
            return
        # boto.ec2.keypair.KeyPair
    key = ec2.create_key_pair(name)
    key.save(os.getcwd())


def ymir_eip(args):
    ec2 = boto.connect_ec2()
    if not args.force:
        q = ('\nCreate new elastic ip (the '
             'ID for the result will be shown on stdout)?\n\n')
        try:
            result = confirm(q.format())
        except KeyboardInterrupt:
            return
        if not result:
            return
    addr = ec2.allocate_address()
    print addr.allocation_id


def ymir_freeze(args):
    msg = 'not implemented yet'
    print msg
    raise SystemExit(msg)
