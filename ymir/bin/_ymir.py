""" ymir.bin._ymir
"""
import os, sys
import shutil
import fabric
from argparse import ArgumentParser
from fabric.contrib.console import confirm
from fabric.colors import red
from ymir.schema import schema

from ymir.version import __version__
YMIR_SRC = os.path.dirname(os.path.dirname(__file__))

def get_parser():
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
    init_parser = subparsers.add_parser('init', help='init ymir project')
    init_parser.add_argument('init_dir', metavar='directory', type=str,
                   help='a (new) directory to initial a ymir project in')
    init_parser.add_argument('-f','--force', action='store_true',
                   help='a (new) directory to initial a ymir project in')
    init_parser.set_defaults(subcommand='init')
    return parser

def ymir_init(parser, args):
    if os.path.exists(args.init_dir) and not args.force:
        err = ('this command is used to initialize a '
               'ymir project, the directory should'
               ' not already exist.')
        raise SystemExit(err)
    if os.path.exists(args.init_dir) and args.force:
        #if confirm(('you passed --force.  are you sure'
        #            ' you want to delete "{0}"?').format(
        #               args.init_dir)):
            shutil.rmtree(args.init_dir)
    skeleton_dir = os.path.join(YMIR_SRC, 'skeleton')
    if not os.path.exists(skeleton_dir):
        err = ('cannot find ymir skeleton project.  '
               'your ymir installation might be broken :(')
        raise SystemExit(err)
    print red('creating directory: ') + args.init_dir
    print red('copying ymir skeleton: '),skeleton_dir
    shutil.copytree(skeleton_dir, args.init_dir)
import voluptuous, demjson
def entry(settings=None):
    """ Main entry point """
    parser = get_parser()
    args = parser.parse_args(sys.argv[1:])
    print args
    if args.subcommand=='version':
        print 'ymir=={0}'.format(__version__)
    elif args.subcommand=='help':
        parser.print_help()
    elif args.subcommand=='init':
        ymir_init(parser, args)
    elif args.subcommand=='validate':
        with open(args.service_json) as fhandle:
            try:
                schema(demjson.decode(fhandle.read()))
            except voluptuous.Invalid,e:
                raise SystemExit("error validating {0}\n\t{1}".format(
                    os.path.abspath(args.service_json), e))
if __name__=='__main__':
    entry()
