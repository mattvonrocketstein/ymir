""" ymir.commands
"""

import os

import addict
import voluptuous, demjson

from fabric.colors import red, green

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
        return _reflect(service_json=tmp)

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
    #print 'Chose schema:\n ',schema.schema_name
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
        return []
    files = tmp['setup_list'] + tmp['provision_list']
    for _file in files:
        if not os.path.exists(os.path.join(SERVICE_ROOT, _file)):
            err= ('Files mentioned in service json '
                  'must exist relative to {0}, but {1}'
                  ' was not found').format(
                SERVICE_ROOT, _file)
            return [err]
    return []

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
    chosen_schema = _choose_schema(service_json)
    if chosen_schema == yschema.eb_schema:
        from ymir.beanstalk import ElasticBeanstalkService
        BaseService = ElasticBeanstalkService
    else:
        BaseService = AbstractService
    #print 'Chose service-class:\n ',BaseService.__name__
    ServiceFromJSON = type(classname, (BaseService,), dct)
    obj = ServiceFromJSON()
    obj._schema = chosen_schema
    obj = _reflect(service_obj=obj)
    if interactive:
        print red("Service definition loaded from JSON")
    return obj

def ymir_shell(args):
    """ """
    wd_json = os.path.join(os.getcwd(),'service.json')
    if os.path.exists(wd_json):
        print 'found service.json import working directory, loading service..'
        fake_args = addict.Dict(service_json=wd_json)
        user_ns = dict(
            service=ymir_load(fake_args))
    from smashlib import embed; embed(user_ns=user_ns)

def ymir_load(args, interactive=True):
    """ """
    ymir_validate(args, interactive=False)
    return _ymir_load(args, interactive=interactive)

def _reflect(service_json=None, service_obj=None, simple=True):
    """ """
    assert service_json or service_obj
    if service_obj:
        for k, v in service_obj._template_data()['service_defaults'].items():
            tmp = service_obj.SERVICE_DEFAULTS[k]
            if isinstance(tmp, basestring):
                service_obj.SERVICE_DEFAULTS[k] = tmp.format(
                    service_obj._template_data(simple=simple))
        return service_obj
    if service_json:
        for k,v in service_json.items():
            if isinstance(v, basestring) and '{' in v:
                service_json[k] = v.format(**service_json)
        return addict.Dict(service_json)

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
    def print_errs(msg, _errs, die=False):
        assert isinstance(_errs, list), str(type(_errs))
        if interactive:
            print msg
        if not _errs:
            print OK
            return
        for e in _errs:
            print '  ERROR: '+str(e)
        if die:
            raise SystemExit(str(_errs))

    errs = _validate_file(args.service_json)
    print_errs(
        'Validating the overall file schema..',
        errs, die=True)

    if simple:
        return True

    # simple validation has succeded, begin second phase.
    # the schema can be loaded, so build a service object.
    # the service object can then begin to validate itself

    print 'Instantiating service to scrutinize it..'
    service = _ymir_load(args, interactive=False)
    print OK
    errs = service._validate_health_checks()
    print_errs(
        'Validating content in `health_checks` field..',
        errs)

    if not isinstance(service, ElasticBeanstalkService):
        errors = service._validate_keypairs()
        print_errs('Validating AWS keypair at field `key_name`..',
                   errors)

        errs = service._validate_sgs()
        print_errs(
            'Validating AWS security groups in field `security_groups`..',
            errs)
        errs = service._validate_puppet()
        print_errs(
            'Validating puppet code..',
            errs)

def ymir_freeze(args):
    msg = 'not implemented yet'
    print msg
    raise SystemExit(msg)
