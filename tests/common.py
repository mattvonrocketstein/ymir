# -*- coding: utf-8 -*-
"""
"""
import os
import contextlib

import addict
import mock
import demjson
from fabric import api

from ymir.util import TemporaryDirectory, NOOP
from ymir import skeleton
from ymir import api as yapi

skeleton_dir = os.path.dirname(skeleton.__file__)
skeleton_json_path = os.path.join(skeleton_dir, 'service.json')


@contextlib.contextmanager
def fake_context_manager():
    yield


def fake_aws_conn():
    """ """
    conn = mock.Mock()
    conn.get_all_security_groups.return_value = []
    fake_sg = mock.Mock()
    fake_sg.rules = []
    conn.create_security_group.return_value = fake_sg
    return conn


def mock_service():
    """ """
    service = mock.Mock()
    service._service_json = {}
    service.facts = {}
    service.template_data = mock.Mock()
    service.template_data.return_value = service._service_json
    service._status = mock.Mock(return_value=dict(ip=''))
    return service

from contextlib import contextmanager
noop_ctx = contextmanager(lambda *args, **kargs: (yield))


def mock_aws(fxn):
    def newf(*args, **kargs):
        with contextlib.nested(
                mock.patch.dict(os.environ, dict(AWS_PROFILE="!nonsense!")),
                mock.patch('ymir.util.aws.get_tags', lambda *args: {}),
                mock.patch('ymir.util.aws.get_conn', fake_aws_conn),
                mock.patch('ymir.util.aws.get_keypair_names', lambda *args: [])):
            return fxn(*args, **kargs)
    return newf


@contextlib.contextmanager
def demo_service(service_json='service.json'):
    service_name = 'demo_service'
    with TemporaryDirectory() as tmp_dir:
        service_dir = os.path.join(tmp_dir, service_name)
        with api.lcd(tmp_dir):
            cmd = api.local('ymir init {0}'.format(service_name))
            assert not cmd.failed, "`ymir init` exited with bad status"
            err = '`ymir init` did not create directory'
            assert os.path.exists(service_dir), err
            with api.lcd(service_dir):
                service_json = os.path.join(service_dir, service_json)
                sg_json = os.path.join(service_dir, 'security_groups.json')
                #

                def get_service():
                    out = yapi.load_service_from_json(service_json, quiet=True)
                    out.ssh_ctx = fake_context_manager
                    return out
                get_json = lambda: demjson.decode_file(service_json)
                get_sg_json = lambda: demjson.decode_file(sg_json)

                def rewrite_json(*args, **kargs):
                    assert bool(args) ^ bool(kargs)
                    if args:
                        args = list(args)
                        new_json = args.pop()
                        assert not args
                    if kargs:
                        new_json = get_json()
                        new_json.update(**kargs)
                    with open(service_json, 'w') as fhandle:
                        fhandle.write(demjson.encode(new_json))

                def rewrite_sg_json(new_json):
                    with open(sg_json, 'w') as fhandle:
                        fhandle.write(demjson.encode(new_json))
                test_service_ctx = addict.Dict(
                    get_service=get_service,
                    get_json=get_json,
                    get_sg_json=get_sg_json,
                    rewrite_json=rewrite_json,
                    rewrite_sg_json=rewrite_sg_json,
                    service_name=service_name,
                    service_dir=service_dir,
                    service_json=service_json,
                    sg_json=sg_json,
                    tmpdir=tmp_dir,
                    tmp_dir=tmp_dir,
                )
                yield test_service_ctx
