# -*- coding: utf-8 -*-
import os
from fabric import api

import mock
import inspect
from peak.util.imports import lazyModule
from .common import skeleton_dir, skeleton_json_path, fake_aws_conn

yservice = lazyModule('ymir.service')

from ymir.util import TemporaryDirectory
from ymir import skeleton


def test_ymir_init():
    """ ymir init should work, and should copy all files from ymir.skeleton """
    service_name = 'demo_service'
    with TemporaryDirectory() as tmp_dir:
        service_dir = os.path.join(tmp_dir, service_name)
        service_json = os.path.join(service_dir, 'service.json')
        with api.lcd(tmp_dir):
            cmd = api.local('ymir init {0}'.format(service_name))
            assert not cmd.failed, "`ymir init` exited with bad status"
            err = '`ymir init` did not create directory'
            assert os.path.exists(service_dir), err
            err = '`ymir init {0}` did not copy file {0} from skeleton!'
            skeleton_files_and_dirs = []
            for root, dirs, files in os.walk(skeleton_dir):
                for name in files:
                    fullpath = os.path.join(root, name)
                    skeleton_files_and_dirs.append(
                        fullpath.replace(skeleton_dir + '/', ''))
                for name in dirs:
                    fullpath = os.path.join(root, name)
                    skeleton_files_and_dirs.append(
                        fullpath.replace(skeleton_dir + '/', ''))
            skeleton_files_and_dirs = [
                fname for fname in skeleton_files_and_dirs if
                not os.path.splitext(fname)[-1] == '.pyc'
            ]
            for fname in skeleton_files_and_dirs:
                file_copied_from_skeleton = os.path.join(service_dir, fname)
                this_err = err.format(file_copied_from_skeleton)
                assert os.path.exists(file_copied_from_skeleton), this_err

            #err = '`ymir init {0}` did not create service.json!'
            #assert os.path.exists(service_json), err.format(service_name)


def test_ymir_help():
    """ `ymir help` should work and should return correct status """
    with api.quiet():
        err = '`ymir -h` should always be a valid command line invocation'
        assert not api.local('ymir -h').failed, err
        err = '`ymir --help` should always be a valid command line invocation'
        assert not api.local('ymir --help').failed, err
        err = '`ymir help` should always be a valid command line invocation'
        assert not api.local('ymir help').failed, err


def test_ymir_invalid_arg():
    """ ymir invocation with bad argument should fail """
    with api.quiet():
        err = 'ymir invocation with a bad argument should fail'
        assert api.local('ymir bad_arg').failed, err


def test_ymir_sg():
    """ """
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
