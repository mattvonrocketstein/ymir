""" ymir.bin._ymir
"""
import os, sys
import shutil
import fabric
from argparse import ArgumentParser
from ymir.version import __version__

from ymir.commands import ymir_init, ymir_load, ymir_validate

def get_parser():
    """ creates the parser for the ymir command line utility """
    parser = ArgumentParser(prog=os.path.split(sys.argv[0])[-1])
    subparsers = parser.add_subparsers(help='commands')
    help_parser = subparsers.add_parser('help', help='show ymir help')
    help_parser.set_defaults(subcommand='help')
    version_parser = subparsers.add_parser('version', help='show ymir version')
    version_parser.set_defaults(subcommand='version')
    validate_parser = subparsers.add_parser(
        'validate', help='validate service.json')
    validate_parser.add_argument(
        'service_json', metavar='service_json',
        type=str,
        help='a (new) directory to initial a ymir project in')
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
                   help='a (new) directory to initial a ymir project in')
    init_parser.set_defaults(subcommand='init')
    return parser


def entry(settings=None):
    """ Main entry point """
    parser = get_parser()
    args = parser.parse_args(sys.argv[1:])
    print args
    if args.subcommand == 'version':
        print 'ymir=={0}'.format(__version__)
    elif args.subcommand == 'help':
        parser.print_help()
    elif args.subcommand == 'init':
        ymir_init(args)
    elif args.subcommand == 'validate':
        ymir_validate(args)
    elif args.subcommand == 'load':
        ymir_load(args)

if __name__=='__main__':
    entry()
