# -*- coding: utf-8 -*-
""" ymir.validation
"""
import os
import logging
import voluptuous
from fabric.colors import red
from ymir import util
from ymir import data as ydata
from ymir import schema as yschema
from ymir.base import report as base_report
from ymir.beanstalk import ElasticBeanstalkService

logger = logging.getLogger(__name__)

_report = lambda x: base_report('ymir.validation', x)


def print_errs(msg, _errs, quiet=False, die=False, report=_report):
    """ helper for main validation function """
    assert isinstance(_errs, list), str([type(_errs), _errs])
    if msg:
        report(msg)
    if not _errs:
        quiet or report(ydata.OK)
        return True
    else:
        for e in _errs:
            report('ERROR\n')
            report(red('  error {0}: '.format(_errs.index(e))) + str(e))
        if die:
            raise SystemExit(str(_errs))


def validate(service_json, schema=None, simple=True, quiet=False):
    """ validate service json is 2 step.  when simple==True,
        validation exits early after running against the main
        JSON schema.  otherwise, the service will be instantiated
        and sanity-checked against real-world requirements such as
        actually existing security-groups, keyfiles, etc.
    """
    report = util.NOOP if quiet else _report
    print_errs('',
               _validate_file(service_json, schema, report=report),
               quiet=True, die=True)

    if simple:
        return True

    # simple validation has succeded, begin second phase.
    # the schema can be loaded, so build a service object.
    # the service object can then begin to validate itself
    print 'Instantiating service to scrutinize it..'
    service = yapi.load_service_from_json(service_json, quiet=quiet)
    report = util.NOOP if quiet else service.report

    print_errs(
        'checking content in `health_checks` field..',
        service._validate_health_checks(),
        report=report,)
    if not isinstance(service, ElasticBeanstalkService):
        print_errs('checking AWS keypair at field `key_name`..',
                   service._validate_keypairs(), report=report,)
        print_errs('checking puppet-librarian\'s metadata.json',
                   service._validate_puppet_librarian(), report=report)
        print_errs('checking simple AWS security groups in field `security_groups`..',
                   service._validate_named_sgs(), report=report,)
        print_errs('checking puppet code..',
                   service._validate_puppet(), report=report,)
        print_errs('checking puppet templates..',
                   service._validate_puppet_templates(), report=report,)


def _validate_file(fname, schema=None, report=util.NOOP, quiet=False):
    """ simple schema validation, this returns a
        list of [error_message] or None
    """
    report('validating file using {0}'.format(schema))
    assert isinstance(fname, basestring)
    tmp = yapi.load_json(fname)
    if schema is None:
        schema = yschema.choose_schema(tmp, quiet=quiet)
    is_eb = schema.schema_name == 'beanstalk_schema'
    try:
        schema(tmp)
    except voluptuous.Invalid, e:
        msg = "error validating {0}:\n\n{1}"
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
