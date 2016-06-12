# -*- coding: utf-8 -*-
""" tests.test_puppet
"""
import mock
import pytest
import requests

import tests.common as test_common


@test_common.mock_aws
def test_puppet_support():
    with test_common.demo_service() as ctx:
        err = 'json field `ymir_build_puppet` has no affect on property `_supports_puppet`'
        ctx.rewrite_json(ymir_build_puppet=True)
        service = ctx.get_service()
        assert service._supports_puppet, err
        ctx.rewrite_json(ymir_build_puppet=False)
        service = ctx.get_service()
        assert not service._supports_puppet, err


@test_common.mock_aws
@mock.patch('ymir.puppet.rsync_project')
def test_copy_puppet(rsync_mock):
    with test_common.demo_service() as ctx:
        ctx.rewrite_json(ymir_build_puppet=True)
        service = ctx.get_service()
        service.copy_puppet()
        err = 'copy_puppet did not invoke rsync!'
        assert rsync_mock.called, err


@test_common.mock_aws
def test_copy_puppet_noop():
    # this time, the rsync_mock is missing.  if
    # the @noop_if_no_puppet_support decorator
    # is not working, this test will break (prompting for hostname)
    with test_common.demo_service() as ctx:
        ctx.rewrite_json(ymir_build_puppet=False)
        service = ctx.get_service()
        service.copy_puppet()
