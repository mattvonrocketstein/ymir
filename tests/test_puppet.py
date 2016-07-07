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
@mock.patch('ymir.mixins.puppet.rsync_project')
@mock.patch('ymir.mixins.puppet.PuppetMixin._require_rsync')
def test_copy_puppet(rsync_mock, _require_rsync):
    with test_common.demo_service() as ctx:
        ctx.rewrite_json(ymir_build_puppet=True)
        service = ctx.get_service()
        service.copy_puppet()
        err = 'copy_puppet did not invoke rsync!'
        assert rsync_mock.called, err


@test_common.mock_aws
def test_puppet_template_vars():
    with test_common.demo_service() as ctx:
        ctx.rewrite_json(ymir_build_puppet=True)
        service = ctx.get_service()
        file_to_vars_map = service._puppet_template_vars
        aggreg = lambda x, y: x + y
        all_vars = reduce(aggreg, file_to_vars_map.values())
        # operatingsystem variable is used in motd.erb templates
        assert 'operatingsystem' in all_vars


@test_common.mock_aws
@mock.patch('ymir.mixins._ansible.AnsibleMixin._provision_ansible')
@mock.patch('fabric.api.run')
@mock.patch('ymir.mixins.puppet.PuppetMixin._has_rsync')
def test_require_rsync(has_rsync, run, _provision_ansible):
    has_rsync.return_value = False
    run.succeeded = False
    run.success = True
    with test_common.demo_service() as ctx:
        service = ctx.get_service()
        service._require_rsync()
        assert has_rsync.called
        _provision_ansible.assert_called_with(
            "--become -a 'name=rsync state=present' -m apt ")


@test_common.mock_aws
def test_copy_puppet_noop():
    # this time, the rsync_mock is missing.  if
    # the @noop_if_no_puppet_support decorator
    # is not working, this test will break (prompting for hostname)
    with test_common.demo_service() as ctx:
        ctx.rewrite_json(ymir_build_puppet=False)
        service = ctx.get_service()
        service.copy_puppet()
