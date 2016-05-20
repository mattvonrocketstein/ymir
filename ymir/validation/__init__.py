# -*- coding: utf-8 -*-
""" ymir.validation
"""
import os
import logging

import voluptuous
from fabric import api
from fabric.colors import red, green
from peak.util.imports import lazyModule

from ymir import util
from ymir import schema as yschema
from ymir.base import report as base_report
from ymir import api as yapi
from ymir import checks
from ymir.util import puppet

beanstalk = lazyModule('ymir.beanstalk')
logger = logging.getLogger(__name__)
_report = lambda msg: base_report('ymir.validation', msg)


def validate_puppet(service):
    """ runs puppet parser validation on puppet files contained
        inside the given service.  NB: this checks all the puppet
        code, not just things things in the service.json `setup_list`
        and `provision_list` fields
    """
    errors, messages = [], []
    pdir = service._puppet_dir
    if not os.path.exists(pdir):
        msg = 'puppet directory does not exist @ {0}'
        msg = msg.format(pdir)
        errors.append(msg)
    else:
        parser = service.template_data().get('puppet_parser', '')
        validation_cmd = 'puppet parser {0} validate '.format(
            '--parser {0}'.format(parser) if parser else '')
        with api.quiet():
            result = api.local('find {0}|grep .pp$'.format(pdir), capture=True)
            for filename in result.split('\n'):
                if not filename:
                    continue
                (" .. validating {0}".format(filename))
                result = api.local('{1} {0}'.format(
                    filename, validation_cmd), capture=True)
                error = result.return_code != 0
                if error:
                    short_fname = filename.replace(os.getcwd(), '.')
                    error = "running `{1} {0}'".format(
                        short_fname, validation_cmd)
                    errors.append(error)
                else:
                    messages.append(".. ok: " + filename)
    return errors, messages


def validate_puppet_templates(service):
    """ validates that variables mentioned in puppet
        templates are defined in service.json
    """
    errors, messages = [], []
    default_facts = puppet.DEFAULT_FACTS
    # local_puppet_template_files = service._get_puppet_templates()
    service_vars = service._service_data.keys()
    service_vars += default_facts
    for f, template_vars in service._get_puppet_template_vars().items():
        for template_var in template_vars:
            if template_var not in service_vars:
                msg = ("template {0} defines variable `{1}` "
                       "which is not defined for service").format(
                    f, template_var)
                errors.append(msg)
    return errors, messages


def validate_keypairs(service):
    """ validates that keypairs mentioned in service.json
        are present on the filesystem and on AWS with the
        current account
    """
    errors, messages = [], []
    service_data = service._service_data
    pem_file = os.path.expanduser(service_data['pem'])
    if not os.path.exists(pem_file):
        errors.append('  ERROR: pem file is not present: ' + pem_file)
    keys = util.get_keypair_names()
    key_name = service._service_data['key_name']
    if key_name not in keys:
        errors.append(
            '  ERROR: aws keypair {0} not found in {1}'.format(key_name, keys))
    return errors, messages


def validate_security_groups(service):
    """ validates that named security groups mentioned
        in service.json are defined according to AWS
        with the current account
    """
    """ validation for security groups.
    NB: this requires AWS credentials
    """
    groups = service._service_data['security_groups']
    errors, messages = [], []
    # filter for only named groups, in case the security_groups field
    # eventually supports more complete data (like security_groups.json)
    configured_sgs = [x for x in groups if isinstance(x, basestring)]
    actual_sgs = [x.name for x in service.conn.get_all_security_groups()]
    for sg in configured_sgs:
        if sg not in actual_sgs:
            err = "name `{0}` mentioned in security_groups is missing from AWS"
            errors.append(err.format(sg))
    return errors, messages


def validate_health_checks(service):
    """
    """
    # here we fake the host value just for validation because we
    # don't know whether this service has been bootstrapped or not
    service_json = service.template_data(simple=True)
    service_json.update(host='host_name')
    errors, messages = [], []
    for check_name in service_json['health_checks']:
        check_type, url = service_json['health_checks'][check_name]
        try:
            checker = getattr(checks, check_type)
        except AttributeError:
            err = '  check-type "{0}" does not exist in ymir.checks'
            err = err.format(check_type)
            errors.append(err)
            return errors, messages
        tmp = service_json.copy()
        tmp.update(dict(host='host'))
        try:
            url = url.format(**service_json)
        except KeyError, exc:
            msg = 'url "{0}" could not be formatted: missing {1}'
            msg = msg.format(url, str(exc))
            errors.append(msg)
        else:
            checker_validator = getattr(
                checker, 'validate', lambda url: None)
            err = checker_validator(url)
            if err:
                errors.append(err)
            messages.append(' .. ok: {0}'.format([
                check_name, check_type, url]))
    return errors, messages


def print_errs(msg, (errors, messages), quiet=False, die=False, report=_report):
    """ helper for main validation functions """
    err = "print_errs requires a tuple of (errors,messages)"
    assert isinstance(errors, list), err
    assert isinstance(messages, list), err
    if msg:
        report(msg)
    for e in errors:
        report(red('  error[{0}]: '.format(errors.index(e))) + str(e))
    for m in messages:
        report(green('   {0}'.format(m)))
    if errors and die:
        raise SystemExit(str(errors))


def validate(service_json, schema=None, simple=True, quiet=False):
    """ validate service json is 2 step.  when simple==True,
        validation exits early after running against the main
        JSON schema.  otherwise, the service will be instantiated
        and sanity-checked against real-world requirements such as
        actually existing security-groups, keyfiles, etc.
    """
    report = util.NOOP if quiet else _report
    print_errs(
        '',
        validate_file(service_json, schema, report=report),
        quiet=True, die=True)

    if simple:
        return True

    # simple validation has succeded, begin second phase.
    # the schema can be loaded, so build a service object.
    # the service object can then begin to validate itself
    report('Instantiating service to scrutinize it..')
    service = yapi.load_service_from_json(service_json, quiet=quiet)
    report = util.NOOP if quiet else service.report

    print_errs(
        'checking content in `health_checks` field..',
        validate_health_checks(service),
        report=report,)
    if not isinstance(service, beanstalk.ElasticBeanstalkService):
        print_errs('checking AWS keypair at field `key_name`..',
                   validate_keypairs(service), report=report,)
        print_errs('checking puppet-librarian\'s metadata.json',
                   puppet.validate_metadata_file(service._puppet_metadata),
                   report=report)
        print_errs(
            'checking AWS security groups in field `security_groups` exist..',
            validate_security_groups(service), report=report,)
        print_errs('checking puppet code validates with puppet parser..',
                   validate_puppet(service), report=report,)
        print_errs('checking puppet templates for undefined variables..',
                   validate_puppet_templates(service), report=report,)


def validate_file(fname, schema=None, report=util.NOOP, quiet=False):
    """ naive schema validation for service.json """
    errors, messages = [], []
    report = report if not quiet else util.NOOP
    if schema:
        report('validating file using explicit schema: {0}'.format(schema))
    err = 'got {0} instead of string for fname'.format(fname)
    assert isinstance(fname, basestring), err
    tmp = yapi.load_json(fname)
    if schema is None:
        schema = yschema.choose_schema(tmp, quiet=quiet)
    is_eb = schema.schema_name == 'beanstalk_schema'
    try:
        schema(tmp)
    except voluptuous.Invalid, e:
        msg = "error validating {0}:\n\n{1}"
        msg = msg.format(os.path.abspath(fname), e)
        return [msg], []
    SERVICE_ROOT = os.path.dirname(fname)
    SERVICE_ROOT = os.path.abspath(SERVICE_ROOT)
    if is_eb:
        return [], []
    files = tmp['setup_list'] + tmp['provision_list']
    for _file in files:
        no_protocol = '://' not in _file
        abspath = os.path.join(SERVICE_ROOT, _file)
        if no_protocol and not os.path.exists(abspath):
            err = ('Files mentioned in service json '
                   'must exist relative to {0}, but {1}'
                   ' was not found').format(
                SERVICE_ROOT, _file)
            return [err], []
    return errors, messages
