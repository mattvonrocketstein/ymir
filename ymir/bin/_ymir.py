# -*- coding: utf-8 -*-
""" ymir.bin._ymir
"""

import os
import sys
import logging
from argparse import ArgumentParser

from ymir.base import report
from ymir.version import __version__
from ymir.commands import (
    ymir_init, ymir_sg, ymir_list,
    ymir_eip, ymir_keypair, ymir_shell, ymir_validate)
logger = logging.getLogger(__name__)

LOG_LEVELS = [logging.CRITICAL,  # 50
              logging.ERROR,  # 40
              logging.WARNING,  # 30
              logging.INFO,  # 20
              logging.DEBUG,  # 10
              ]


def ymir_freeze(args):
    print 'not implemented yet'


def get_parser():
    """ creates the parser for the ymir command line utility """
    parser = ArgumentParser(prog=os.path.split(sys.argv[0])[-1])
    parser.add_argument(
        '-v', '--verbose', default=1,
        action="count", dest="verbose",
        help="turn up logging verbosity")
    parser.add_argument('--debug',
                        default=False,
                        action='store_true',
                        dest='debug',
                        help='shortcut for -vvv')
    subparsers = parser.add_subparsers(help='commands')
    help_parser = subparsers.add_parser('help', help='show ymir help')
    help_parser.set_defaults(subcommand='help')
    version_parser = subparsers.add_parser('version', help='show ymir version')
    version_parser.set_defaults(subcommand='version')
    shell_parser = subparsers.add_parser(
        'shell', help='open interactive shell')
    shell_parser.set_defaults(subcommand='shell')

    eip_parser = subparsers.add_parser('eip', help='assign new elastic ip')
    eip_parser.set_defaults(subcommand='eip')
    eip_parser.add_argument('-f', '--force', action='store_true',
                            help='force noninteractive mode')

    list_parser = subparsers.add_parser('list', help='list AWS resources')
    list_parser.set_defaults(subcommand='list')
    list_parser.add_argument('-k', '--keypairs', action='store_true',
                             help='list keypairs')
    list_parser.add_argument('-i', '--instances', action='store_true',
                             help='list instances')

    sgkargs = dict(
        metavar='security_group_json', type=str,
        nargs='?', default='security_groups.json')
    sg_parser = subparsers.add_parser(
        'sg', help='shortcut for security_group command')
    sg_parser.set_defaults(subcommand='sg')
    sg_parser.add_argument('sg_json', **sgkargs)
    sg_parser.add_argument(
        '--list', '-l', action='store_true', help='list security groups')
    security_group_parser = subparsers.add_parser(
        'security_group', help='updates AWS security group from JSON')
    security_group_parser.set_defaults(subcommand='security_group')
    security_group_parser.add_argument('sg_json', **sgkargs)
    sg_parser.add_argument('-f', '--force', action='store_true',
                           help='force rules even if they dont support ssh')
    security_group_parser.add_argument('-f', '--force', action='store_true',
                                       help='force rules even if they dont support ssh')

    keypair_parser = subparsers.add_parser('keypair', help='show ymir keypair')
    keypair_parser.set_defaults(subcommand='keypair')
    keypair_parser.add_argument(
        'keypair_name', metavar='keypair_name',
        type=str,
        help='a (new) keyname created on aws.  pem saved to ~/.ssh')
    keypair_parser.add_argument('-f', '--force', action='store_true',
                                help='a (new) directory to initial a ymir project in')

    # build 'validate' subparser
    validate_parser = subparsers.add_parser(
        'validate', help='validate service.json')

    vpkargs = dict(metavar='service_json',
                   type=str,
                   help='service json to validate against')

    vpkargs.update(
        dict(nargs='?', default=''))
    validate_parser.add_argument('service_json', **vpkargs)

    validate_parser.set_defaults(subcommand='validate')
    init_parser = subparsers.add_parser('init', help='init ymir project')
    init_parser.add_argument('init_dir', metavar='directory', type=str,
                             help='a (new) directory to initial a ymir project in')
    init_parser.add_argument('-f', '--force', action='store_true',
                             help='force overwrite even if directory exists')
    init_parser.set_defaults(subcommand='init')
    freeze_parser = subparsers.add_parser(
        'freeze', help='freeze ymir service (must be running)')
    freeze_parser.set_defaults(subcommand='freeze')
    return parser


def entry(settings=None):
    """ Main entry point """
    report('ymir', 'version {0}'.format(__version__))
    parser = get_parser()
    args = parser.parse_args(sys.argv[1:])
    service_json_not_found = (
        not getattr(args, 'service_json', None) or
        not os.path.exists(args.service_json))
    if 'service_json' in args and service_json_not_found:
        args.service_json = os.environ.get('YMIR_SERVICE_JSON')
        # print 'using service_json:', args.service_json

    if args.debug:
        args.verbose = 4
    try:
        level = LOG_LEVELS[args.verbose]
    except IndexError:
        raise SystemExit("-vvv is the maximum!")

    logging.basicConfig(
        level=level,
        format="%(levelname)s [%(filename)s:%(lineno)s] %(message)s",
    )
    subcommand_map = dict(
        help=lambda args: parser.print_help(),
        eip=ymir_eip,
        security_group=ymir_sg,
        init=ymir_init,
        validate=ymir_validate,
        keypair=ymir_keypair,
        freeze=ymir_freeze,
        shell=ymir_shell,
        list=ymir_list,
    )
    logger.debug('log level is: {0}'.format(level))
    if args.subcommand == 'sg':
        args.subcommand = 'security_group'
    if args.subcommand == 'version':
        print '{0}'.format(__version__)
        return
    subcommand_map[args.subcommand](args)

if __name__ == '__main__':
    entry()
