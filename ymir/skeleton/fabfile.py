#!/usr/bin/env python
"""
\x1b[31mYmir Automation:\x1b[0m
  This is the \x1b[35mDemo\x1b[0m Service
"""
import os, sys

try:
    import addict
    from ymir.commands import ymir_load as _load
except ImportError:
    err = ('This fabfile requires the ymir automation framework.  '
           'To continue, please follow the instructions at '
           'https://github.com/mattvonrocketstein/ymir')
    raise SystemExit(err)

DEBUG = False
YMIR_SERVICE_ROOT = os.path.dirname(__file__)
YMIR_SERVICE_JSON = os.path.join(YMIR_SERVICE_ROOT, 'service.json')

if not os.path.exists(YMIR_SERVICE_JSON):
    err = ("Your ymir service is misconfigured.  Expected "
           " to find 'service.json' alongside the fabfile, "
           "please create {0} to continue.").format(
        YMIR_SERVICE_JSON)
    raise SystemExit(err)

# Create the ymir service from the service description
_service = _load(
    addict.Dict(service_json=YMIR_SERVICE_JSON),
    interactive=DEBUG)

# Install service operations as fabric commands
_service.fabric_install()
