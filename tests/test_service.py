# -*- coding: utf-8 -*-
"""
"""
from ymir import api

import mock
from peak.util.imports import lazyModule
from .common import skeleton_json_path, mock_aws

yservice = lazyModule('ymir.service')


@mock_aws
def test_load_skeleton_service():
    service = api.load_service_from_json(skeleton_json_path)
    assert isinstance(service, yservice.AbstractService)
    return service


def test_service_has_important_callables():
    service = test_load_skeleton_service()
    for x in service._fabric_commands:
        assert callable(getattr(service, x))
    assert callable(service.ssh_ctx)
    assert callable(service.fabric_install)
