# -*- coding: utf-8 -*-
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
    assert callable(service.run)
    assert callable(service.sudo)
    assert callable(service.ssh_ctx)
    assert callable(service.fabric_install)
    assert callable(service.provision)
#from smashlib import embed; embed()
