# -*- coding: utf-8 -*-
""" ymir_tests.test_utils
"""
import os
import pytest
import mock
from ymir import util


def test_noop():
    util.NOOP()


def test_report():
    """ """
    util.report('label', 'message')


def test_get_conn_with_AWS_PROFILE_as_nonsense():
    """ """
    with mock.patch.dict(os.environ, {}):
        with pytest.raises(SystemExit):
            util.get_conn()
    with mock.patch.dict(os.environ, {'AWS_PROFILE': 'bd11cce2'}):
        with pytest.raises(SystemExit):
            util.get_conn()
