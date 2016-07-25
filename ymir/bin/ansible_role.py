# -*- coding: utf-8 -*-
""" ymir.bin.ansible_role

    The missing ansible-role command, applying a single role without
    editing a playbook.
"""
import os
import sys
import shutil
import tempfile
from argparse import ArgumentParser
from fabric import api
from ymir.base import report as base_report
from ymir.version import __version__
from ymir import util

report = lambda *args, **kargs: base_report(
    'ansible-role-apply', *args, **kargs)


def get_parser():
    """ creates the parser for the ymir command line utility """
    parser = ArgumentParser(prog=os.path.split(sys.argv[0])[-1])
    parser.add_argument(
        'rolename',
        metavar='role_name', type=str, nargs=1,
    )
    parser.add_argument(
        '--module-path', '-M',
        help='ansible module-path')
    parser.add_argument(
        '--env', help='JSON env for role-application')
    return parser


def entry(settings=None):
    """ Main entry point """
    base_report('ymir', 'version {0}'.format(__version__))
    parser = get_parser()
    prog_args, extra_ansible_args = parser.parse_known_args(sys.argv[1:])
    role_name = prog_args.rolename.pop()
    module_path = prog_args.module_path
    temporary = False
    if not module_path:
        module_path = tempfile.mkdtemp()
        temporary = True
        report("ansible module-path not given, using {0}".format(module_path))
    else:
        extra_ansible_args += ['--module-path', module_path]
    import shellescape
    extra_ansible_args = [
        shellescape.quote(x) if ' ' in x else x
        for x in extra_ansible_args]
    # raise Exception, extra_ansible_args
    role_dir = os.path.join(module_path, 'roles')
    if not os.path.exists(role_dir):
        msg = "ansible role-dir does not exist at '{0}', creating it"
        report(msg.format(role_dir))
        api.local('mkdir -p "{0}"'.format(role_dir))
    try:
        success = util._ansible.apply_ansible_role(
            role_name, role_dir,
            ansible_args=extra_ansible_args,
            report=report)
        if not success and temporary:
            report("next time pass --module-path if you "
                   "want to avoid redownloading the role")
    finally:
        if temporary:
            shutil.rmtree(module_path)
    print prog_args, extra_ansible_args
