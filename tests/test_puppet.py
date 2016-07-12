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
@mock.patch('ymir.util.puppet.run_puppet')
def test_provision_puppet(run_puppet):
    with test_common.demo_service() as ctx:
        ctx.rewrite_json(ymir_build_puppet=True)
        service = ctx.get_service()
        service._provision_puppet("puppet/zoo.pp")
        assert run_puppet.called


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
@mock.patch('ymir.mixins.packages.PackageMixin._update_system_packages')
def test_require_rsync(_update_system_packages, has_rsync, run, _provision_ansible):
    has_rsync.return_value = False
    run.succeeded = False
    _update_system_packages.return_value = True
    run.success = True
    _provision_ansible.return_value = True
    with test_common.demo_service() as ctx:
        service = ctx.get_service()
        service._require_rsync()
        assert has_rsync.called
        _provision_ansible.assert_called_with(
            '--become --module-name apt -a "name=rsync state=present"')


@test_common.mock_aws
def test_copy_puppet_noop():
    # this time, the rsync_mock is missing.  if
    # the @noop_if_no_puppet_support decorator
    # is not working, this test will break (prompting for hostname)
    with test_common.demo_service() as ctx:
        ctx.rewrite_json(ymir_build_puppet=False)
        service = ctx.get_service()
        service.copy_puppet()

from ymir.data import BadProvisionInstruction


@test_common.mock_aws
def test_run_provisioner():
    with test_common.demo_service() as ctx:
        service = ctx.get_service()
        provisioner_name, provision_instruction = 'foobar', 'baz'
        with pytest.raises(BadProvisionInstruction):
            service._run_provisioner(provisioner_name, provision_instruction)
