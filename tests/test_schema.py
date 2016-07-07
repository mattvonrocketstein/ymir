# -*- coding: utf-8 -*-
import os
import pytest
from ymir.schema import validators as v
from ymir import schema
from ymir import api as yapi
import tests.common as test_common

Invalid = v.Invalid


def test_list_of_dicts():
    with pytest.raises(Invalid):
        v.list_of_dicts("foo")
    with pytest.raises(Invalid):
        v.list_of_dicts(["string"])
    with pytest.raises(Invalid):
        v.list_of_dicts([1])
    v.list_of_dicts([{}])


def test_filepath():
    with pytest.raises(Invalid):
        v.filepath_validator("sadkajshdlasjdlasdsda")
    with pytest.raises(Invalid):
        v.filepath_validator("~")
    v.filepath_validator(__file__)
    v.filepath_validator(__file__.replace("~", os.path.expanduser("~")))


def test_list_of_strings():
    with pytest.raises(Invalid):
        v.list_of_strings("foo")
    with pytest.raises(Invalid):
        v.list_of_strings([{}])
    with pytest.raises(Invalid):
        v.list_of_strings([1])
    v.list_of_strings(["string"])


def test_choose_ec2_schema():
    expected = schema.ec2_schema
    actual = schema.choose_schema(dict(instance_type='ec2'))
    assert actual == expected


def test_choose_vagrant_schema():
    expected = schema.vagrant_schema
    actual = schema.choose_schema(dict(instance_type='vagrant'))
    assert actual == expected


def test_choose_extension_schema():
    expected = schema.extension_schema
    actual = schema.choose_schema(dict(extends=__file__))
    assert actual == expected
