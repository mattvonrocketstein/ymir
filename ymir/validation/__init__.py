# -*- coding: utf-8 -*-
""" ymir.validation
"""
import os
import logging

import voluptuous

from fabric import api
from peak.util.imports import lazyModule

from ymir import util
from ymir import checks
from ymir.util import puppet
from ymir.base import report as base_report

from ymir import schema as yschema
from ymir import data as ydata

yapi = lazyModule('ymir.api')
yservice = lazyModule('ymir.service')
beanstalk = lazyModule('ymir.beanstalk')
logger = logging.getLogger(__name__)
_report = lambda msg: base_report('ymir.validation', msg)


@util.declare_validator
def validate_puppet(service):
    """ runs puppet parser validation on puppet files contained
        inside the given service.  NB: this checks all the puppet
        code, not just things things in the service.json `setup_list`
        and `provision_list` fields
    """
    errors, warnings, messages = [], [], []
    pdir = service._puppet_dir
    if service._supports_puppet and not os.path.exists(pdir):
        msg = 'puppet directory does not exist @ {0}'
        msg = msg.format(pdir)
        errors.append(msg)
    elif not service._supports_puppet and os.path.exists(pdir):
        msg = "puppet directory is present, but `ymir_build_puppet` is false"
        errors.append(msg)
    elif service._supports_puppet:
        parser = service.template_data()['puppet_parser']
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
                    messages.append(filename)
    return errors, warnings, messages


@util.declare_validator
def validate_puppet_templates(service):
    """ validates that variables mentioned in puppet
        templates are defined in service.json
    """
    errors, warnings, messages = [], [], []
    if not service._supports_puppet:
        messages = [
            "`ymir_build_puppet` is false supported for this service, skipping"]
        return errors, warnings, messages
    default_facts = puppet.DEFAULT_FACTS

    service_vars = service.facts.keys()
    service_vars += default_facts
    for f, template_vars in service._get_puppet_template_vars().items():
        for template_var in template_vars:
            if template_var not in service_vars:
                msg = ("template {0} uses variable `{1}` "
                       "which is not defined for service").format(
                    f, template_var)
                errors.append(msg)
    return errors, warnings, messages


@util.declare_validator
def validate_keypairs(service):
    """ validates that keypairs mentioned in service.json
        are present on the filesystem and on AWS with the
        current account
    """
    errors, warnings, messages = [], [], []
    service_data = service._service_json
    pem_file = service_data.get('pem')
    pem_file = os.path.expanduser(pem_file)
    if not os.path.exists(pem_file):
        errors.append('pem file is not present: ' + pem_file)
    keys = util.get_keypair_names()
    key_name = service._service_json['key_name']
    if key_name not in keys:
        errors.append(
            'aws keypair {0} not found in any of {1} keys'.format(key_name, len(keys)))
    return errors, warnings, messages


@util.declare_validator
def validate_vagrant(service):
    """ """
    errors, warnings, messages = [], [], []
    return errors, warnings, messages


def validate_security_groups_json(service):
    """ validates that if security_groups.json is present,
        it the values there jive with what's found in
        service_json['security_groups']
    """
    groups = service._service_json['security_groups']
    errors, warnings, messages = [], [], []
    sg_json = service._sg_json
    if not service._sg_file:
        msg = "this service doesn't have a security_groups.json file."
        messages.append(msg)
    elif service._sg_file and sg_json is None:
        err = "security_groups.json is present but does not decode as JSON"
        errors.append(err)
    elif service._sg_file and sg_json:
        try:
            yschema.SGFileSchema(sg_json)
        except (voluptuous.MultipleInvalid,) as exc:
            err = "{0} does not match SGFileSchema".format(service._sg_file)
            errors.append(err)
            errors.append(str(exc))
        else:
            set1 = set([group['name'] for group in sg_json])
            set2 = set(groups)
            if set1 != set2:
                warnings.append(
                    "mismatch between names in {0} and service.json".format(
                        service._sg_file))
                warnings.append("{0} vs {1}".format(set1, set2))
    return errors, warnings, messages


def validate_security_groups(service):
    """ validates that named security groups mentioned
        in service.json are defined according to AWS
        with the current account
    """
    groups = service._service_json['security_groups']
    errors, warnings, messages = [], [], []
    # filter for only named groups, in case the security_groups field
    # eventually supports more complete data (like security_groups.json)
    configured_sgs = [x for x in groups if isinstance(x, basestring)]
    actual_sgs = [x.name for x in service.conn.get_all_security_groups()]
    for sg in configured_sgs:
        if sg not in actual_sgs:
            err = "name `{0}` mentioned in security_groups is missing from AWS"
            errors.append(err.format(sg))
    return errors, warnings, messages


@util.declare_validator
def validate_health_checks(service):
    """ """
    # here we fake the host value just for validation because we
    # don't actually know whether this service has been bootstrapped or not
    service_json = service.template_data()
    service_json.update(host='host_name')
    service_json.update(service.facts)
    errors, warnings, messages = [], [], []
    for check_name in service_json['health_checks']:
        check_type, url = service_json['health_checks'][check_name]
        try:
            checker = getattr(checks, check_type.replace('-', '_'))
        except AttributeError:
            err = '  check-type "{0}" does not exist in ymir.checks'
            err = err.format(check_type)
            errors.append(err)
            continue
        tmp = service_json.copy()
        tmp.update(dict(host='host'))
        try:
            url = yapi.str_reflect(url, service_json)
        except yapi.ReflectionError as exc:
            msg = 'url "{0}" could not be formatted: missing {1}'
            msg = msg.format(url, str(exc))
            errors.append(msg)
        else:
            checker_validator = getattr(
                checker, 'validate', None)
            if checker_validator is None:
                warnings.append("checker '{0}' has no validation defined".format(
                    checker.__name__))
            else:
                err = checker_validator(url)
                if err:
                    errors.append(err)
                else:
                    messages.append('{0}'.format([
                        check_name, '{0}://{1}'.format(check_type, url)]))
    return errors, warnings, messages


def print_errs(msg, validator_result, quiet=False, die=False, report=_report):
    """ helper for main validation functions """
    err = "print_errs requires a tuple of (errors, warnings, messages)"
    try:
        (errors, warnings, messages) = validator_result
    except ValueError:
        raise ValueError(err + ", got: {0}".format(validator_result))
    for tmp in (errors, warnings, messages):
        assert isinstance(tmp, list), err
    if msg:
        report(msg)
    space2 = '  '
    _map = {ydata.FAIL: errors,
            ydata.SUCCESS: messages,
            ydata.WARN: warnings}
    for icon, _list in _map.items():
        for msg in _list:
            report(space2 + icon + str(msg))
    if errors and die:
        raise SystemExit("encountered {0} errors".format(len(errors)))


def validate(service_json, schema=None, simple=True, quiet=False):
    """ validate service json is 2 step.  when simple==True,
        validation exits early after running against the main
        JSON schema.  otherwise, the service will be instantiated
        and sanity-checked against real-world requirements such as
        actually existing security-groups, keyfiles, etc.
    """
    report = util.NOOP if quiet else _report
    print_errs(
        '', validate_file(service_json, schema, report=report),
        quiet=True, die=True)
    if simple:
        return True

    # simple validation has succeeded, begin second phase.
    # the schema can be loaded, so build a service object.
    # the service object can then begin to validate itself
    # quiet or report('Instantiating service to scrutinize it..')
    service = yapi.load_service_from_json(service_json, quiet=quiet)
    report = util.NOOP if quiet else service.report

    print_errs(
        'checking content in `health_checks` field..',
        validate_health_checks(service),
        report=report,)
    if isinstance(service, yservice.AmazonService):
        print_errs(
            'checking AWS security groups in field `security_groups` exist..',
            validate_security_groups(service), report=report,)
        print_errs(
            'checking for agreement between `security_groups` field and security_groups.json file..',
            validate_security_groups_json(service), report=report,)
        print_errs('checking AWS keypair at field `key_name`..',
                   validate_keypairs(service), report=report,)
    print_errs('checking puppet-librarian\'s metadata.json',
               validate_metadata_file(service._puppet_metadata),
               report=report)
    print_errs('checking puppet code validates with puppet parser..',
               validate_puppet(service), report=report,)
    print_errs('checking puppet templates for undefined variables..',
               validate_puppet_templates(service), report=report,)


@util.declare_validator
def validate_metadata_file(metadata_f):
    """ returns a list of errors encountered while validating
        a puppet metadata.json file
    """
    errors, warnings, messages = [], [], []
    if not os.path.exists(metadata_f):
        errors.append('{0} does not exist!'.format(metadata_f))
    else:
        if util.has_gem('metadata-json-lint'):
            cmd_t = 'metadata-json-lint {0}'
            with api.quiet():
                x = api.local(cmd_t.format(metadata_f), capture=True)
            error = x.return_code != 0
            if error:
                errors.append('could not validate {0}'.format(metadata_f))
                errors.append(x.stderr.strip())
        else:
            errors.append(
                'cannot validate.  '
                'run "gem install metadata-json-lint" first')
    return errors, warnings, messages


def validate_file(fname, schema=None, report=util.NOOP, quiet=False):
    """ naive schema validation for service.json """
    errors, warnings, messages = [], [], []
    report = report if not quiet else util.NOOP
    # if schema:
    #    report('validating file using explicit schema: {0}'.format(
    #        yellow(schema.schema_name)))
    err = 'got {0} instead of string for fname'.format(fname)
    assert isinstance(fname, basestring), err
    tmp = yapi.load_json(fname)
    if schema is None:
        schema = yschema.choose_schema(tmp)
    is_eb = schema.schema_name == 'beanstalk_schema'
    try:
        schema(tmp)
    except voluptuous.Invalid, e:
        msg = "error validating {0}:\n\n{1}"
        msg = msg.format(os.path.abspath(fname), e)
        return [msg], [], []
    SERVICE_ROOT = os.path.dirname(fname)
    SERVICE_ROOT = os.path.abspath(SERVICE_ROOT)
    if is_eb:
        return [], [], []
    files = tmp['setup_list'] + tmp['provision_list']
    for _file in files:
        no_protocol = '://' not in _file
        abspath = os.path.join(SERVICE_ROOT, _file)
        if no_protocol and not os.path.exists(abspath):
            err = ('Files mentioned in service json '
                   'must exist relative to {0}, but {1}'
                   ' was not found').format(
                SERVICE_ROOT, _file)
            return [err], [], []
    return errors, warnings, messages
