""" ymir.commands
"""

import voluptuous, demjson

import os
import shutil

from fabric.colors import red
from fabric.contrib.console import confirm

from ymir.schema import schema
from ymir.service import AbstractService

YMIR_SRC = os.path.dirname(__file__)

def ymir_init(args):
    """ responsible for executing the 'ymir init' command """
    init_dir = os.path.abspath(args.init_dir)
    if os.path.exists(init_dir) and not args.force:
        err = ('this command is used to initialize a '
               'ymir project, the directory should'
               ' not already exist.')
        raise SystemExit(err)
    using_dot = init_dir == os.getcwd()
    if using_dot:
        os.chdir(os.path.dirname(init_dir))
    if os.path.exists(init_dir) and args.force:
        #if confirm(('you passed --force.  are you sure'
        #            ' you want to delete "{0}"?').format(
        #               init_dir)):
            shutil.rmtree(init_dir)
    skeleton_dir = os.path.join(YMIR_SRC, 'skeleton')
    if not os.path.exists(skeleton_dir):
        err = ('cannot find ymir skeleton project.  '
               'your ymir installation might be broken :(')
        raise SystemExit(err)
    print red('creating directory: ') + init_dir
    print red('copying ymir skeleton: '), skeleton_dir
    shutil.copytree(skeleton_dir, init_dir)
    if using_dot:
        os.path.chdir(init_dir)
def _load_json(fname):
    with open(fname) as fhandle:
        return demjson.decode(fhandle.read())

def _validate_file(fname):
    """ returns only error """
    tmp = _load_json(fname)
    try:
        schema(tmp)
    except voluptuous.Invalid, e:
        msg = "error validating {0}\n\t{1}"
        msg = msg.format(os.path.abspath(fname), e)
        return msg
    SERVICE_ROOT = os.path.dirname(fname)
    SERVICE_ROOT = os.path.abspath(SERVICE_ROOT)
    tmp.update(SERVICE_ROOT=SERVICE_ROOT)
    files = [tmp['puppet_setup']] + tmp['puppet']
    for _file in files:
        if not os.path.exists(os.path.join(SERVICE_ROOT, _file)):
            err= ('Files mentioned in service json '
                  'must exist relative to {0}, but {1}'
                  ' was not found').format(
                SERVICE_ROOT, _file)
            return err



def ymir_load(args, interactive=True):
    """ """
    ymir_validate(args, interactive=interactive)
    SERVICE_ROOT = os.path.dirname(args.service_json)
    SERVICE_ROOT = os.path.abspath(SERVICE_ROOT)
    service_json = _load_json(args.service_json)
    if interactive:
        lint = demjson.jsonlint()
        print red("Service root: "), '\n  ', SERVICE_ROOT
        print red("Service JSON: ")
        rc = lint.main(['-S','--format', args.service_json])
    dct = dict([
        [x.upper(), y] for x, y in service_json.items()])
    dct.update(SERVICE_ROOT=SERVICE_ROOT)
    ServiceFromJSON = type(
        'ServiceFromJSON',
        (AbstractService,), dct)
    if interactive:
        print red("Service definition loaded from JSON")
    return ServiceFromJSON()

def ymir_validate(args, interactive=True):
    """ """
    err = _validate_file(args.service_json)
    if err:
        raise SystemExit(err)
    elif interactive:
        print 'ok'
