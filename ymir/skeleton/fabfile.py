#!/usr/bin/env python
"""
\x1b[31mYmir Automation:\x1b[0m
  This is the \x1b[35mDemo\x1b[0m Service
"""
import os, sys

import addict
from ymir.commands import ymir_load

DEBUG = False
YMIR_SERVICE_ROOT = os.path.dirname(__file__)
YMIR_SERVICE_JSON = os.path.join(YMIR_SERVICE_ROOT, 'service.json')

if not os.path.exists(YMIR_SERVICE_JSON):
    err = ("ymir expects to find 'service.json' alongside the fabfile"
           "..  please create {0} to continue.").format(
        YMIR_SERVICE_JSON)
    raise SystemExit(err)


_service = ymir_load(
    addict.Dict(service_json=YMIR_SERVICE_JSON),
    interactive=DEBUG)
_service.fabric_install()
