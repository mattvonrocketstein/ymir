# -*- coding: utf-8 -*-
"""
"""
from ymir import api

import mock
from peak.util.imports import lazyModule
import tests.common as common

yservice = lazyModule('ymir.service')


@common.mock_aws
def test_load_skeleton_service():
    service = api.load_service_from_json(common.skeleton_json_path)
    assert isinstance(service, yservice.AbstractService)
    return service


def test_ssh_config_string_prop():
    service = common.mock_service()
    #assert isinstance(service._ssh_config_string, basestring)


def test_service_has_important_callables():
    service = test_load_skeleton_service()
    for x in service._fabric_commands:
        assert callable(getattr(service, x))
    assert callable(service.ssh_ctx)
    assert callable(service.fabric_install)
