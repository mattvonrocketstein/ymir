# -*- coding: utf-8 -*-
import os
from fabric import api

import mock
from peak.util.imports import lazyModule
from .common import skeleton_dir, skeleton_json_path, fake_aws_conn

yservice = lazyModule('ymir.service')


def test_ymir_help():
    with api.quiet():
        err = '`ymir -h` should always be a valid command line invocation'
        assert not api.local('ymir -h').failed, err
        err = '`ymir --help` should always be a valid command line invocation'
        assert not api.local('ymir --help').failed, err
        err = '`ymir help` should always be a valid command line invocation'
        assert not api.local('ymir help').failed, err


def test_ymir_invalid_arg():
    with api.quiet():
        err = 'ymir invocation with a bad argument should fail'
        assert api.local('ymir bad_arg').failed, err


def test_ymir_sg():
    with api.quiet():
        err = '`{0}` should always require an argument or ./security_groups.json'
        assert api.local('ymir sg').failed, err.format('ymir sg')
        assert api.local('ymir security_group').failed, err.format(
            'ymir security_group')
        err = 'skeleton directory must contain security_groups.json'
        assert os.path.exists(
            os.path.join(skeleton_dir, 'security_groups.json')), err
        with api.lcd(skeleton_dir):
            err = 'default skeleton security group should fail as it has no ssh rule'
            assert api.local('ymir sg ./security_groups.json').failed, err


def test_ymir_validate():
    """ """
    with api.settings(warn_only=True):
        with api.lcd(skeleton_dir):
            err = 'ymir validate should fail without AWS_PROFILE envvar set'
            assert api.local('ymir validate').failed, err


def test_ymir_init():
    """ """
