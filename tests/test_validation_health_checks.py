# -*- coding: utf-8 -*-
""" ymir/tests/test_validation_health_checks
"""
import pytest
import addict
import demjson
from ymir import validation
from ymir.util import TemporaryDirectory
from ymir import api as yapi
from tests import common as test_common


@test_common.mock_aws
def test_validate_health_checks():
    """ """
    with test_common.demo_service() as ctx:
        service = ctx.get_service()
        service_json = ctx.get_json()
        errors, messages = validation.validate_health_checks(service)
        err = 'skeleton json should have validating health checks'
        assert not errors, err
        service_json['health_checks'] = []  # should be dict
        ctx.rewrite_json(service_json)
        with pytest.raises(SystemExit):
            service = ctx.get_service()
        bad_check_type = 'nonexistant_check_type'
        service_json['health_checks'] = {
            "foo": [bad_check_type, 'localhost']}  # should be dict
        ctx.rewrite_json(service_json)
        service = ctx.get_service()
        errors, messages = validation.validate_health_checks(service)
        err = 'health_checks field with bad type should cause validation error'
        assert errors, err
        errors = [x for x in errors if bad_check_type in x]
        assert errors, err


@test_common.mock_aws
def test_validate_security_groups():
    """ """
    with test_common.demo_service() as ctx:
        service_json = ctx.get_json()
        bad_sg_name = '!does-not-exist!'
        service_json['security_groups'] = [bad_sg_name]
        ctx.rewrite_json(service_json)
        service = ctx.get_service()
        errors, messages = validation.validate_security_groups(service)
        errors = [x for x in errors if bad_sg_name in x]
        err = 'bad security group should trigger validation error'
        assert errors, err
        service.conn.get_all_security_groups.return_value = [
            addict.Dict(name=bad_sg_name)]
        errors, messages = validation.validate_security_groups(service)
        err = 'good security group name should not trigger validation error'
        assert not errors, err
