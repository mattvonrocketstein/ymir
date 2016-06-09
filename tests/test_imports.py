# -*- coding: utf-8 -*-
""" tests.test_imports
"""
import mock
from .common import mock_aws


@mock_aws
def test_critical_imports():
    from ymir import load_service_from_json
    from ymir.skeleton import fabfile as fabby
    from ymir import util
