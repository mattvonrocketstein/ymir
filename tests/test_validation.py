# -*- coding: utf-8 -*-
"""
"""
import os
import demjson
from ymir import validation
from .common import skeleton_json_path


def test_skeleton_json_exists():
    assert os.path.exists(skeleton_json_path)


def test_skeleton_json_decodes():
    return demjson.decode_file(skeleton_json_path)


def test_validate_skeleton_json():
    """ """
    json = test_skeleton_json_decodes()
    assert validation.validate(skeleton_json_path)
