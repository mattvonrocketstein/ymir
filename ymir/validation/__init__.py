# -*- coding: utf-8 -*-
""" ymir.validation
"""
import os
import logging
import voluptuous
from fabric.colors import red
from ymir import data as ydata
from ymir import schema as yschema
logger = logging.getLogger(__name__)


def validate(service_json, simple=True,
             # interactive=True
             ):
    """ """
    def print_errs(_errs, die=False):
        assert isinstance(_errs, list), str(_errs)
        if not _errs:
            return
        for e in _errs:
            print red('  ERROR: ') + str(e)
        if die:
            raise SystemExit(str(_errs))

    errs = _validate_file(service_json)
    print_errs(errs, die=True)

    if simple:
        return True

    # simple validation has succeded, begin second phase.
    # the schema can be loaded, so build a service object.
    # the service object can then begin to validate itself

    print 'Instantiating service to scrutinize it..'
    service = yapi.load_service_from_json(
        service_json, interactive=False, simple=True)
    print ydata.OK
    errs = service._validate_health_checks()
    print_errs(
        'Validating content in `health_checks` field..',
        errs)
    from ymir.beanstalk import ElasticBeanstalkService
    if not isinstance(service, ElasticBeanstalkService):
        errors = service._validate_keypairs()
        print_errs('Validating AWS keypair at field `key_name`..',
                   errors)
        errs = service._validate_puppet_librarian()
        print_errs('Validating puppet-librarian\'s metadata.json', errs)
        errs = service._validate_named_sgs()
        print_errs(
            'Validating simple AWS security groups in field `security_groups`..',
            errs)
        errs = service._validate_puppet()
        print_errs(
            'Validating puppet code..',
            errs)
        errs = service._validate_puppet_templates()
        print_errs('Validating puppet templates..', errs)


def _validate_file(fname):
    """ simple schema validation, this
        returns error message or None """
    tmp = yapi.load_json(fname)
    schema = yschema._choose_schema(tmp)
    is_eb = schema.schema_name == 'eb_schema'
    # print 'Chose schema:\n ',schema.schema_name
    try:
        schema(tmp)
    except voluptuous.Invalid, e:
        msg = "error validating {0}\n\t{1}"
        msg = msg.format(os.path.abspath(fname), e)
        return msg
    SERVICE_ROOT = os.path.dirname(fname)
    SERVICE_ROOT = os.path.abspath(SERVICE_ROOT)
    if is_eb:
        return []
    files = tmp['setup_list'] + tmp['provision_list']
    for _file in files:
        if '://' not in _file and not os.path.exists(os.path.join(SERVICE_ROOT, _file)):
            err = ('Files mentioned in service json '
                   'must exist relative to {0}, but {1}'
                   ' was not found').format(
                SERVICE_ROOT, _file)
            return [err]
    return []

from ymir import api as yapi
