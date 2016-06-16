#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Dynamic inventory script for ansible that works with ymir data.
# See also: http://docs.ansible.com/ansible/intro_dynamic_inventory.html
#
import os
from ymir import load_service_from_json

YMIR_SERVICE_JSON = os.path.abspath(
    os.environ.get(
        'YMIR_SERVICE_JSON',
        os.path.join(
            os.path.dirname(__file__),
            '..',  # because this file resides in service_root/ansible
            'service.json')))

# Create the ymir service from the service description
_service = load_service_from_json(YMIR_SERVICE_JSON, quiet=True)

# print out JSON suitable for use as ansible dynamic inventory
_service.ansible_inventory()
