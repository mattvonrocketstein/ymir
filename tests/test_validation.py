# -*- coding: utf-8 -*-
"""
"""
import os
import shutil
import contextlib

import mock
import demjson
from fabric import api

from ymir import validation
from ymir.util import TemporaryDirectory
from ymir import api as yapi
from tests import common as test_common


def test_skeleton_json_exists():
    """ skeleton json must exist """
    assert os.path.exists(test_common.skeleton_json_path)


def test_skeleton_json_decodes():
    """ skeleton json should actually be json """
    return demjson.decode_file(test_common.skeleton_json_path)


def test_validate_skeleton_json():
    """ skeleton json should pass naive validation """
    json = test_skeleton_json_decodes()
    assert validation.validate(test_common.skeleton_json_path) == True


@test_common.mock_aws
@mock.patch('ymir.validation.validate_simple')
@mock.patch('ymir.validation.validate_health_checks')
@mock.patch('ymir.validation.validate_security_groups')
@mock.patch('ymir.validation.validate_puppet_templates')
@mock.patch('ymir.validation.validate_puppet')
@mock.patch('ymir.validation.validate_keypairs')
def test_validate_outermost(*mocks):
    """ confirm that ymir.validation.validate() calls
        each of the other validation subroutines
    """
    for m in mocks:
        errors = messages = warnings = []
        m.return_value = errors, warnings, messages
    with test_common.demo_service() as ctx:
        validation.validate(service_json_file=ctx.service_json, simple=False)
        for m in mocks:
            assert m.called


@test_common.mock_aws
def test_validate_puppet_with_no_files():
    with test_common.demo_service() as ctx:
        ctx.rewrite_json(ymir_build_puppet=True)
        service = ctx.get_service()
        api.local('find {0} -name "*.pp"|xargs rm'.format(ctx.service_dir))
        errors, warnings, messages = validation.validate_puppet(service)
        err = ('there were no puppet files to validate, '
               'so there should be no errors')
        assert errors == [], err
        shutil.rmtree(service._puppet_dir)
        errors, warnings, messages = validation.validate_puppet(service)
        err = ('deleting the services puppet directory'
               ' should cause an error in puppet validation')
        assert errors, err


@test_common.mock_aws
def test_validate_puppet_with_skeleton_files():
    """ all the puppet files in the skeleton should validate.
        NB: this test fails with tox but works otherwise.  what gives?
    """
    with test_common.demo_service() as ctx:
        ctx.rewrite_json(ymir_build_puppet=True)
        service = ctx.get_service()
        errors, warnings, messages = validation.validate_puppet(service)
        err = 'skeleton-included puppet files should all validate'
        assert errors == [], err


@test_common.mock_aws
def test_validate_puppet_with_bad_files():
    with test_common.demo_service() as ctx:
        ctx.rewrite_json(ymir_build_puppet=True)
        service = ctx.get_service()
        bad_puppet_code = ">random string! is; =bad puppet code'"
        bad_puppet_file = os.path.join(service._puppet_dir, 'bad_puppet.pp')
        with open(bad_puppet_file, 'w') as fhandle:
            fhandle.write(bad_puppet_code)
        errors, warnings, messages = validation.validate_puppet(service)
        err = 'service with bad puppet files should not validate'
        assert len(errors) > 0, err
        errors = [x for x in errors if bad_puppet_file in x]
        err = ('at least one of the validation errors '
               'should mention the file with bad puppet code')
        assert len(errors) > 0, err


@test_common.mock_aws
def test_validate_puppet_templates_with_skeleton():
    with test_common.demo_service() as ctx:
        ctx.rewrite_json(ymir_build_puppet=True)
        service = ctx.get_service()
        errors, warnings, messages = validation.validate_puppet_templates(
            service)
        err = 'service with skeleton puppet files should validate'
        assert not errors


@test_common.mock_aws
def test_validate_puppet_templates_with_bad_puppet_vars():
    with test_common.demo_service() as ctx:
        ctx.rewrite_json(ymir_build_puppet=True)
        service = ctx.get_service()
        bad_puppet_template = "<%= @undefined_puppet_template_variable %>"
        bad_puppet_file = os.path.join(
            service._puppet_dir,
            'modules', 'ymir', 'templates',
            'bad_template.erb')
        with open(bad_puppet_file, 'w') as fhandle:
            fhandle.write(bad_puppet_template)
        errors, warnings, messages = validation.validate_puppet_templates(
            service)
        err = 'service with bad puppet template files should not validate'
        assert errors, err
        errors = [x for x in errors if bad_puppet_file in x]
        err = ('at least one of the validation errors should '
               'mention the puppet template file with the '
               'undefined variable')
        assert errors, err


@test_common.mock_aws
def test_validate_keypairs():
    """ """
    with test_common.demo_service() as ctx:
        service_json = ctx.get_json()
        service_json['pem'] = '/does_not_exist!'
        service_json['key_name'] = '!does_not_exist!'
        ctx.rewrite_json(service_json)
        service = ctx.get_service()
        errors, warnings, messages = validation.validate_keypairs(service)
        pem_errors = [x for x in errors if service_json['pem'] in x]
        err = 'missing pem file should cause an error in keypair validation'
        assert pem_errors, err
        err = ('nonexistant AWS keypair should '
               'cause an error in keypair validation')
        key_errors = [x for x in errors if service_json['key_name'] in x]
        assert key_errors, err
