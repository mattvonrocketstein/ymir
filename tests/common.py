# -*- coding: utf-8 -*-
"""
"""
import os
import contextlib
import addict
import mock
from fabric import api
from ymir.util import TemporaryDirectory
from ymir import skeleton

skeleton_dir = os.path.dirname(skeleton.__file__)

skeleton_json_path = os.path.join(skeleton_dir, 'service.json')


def fake_aws_conn():
    """ """
    return mock.Mock()


def mock_aws(fxn):
    def newf(*args, **kargs):
        with contextlib.nested(
                mock.patch.dict(os.environ, dict(AWS_PROFILE="nonsense!")),
                mock.patch('ymir.util.get_conn', fake_aws_conn),
                mock.patch('ymir.util.get_tags', lambda *args: {}),
                mock.patch('ymir.util.get_keypair_names', lambda *args: [])):
            return fxn(*args, **kargs)
    return newf


@contextlib.contextmanager
def demo_service():
    service_name = 'demo_service'
    with TemporaryDirectory() as tmp_dir:
        service_dir = os.path.join(tmp_dir, service_name)
        with api.lcd(tmp_dir):
            cmd = api.local('ymir init {0}'.format(service_name))
            assert not cmd.failed, "`ymir init` exited with bad status"
            err = '`ymir init` did not create directory'
            assert os.path.exists(service_dir), err
            with api.lcd(service_dir):
                yield addict.Dict(
                    service_name=service_name,
                    service_dir=service_dir,
                    service_json=os.path.join(service_dir, 'service.json'),
                    tmpdir=tmp_dir,
                    tmp_dir=tmp_dir,
                )
