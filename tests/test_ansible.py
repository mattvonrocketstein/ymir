# -*- coding: utf-8 -*-
""" tests.test_ansible
"""

import json
import mock
import pytest
import tests.common as test_common
from ymir.data import BadProvisionInstruction


def test_inventory(capsys):
    with test_common.demo_service('vagrant.json') as ctx:
        ctx.rewrite_json(
            service_defaults=dict(FOO='bar'))
        service = ctx.get_service()
        service.ansible_inventory()
        out, err = capsys.readouterr()
        print out
        try:
            inventory = json.loads(out.strip())
        except:
            err = "inventory operation must return parsable json on stdout"
            raise Exception, err
        try:
            assert inventory['vars']['FOO'] == 'bar'
        except KeyError:
            err = 'service_defaults key is missing from ansible inventory'
            raise Exception(err)
