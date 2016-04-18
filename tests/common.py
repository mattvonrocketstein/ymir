# -*- coding: utf-8 -*-
"""
"""
import os
import inspect
import contextlib

import mock
from ymir import skeleton

skeleton_dir = os.path.dirname(inspect.getfile(skeleton))

skeleton_json_path = os.path.join(skeleton_dir, 'service.json')


def fake_aws_conn():
    """ """
    return mock.Mock()


def mock_aws(fxn):
    def newf(*args, **kargs):
        with contextlib.nested(
                mock.patch('ymir.util.get_conn', fake_aws_conn),
                mock.patch('ymir.util.get_tags', lambda *args: {})):
            return fxn(*args, **kargs)
    return newf
