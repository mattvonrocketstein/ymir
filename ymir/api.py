# -*- coding: utf-8 -*-
"""
"""
import os
import demjson

from ymir.base import report
from ymir import util


def _reflect(service_json=None, service_obj=None, service_json_file=None, simple=True):
    """ given a dictionary of service-json, reflect that data onto the service object"""
    assert (service_json or service_obj) and not all(
        [service_json, service_obj])

    if service_obj:
        tdata = service_obj._template_data(simple=simple)
        for k, v in tdata['service_defaults'].items():
            tmp = service_obj.SERVICE_DEFAULTS[k]
            if isinstance(tmp, basestring):
                service_obj.SERVICE_DEFAULTS[k] = tmp.format(**tdata)
        return service_obj
    if service_json:
        for k, v in service_json.items():
            if isinstance(v, basestring) and '{' in v:
                service_json[k] = v.format(**service_json)
        return service_json


def load_json(fname):
    """ loads json and allows for
        templating / value reflection
    """
    with open(fname) as fhandle:
        tmp = demjson.decode(fhandle.read())
    return _reflect(service_json_file=fname, service_json=tmp)


def load_service_from_json(filename=None):
    """ entry point """
    from ymir import validation
    report('profile', os.environ.get('AWS_PROFILE', 'default'))
    service_json_file = filename or util.get_or_guess_service_json_file()
    # print 'found service.json at {0}.  loading
    # service..'.format(service_json_file)
    validation.validate(service_json_file, simple=True)
    return _load_service_from_json_helper(
        service_json_file=service_json_file,
        json=load_json(service_json_file))

# alias is frequently imported in fabfiles to avoid cluttering fabric namespace
_load_service_from_json = load_service_from_json


def _load_service_from_json_helper(service_json_file=None, json={}, simple=False):
    """ load service obj from service json """
    from ymir import schema as yschema
    from ymir.beanstalk import ElasticBeanstalkService
    from ymir.service import AbstractService
    # print red("Service root: "), '\n  ', json['SERVICE_ROOT']
    # print red("Service JSON: ")
    service_json = json
    dct = dict([
        [x.upper(), y] for x, y in service_json.items()])
    classname = str(json["name"]).lower()
    chosen_schema = yschema._choose_schema(json)
    if chosen_schema == yschema.eb_schema:
        BaseService = ElasticBeanstalkService
    else:
        BaseService = AbstractService
    # print 'Chose service-class:\n ',BaseService.__name__
    ServiceFromJSON = type(classname, (BaseService,), dct)
    obj = ServiceFromJSON(service_root=os.path.dirname(service_json_file))
    obj._schema = chosen_schema
    obj = _reflect(service_obj=obj, simple=simple)
    # if interactive:
    #    print red("Service definition loaded from JSON")
    return obj
