# -*- coding: utf-8 -*-
"""
"""
import pytest
import mock
from peak.util.imports import lazyModule

from ymir import api
from ymir.data import BadProvisionInstruction

import tests.common as test_common

yservice = lazyModule('ymir.service')


@test_common.mock_aws
def test_load_skeleton_service():
    service = api.load_service_from_json(test_common.skeleton_json_path)
    assert isinstance(service, yservice.AbstractService)
    return service


def test_ssh_config_string_prop():
    service = test_common.mock_service()
    #assert isinstance(service._ssh_config_string, basestring)


def test_service_has_important_callables():
    service = test_load_skeleton_service()
    for x in service._fabric_commands:
        assert callable(getattr(service, x))
    assert callable(service.ssh_ctx)
    assert callable(service.fabric_install)


@test_common.mock_aws
def test_run_provisioner():
    with test_common.demo_service() as ctx:
        service = ctx.get_service()
        provisioner_name, provision_instruction = 'foobar', 'baz'
        with pytest.raises(BadProvisionInstruction):
            service._run_provisioner(provisioner_name, provision_instruction)
