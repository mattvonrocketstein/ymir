# -*- coding: utf-8 -*-
""" ymir.validation
"""
import os
import logging
import voluptuous
from fabric.colors import red
from ymir import data as ydata
from ymir import schema as yschema
from ymir.base import report as base_report

logger = logging.getLogger(__name__)

report = lambda x: base_report('ymir.validation', x)


def validate(service_json, simple=True,):
    """ """
    def print_errs(msg, _errs, die=False, report=report):
        assert isinstance(_errs, list), str([type(_errs), _errs])
        report(msg)
        if not _errs:
            report(ydata.OK)
        else:
            for e in _errs:
                report(red('  ERROR: ') + str(e))
            if die:
                raise SystemExit(str(_errs))

    from ymir.beanstalk import ElasticBeanstalkService

    print_errs('Validating overall file schema',
               _validate_file(service_json), die=True)

    if simple:
        return True

    # simple validation has succeded, begin second phase.
    # the schema can be loaded, so build a service object.
    # the service object can then begin to validate itself
    print 'Instantiating service to scrutinize it..'
    service = yapi.load_service_from_json(service_json)

    print_errs(
        'Validating content in `health_checks` field..',
        service._validate_health_checks(),
        report=service.report,)
    if not isinstance(service, ElasticBeanstalkService):
        print_errs('Validating AWS keypair at field `key_name`..',
                   service._validate_keypairs(), report=service.report,)
        print_errs('Validating puppet-librarian\'s metadata.json',
                   service._validate_puppet_librarian(), report=service.report)
        print_errs('Validating simple AWS security groups in field `security_groups`..',
                   service._validate_named_sgs(), report=service.report,)
        print_errs('Validating puppet code..',
                   service._validate_puppet(), report=service.report,)
        print_errs('Validating puppet templates..',
                   service._validate_puppet_templates(), report=service.report,)


def _validate_file(fname):
    """ simple schema validation, this returns a
        list of [error_message] or None
    """

    assert isinstance(fname, basestring)
    tmp = yapi.load_json(fname)
    schema = yschema._choose_schema(tmp)
    is_eb = schema.schema_name == 'eb_schema'
    # print 'Chose schema:\n ',schema.schema_name
    try:
        schema(tmp)
    except voluptuous.Invalid, e:
        msg = "error validating {0}\n\t{1}"
        msg = msg.format(os.path.abspath(fname), e)
        return [msg]
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
