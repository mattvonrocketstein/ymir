# -*- coding: utf-8 -*-
""" ymir.commands

    Entry points for commandline utilities
"""

import os
import copy
import logging

import boto
import demjson

from fabric.colors import red
from fabric.contrib.console import confirm

from ymir import util
from ymir import api as yapi
from ymir import validation
from ymir.schema import SGFileSchema
from ymir.security_groups import sg_sync
from ymir.base import report as _report

from ymir import data as ydata

logger = logging.getLogger(__name__)

report = lambda *args: _report("ymir.commands", *args)


def ymir_sg(args):
    def supports_ssh(_rules):
        """ a dumb heuristic to prevent people from
            creating inaccessible EC2 resources
        """
        for _rule in _rules:
            if _rule[2] == 22:
                return True
        return False

    def list_groups():
        print [sg.name for sg in util.get_conn().get_all_security_groups()]

    if args.list:
        return list_groups()
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
        sg_sync(name=name, description=descr, rules=rules,)


def ymir_validate(args):
    """ """
    default_service_json = os.path.join(os.getcwd(), 'service.json')
    default_vagrant_json = os.path.join(os.getcwd(), 'vagrant.json')
    default_service_json_found = os.path.exists(default_service_json)
    default_vagrant_json_found = os.path.exists(default_vagrant_json)
    default_files_found = default_vagrant_json_found or default_service_json_found
    if args.service_json is None and not default_files_found:
        err = ('either filename should be passed, '
               '$YMIR_SERVICE_JSON must be set, '
               'or ./service.json should exist')
        report(err)
        raise SystemExit(1)
    elif args.service_json is None and default_files_found:
        report("No service-description provided.  Found defaults:")
        if default_service_json_found:
            report("  {0}".format(default_service_json))
        if default_vagrant_json_found:
            report("  {0}".format(default_vagrant_json))
        if default_service_json_found:
            report("validating {0}".format(default_service_json))
            tmp_args = copy.copy(args)
            tmp_args.service_json = default_service_json
            ymir_validate(tmp_args)
        if default_vagrant_json_found:
            report("validating {0}".format(default_vagrant_json))
            tmp_args = copy.copy(args)
            tmp_args.service_json = default_vagrant_json
            ymir_validate(tmp_args)
    elif args.service_json:
        validation.validate(args.service_json, simple=False)


def ymir_shell(args):
    """ """
    service = yapi.load_service_from_json()
    report("starting shell")
    user_ns = dict(
        conn=util.get_conn(),
        service=service)
    report("namespace: \n\n{0}\n\n".format(user_ns))
    try:
        from smashlib import embed
    except ImportError:
        raise SystemExit("need smashlib should be installed first")
    embed(user_ns=user_ns,)


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
    skeleton_dir = ydata.YMIR_SKELETON
    if not os.path.exists(skeleton_dir):
        err = ('cannot find ymir skeleton project.  '
               'your ymir installation might be broken :(')
        raise SystemExit(err)
    print red('creating directory: ') + init_dir
    print red('copying ymir skeleton: '), skeleton_dir
    util.copytree(skeleton_dir, init_dir)


def ymir_list(args):
    """ responsible for executing the 'ymir list' command,
        which lists AWS resources associated with the current
        $AWS_PROFILE
    """
    if args.keypairs:
        print util.get_keypair_names()
    elif args.instances:
        print util.show_instances()
    else:
        msg = "not sure what to list."
        raise SystemExit(msg)


def ymir_keypair(args):
    """ responsible for executing the 'ymir keypair' command,
        which creates new AWS keypairs on demand
    """
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
