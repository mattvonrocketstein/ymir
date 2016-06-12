# -*- coding: utf-8 -*-
""" tests.test_imports
"""
import mock
from .common import mock_aws


@mock_aws
def test_critical_imports():
    from ymir import load_service_from_json
    # this import will talk to AWS without the mock
    from ymir.skeleton import fabfile as fabby
    from ymir import util
    from ymir import service
