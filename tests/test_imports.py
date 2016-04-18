# -*- coding: utf-8 -*-
"""
"""
import mock
from .common import mock_aws


@mock_aws
def test_critical_imports():
    from ymir import load_service_from_json
    from ymir.skeleton import fabfile as fabby
