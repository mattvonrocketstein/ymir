""" ymir.commands
"""

import os
import shutil

import addict
import voluptuous, demjson

from fabric.colors import red, green
from fabric.contrib.console import confirm

from ymir import util
from ymir import checks
from ymir.util import copytree
from ymir import schema as yschema
from ymir.service import AbstractService
from ymir.beanstalk import ElasticBeanstalkService

OK = green('  ok')
YMIR_SRC = os.path.dirname(__file__)

def _load_json(fname):
    """ loads json and allows for
        templating / value reflection
    """
    with open(fname) as fhandle:
        tmp = demjson.decode(fhandle.read())
        for k,v in tmp.items():
            if isinstance(v, basestring) and '{' in v:
                tmp[k] = v.format(**tmp)
        return addict.Dict(tmp)

def _choose_schema(json):
    json = json.copy()
    if json.instance_type in [u'elastic_beanstalk', u'elasticbeanstalk']:
        schema = yschema.eb_schema
    else:
        schema = yschema.default_schema
    return schema

def _validate_file(fname):
    """ simple schema validation, this
        returns error message or None """
    tmp = _load_json(fname)
    schema = _choose_schema(tmp)
    is_eb = schema.schema_name == 'eb_schema'
    print 'Chose schema:\n ',schema.schema_name
    try:
        schema(tmp)
    except voluptuous.Invalid, e:
        msg = "error validating {0}\n\t{1}"
        msg = msg.format(os.path.abspath(fname), e)
        return msg
    SERVICE_ROOT = os.path.dirname(fname)
    SERVICE_ROOT = os.path.abspath(SERVICE_ROOT)
    tmp.update(dict(SERVICE_ROOT=SERVICE_ROOT))
    if is_eb:
        return
    files = tmp['setup_list'] + tmp['provision_list']
    for _file in files:
        if not os.path.exists(os.path.join(SERVICE_ROOT, _file)):
            err= ('Files mentioned in service json '
                  'must exist relative to {0}, but {1}'
                  ' was not found').format(
                SERVICE_ROOT, _file)
            return err

def _ymir_load(args, interactive=True):
    """ load service obj from service json """
    SERVICE_ROOT = os.path.dirname(args.service_json)
    SERVICE_ROOT = os.path.abspath(SERVICE_ROOT)
    service_json = _load_json(args.service_json)
    if interactive:
        lint = demjson.jsonlint()
        print red("Service root: "), '\n  ', SERVICE_ROOT
        print red("Service JSON: ")
        rc = lint.main(['-S', '--format', args.service_json])
    dct = dict([
        [x.upper(), y] for x, y in service_json.items()])
    dct.update(SERVICE_ROOT=SERVICE_ROOT)
    classname = str(service_json.name).lower()
    if _choose_schema(service_json) == yschema.eb_schema:
        from ymir.beanstalk import ElasticBeanstalkService
        BaseService = ElasticBeanstalkService
    else:
        BaseService = AbstractService
    print 'Chose service-class:\n ',BaseService.__name__
    ServiceFromJSON = type(
        classname, (BaseService,), dct)

    if interactive:
        print red("Service definition loaded from JSON")
    return ServiceFromJSON()

def ymir_load(args, interactive=True):
    """ """
    ymir_validate(args, interactive=False)
    return _ymir_load(args, interactive=interactive)

def ymir_init(args):
    """ responsible for executing the 'ymir init' command. """
    init_dir = os.path.abspath(args.init_dir)
    if os.path.exists(init_dir) and not args.force:
        err = ('this command is used to initialize a '
               'ymir project, the directory should'
               ' not already exist.')
        raise SystemExit(err)
    using_dot = init_dir == os.getcwd()
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
    copytree(skeleton_dir, init_dir)


def ymir_validate(args, simple=True, interactive=True):
    """ """
    err = _validate_file(args.service_json)
    if err:
        raise SystemExit(err)
    elif interactive:
        print 'Validating the file schema..\n  ok'
    if simple:
        return

    # simple validation has succeded, begin second phase.
    # the schema can be loaded, so build a service object.
    # the service object can then begin to validate itself
    service_json = _load_json(args.service_json)
    service = _ymir_load(args, interactive=False)
    if not isinstance(service, ElasticBeanstalkService):
        print 'Validating AWS keypairs..'
        errors = service._validate_keypairs()
        if errors:
            for err in errors:
                print '  ERROR: '+str(err)
        else:
            print OK

        print 'Validating AWS security groups..'
        err = service._validate_sgs()
        print '  ERROR: '+str(err) if err else OK

    print 'Validating `health_checks` content..'
    err = None
    for check_name in service_json['health_checks']:
        check_type, url = service_json['health_checks'][check_name]
        try:
            getattr(checks, check_type)
        except AttributeError:
            err = '  ERROR: {0} does not exist in ymir.checks'
            err = err.format(check_type)
            print err
    if err is None:
        print '  ok'
