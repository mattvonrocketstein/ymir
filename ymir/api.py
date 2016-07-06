# -*- coding: utf-8 -*-
""" ymir.api
"""
import os
import re

import demjson
from fabric.colors import yellow
from voluptuous import Optional, Undefined

from ymir import util
from ymir.base import report as base_report
from ymir import schema as yschema

import jinja2

jinja_env = jinja2.Environment(undefined=jinja2.StrictUndefined)


class ReflectionError(Exception):
    pass


def str_reflect(obj, ctx, simple=True):
    """ when `simple` is true, lazy JIT params like host/username/pem need
        not be resolved and certain errors are allowed
    """
    pattern = r"'([A-Za-z0-9_\./\\-]*)'"
    try:
        return jinja_env.from_string(obj).render(**ctx)
    except jinja2.UndefinedError as err:
        lazy_keys = ['host', 'username', 'pem']
        group = re.search(pattern, str(err)).group().replace("'", '')
        if group in lazy_keys and simple:
            return obj
        else:
            raise ReflectionError(
                str(dict(
                    original_err=err,
                    group=group,
                    lazy_keys=lazy_keys,
                    simple=simple,)))


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
    service_json_file = filename or util.get_or_guess_service_json_file()
    # report('ymir.api', 'service.json is {0}'.format(
    #    util.unexpand(service_json_file)))
    service_obj = _load_service_from_json_helper(
        service_json_file=service_json_file,
        service_json=load_json(service_json_file),
        quiet=quiet)
    # trigger the caching of this value now,
    # just to print the message as early as possible
    service_obj._debug_mode
    return service_obj

# this alias is frequently imported in
# fabfiles to avoid cluttering fabric namespace
_load_service_from_json = load_service_from_json


def set_schema_defaults(service_json, chosen_schema):
    """ set default values for Optional() entries which are not provided """
    service_json = service_json.copy()
    defaults = [[str(k), k.default] for k in chosen_schema.schema.keys()
                if type(k) == Optional]
    defaults = filter(lambda x: not isinstance(x[1], Undefined), defaults)
    defaults = dict(defaults)
    for k, default in defaults.items():
        if k not in service_json:
            default = default() if callable(default) else default
            service_json[k] = default
    return service_json


def _load_service_from_json_helper(service_json_file=None,
                                   service_json={}, quiet=False, simple=False):
    """ load service obj from service json """
    from ymir import validation
    chosen_schema = yschema.choose_schema(service_json)
    validation.validate(service_json_file, chosen_schema, simple=True)
    report = util.NOOP if quiet else base_report
    report('ymir.api', 'chose schema: {0}'.format(
        yellow(chosen_schema.schema_name)))
    # report("ymir", "ymir service.json version:")
    # report('ymir.api', 'loading service object from description')
    service_json = set_schema_defaults(service_json, chosen_schema)
    service_json = _reflect(service_json)
    classname = str(service_json["name"])
    BaseService = chosen_schema.get_service_class(service_json)
    report('ymir.api', 'chose service class: {0}'.format(
        yellow(BaseService.__name__)))
    ServiceFromJSON = type(classname, (BaseService,),
                           dict(service_json_file=service_json_file))
    obj = ServiceFromJSON(service_json_file=service_json_file)
    obj._schema = chosen_schema
    service_json = set_schema_defaults(service_json, chosen_schema)
    ServiceFromJSON._service_json = service_json
    return obj
