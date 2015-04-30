""" ymir.bin._ymir
"""

import os, sys, shutil
from argparse import ArgumentParser

import boto
import addict
from fabric.contrib.console import prompt, confirm#red,

from ymir.version import __version__
from ymir.commands import ymir_init, ymir_load, ymir_validate, ymir_freeze

from ymir.util import working_dir_is_ymir

def ymir_freeze(args):
    name = args.name
    _id = args.instance_id

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
        #boto.ec2.keypair.KeyPair
    key = ec2.create_key_pair(name)
    key.save(os.getcwd())

def get_parser():
    """ creates the parser for the ymir command line utility """
    parser = ArgumentParser(prog=os.path.split(sys.argv[0])[-1])
    subparsers = parser.add_subparsers(help='commands')
    help_parser = subparsers.add_parser('help', help='show ymir help')
    help_parser.set_defaults(subcommand='help')
    version_parser = subparsers.add_parser('version', help='show ymir version')
    version_parser.set_defaults(subcommand='version')
    shell_parser = subparsers.add_parser('shell', help='open interactive shell')
    shell_parser.set_defaults(subcommand='shell')

    keypair_parser = subparsers.add_parser('keypair', help='show ymir keypair')
    keypair_parser.set_defaults(subcommand='keypair')
    keypair_parser.add_argument(
        'keypair_name', metavar='keypair_name',
        type=str,
        help='a (new) keyname created on aws.  pem saved to ~/.ssh')
    keypair_parser.add_argument('-f','--force', action='store_true',
                   help='a (new) directory to initial a ymir project in')

    # build 'validate' subparser
    validate_parser = subparsers.add_parser(
        'validate', help='validate service.json')

    vpkargs = dict(metavar='service_json',
                   type=str,
                   help='a (new) directory to initial a ymir project in')
    if working_dir_is_ymir():
        # in this case, the service_json
        # positional argument may be implied
        vpkargs.update(
            dict(nargs='?', default='service.json'))
    validate_parser.add_argument('service_json', **vpkargs)

    validate_parser.set_defaults(subcommand='validate')
    load_parser = subparsers.add_parser(
        'load', help='load service.json')
    load_parser.add_argument(
        'service_json', metavar='service_json',
        type=str,
        help='a (new) directory to initial a ymir project in')
    load_parser.set_defaults(subcommand='load')
    init_parser = subparsers.add_parser('init', help='init ymir project')
    init_parser.add_argument('init_dir', metavar='directory', type=str,
                   help='a (new) directory to initial a ymir project in')
    init_parser.add_argument('-f','--force', action='store_true',
                   help='force overwrite even if directory exists')
    init_parser.set_defaults(subcommand='init')
    freeze_parser = subparsers.add_parser('freeze', help='freeze ymir service (must be running)')
    freeze_parser.set_defaults(subcommand='freeze')
    return parser

def entry(settings=None):
    """ Main entry point """
    parser = get_parser()
    args = parser.parse_args(sys.argv[1:])
    if args.subcommand == 'version':
        print 'ymir=={0}'.format(__version__)
    elif args.subcommand == 'help':
        parser.print_help()
    elif args.subcommand == 'init':
        ymir_init(args)
    elif args.subcommand == 'validate':
        ymir_validate(args, simple=False)
    elif args.subcommand == 'load':
        ymir_load(args)
    elif args.subcommand == 'keypair':
        ymir_keypair(args)
    elif args.subcommand == 'freeze':
        ymir_freeze(args)
    elif args.subcommand == 'shell':
        ymir_shell(args)
    # reflect fabric here

if __name__=='__main__':
    entry()
