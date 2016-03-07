# -*- coding: utf-8 -*-
"""
"""
import os
import demjson

from ymir import util
from ymir.base import report as base_report
from ymir import schema as yschema
from voluptuous import Optional, Undefined

NOOP = util.NOOP


def str_reflect(obj, ctx, simple=True):
    try:
        return obj.format(**ctx)
    except KeyError as err:
        lazy_keys = ['host']
        if err.message in lazy_keys and simple:
            return obj
        else:
            raise Exception(str([err, lazy_keys, simple, ]))


def list_reflect(lst, ctx, simple=True):
    return [rreflect(obj, ctx, simple=simple) for obj in lst]


def dict_reflect(dct, ctx, simple=True):
    return dict([[rreflect(k, ctx, simple=simple),
                  rreflect(v, ctx, simple=simple)]
                 for k, v in dct.items()])


def rreflect(obj, ctx, simple=True):
    """ """
    if isinstance(obj, basestring):
        return str_reflect(obj, ctx, simple=simple)
    elif isinstance(obj, list):
        return list_reflect(obj, ctx, simple=simple)
    elif isinstance(obj, dict):
        return dict_reflect(obj, ctx, simple=simple)
    else:
        return obj


def _reflect(service_json=None, service_json_file=None, simple=True):
    """ given a dictionary of service-json, reflects that data onto the service object"""
    assert service_json or service_json_file and not all(
        [service_json, service_json_file])
    working = service_json.copy()

    service_defaults = service_json.get('service_defaults', {})
    working.update(**service_defaults)
    # reflect toplevel service_json into itself
    for k, v in working.items():
        working[k] = rreflect(v, working)
    out = dict([[k, v] for k, v in working.items() if k in service_json])
    return out


def load_json(fname):
    """ loads json and allows for
        templating / value reflection
    """
    if not os.path.exists(fname):
        err = ("\nERROR: Service description file '{0}' not found.\n\n"
               "Set the YMIR_SERVICE_JSON environment "
               "variable and retry this operation.")
        raise SystemExit(err.format(util.unexpand(fname)))
    with open(fname) as fhandle:
        tmp = demjson.decode(fhandle.read())
    return tmp


def load_service_from_json(filename=None, quiet=False):
    """ return a service object from ymir-style service.json file.
        when filename is not given it will be guessed based on cwd.
    """
    from ymir.version import __version__
    report = NOOP if quiet else base_report
    report('aws profile', os.environ.get('AWS_PROFILE', 'default'))
    report('ymir', 'version {0}'.format(__version__))
    service_json_file = filename or util.get_or_guess_service_json_file()
    report('ymir', 'service.json is {0}'.format(
        util.unexpand(service_json_file)))
    obj = _load_service_from_json_helper(
        service_json_file=service_json_file,
        service_json=load_json(service_json_file),
        quiet=quiet)
    return obj

# NB: alias is frequently imported in fabfiles to avoid cluttering fabric
# namespace
_load_service_from_json = load_service_from_json


def set_schema_defaults(service_json, chosen_schema):
    """ """
    service_json = service_json.copy()
    defaults = [[str(k), k.default] for k in chosen_schema.schema.keys()
                if type(k) == Optional]
    defaults = filter(lambda x: not isinstance(x[1], Undefined), defaults)
    defaults = dict(defaults)
    for k, default in defaults.items():
        if k not in service_json:
            default = default() if callable(default) else default
            # report ("ymir.api",
            #       'using implied default: {0}'.format([k, '==', default]))
            service_json[k] = default
    return service_json


def _load_service_from_json_helper(service_json_file=None,
                                   service_json={}, quiet=False, simple=False):
    """ load service obj from service json """
    from ymir import validation
    from ymir.beanstalk import ElasticBeanstalkService
    from ymir.service import AbstractService
    chosen_schema = yschema.choose_schema(service_json, quiet=True)
    validation.validate(service_json_file, chosen_schema, simple=True)
    report = NOOP if quiet else base_report
    # report("ymir","ymir service.json version:")
    report('ymir.api', 'loading service object from description')
    # dynamically create the service instance's class
    dct = dict([
        [x.upper(), y] for x, y in service_json.items()])
    classname = str(service_json["name"]).lower()
    if chosen_schema == yschema.eb_schema:
        BaseService = ElasticBeanstalkService
    else:
        BaseService = AbstractService
    report('ymir.api', 'chose service class: {0}'.format(
        BaseService.__name__))
    ServiceFromJSON = type(classname, (BaseService,), dct)
    obj = ServiceFromJSON(service_root=os.path.dirname(service_json_file))
    obj._schema = chosen_schema
    service_json = _reflect(service_json=service_json, simple=True)
    service_json = set_schema_defaults(service_json, chosen_schema)
    ServiceFromJSON.template_data = lambda himself, **kargs: service_json

    service_json.update(service_json['service_defaults'])
    service_json.update(host=obj._host())
    return obj
