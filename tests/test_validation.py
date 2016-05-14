# -*- coding: utf-8 -*-
"""
"""
import os
import demjson
import mock
import contextlib
from fabric import api

from ymir import validation
from ymir.util import TemporaryDirectory

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
@mock.patch('ymir.validation.validate_file')
@mock.patch('ymir.validation.validate_health_checks')
@mock.patch('ymir.validation.validate_named_sgs')
@mock.patch('ymir.validation.validate_puppet_templates')
@mock.patch('ymir.validation.validate_puppet')
@mock.patch('ymir.validation.validate_keypairs')
def test_validate_outermost(*mocks):
    for m in mocks:
        errors = messages = []
        m.return_value = errors, messages
    with test_common.demo_service() as ctx:
        validation.validate(service_json=ctx.service_json, simple=False)
        for m in mocks:
            assert m.called
