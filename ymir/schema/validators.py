# -*- coding: utf-8 -*-
""" ymir.schema.validators
"""
import os
from voluptuous import Invalid


def nested_vagrant_validator(dct, ):
    """ """
    if not isinstance(dct, dict):
        err = ("expected hash for key @ `vagrant`")
        raise Invalid(err)
    for key in 'name boot_timeout box box_check_update sync_disabled ram cpus'.split():
        if key not in dct:
            err = 'key at `vagrant` would contain sub-key "{0}"'
            raise Invalid(err.format(key))


def filepath_validator(string, key='unknown'):
    """ """
    if not isinstance(string, basestring):
        raise Invalid("expected string for key @ `{0}`".format(
            key))
    string = string.strip()
    if string.startswith("~"):
        string = os.path.expanduser(string)
    if not os.path.isabs(string):
        string = os.path.abspath(string)
    if not os.path.exists(string):
        err = "filepath '{0}' at `{1}` does not exist"
        raise Invalid(err.format(string, key))
    if not os.path.isfile(string):
        err = "filepath '{0}' at `{1}` exists, but is not a file"
        raise Invalid(err.format(string, key))

_validate_extends_field = lambda val: filepath_validator(val, key="extends")


def list_of_dicts(lst, key=None):
    """ """
    if not isinstance(lst, list):
        err = ("expected list of strings for key @ `{0}`")
        err = err.format(key or 'unknown')
        raise Invalid(err)
    for i, x in enumerate(lst):
        if not isinstance(x, dict):
            err = ('expected JSON but top[{0}][{1}] is {2}')
            err = err.format(key, i, type(x))
            raise Invalid(err)


def list_of_strings(lst, key=None):
    if not isinstance(lst, list):
        err = ("expected list of strings for key @ `{0}`, got {1}")
        err = err.format(key or 'unknown', str(list))
        raise Invalid(err)
    for i, x in enumerate(lst):
        if not isinstance(x, basestring):
            print lst
            err = (
                'expected string for key@`{0}`, but index {1} is "{3}" of type {2}')
            err = err.format(
                key, i, type(x).__name__, x)
            raise Invalid(err)

string_or_int = lambda x: isinstance(x, (unicode, int))
_validate_sl_field = lambda lst: list_of_strings(lst, key='setup_list')
_validate_sg_field = lambda lst: list_of_strings(lst, key='security_groups')
_validate_pl_field = lambda lst: list_of_strings(lst, key='provision_list')


def _validate_puppet_parser(x):
    """ """
    if x != 'future':
        err = "puppet_parser has only one acceptable value: 'future'"
        raise Invalid(err)
