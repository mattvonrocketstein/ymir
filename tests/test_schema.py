# -*- coding: utf-8 -*-
import pytest
from ymir.schema.util import (
    list_of_dicts, Invalid, list_of_strings)


def test_list_of_dicts():
    with pytest.raises(Invalid):
        list_of_dicts("foo")
    with pytest.raises(Invalid):
        list_of_dicts(["string"])
    with pytest.raises(Invalid):
        list_of_dicts([1])
    list_of_dicts([{}])


def test_list_of_strings():
    with pytest.raises(Invalid):
        list_of_strings("foo")
    with pytest.raises(Invalid):
        list_of_strings([{}])
    with pytest.raises(Invalid):
        list_of_strings([1])
    list_of_strings(["string"])
