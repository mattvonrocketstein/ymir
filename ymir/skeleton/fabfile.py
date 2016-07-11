#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
\x1b[31mYmir Automation:\x1b[0m
  This is the \x1b[35mDemo\x1b[0m Service
"""
from fabric import api
from ymir import load_service_from_json, guess_service_json_file

YMIR_SERVICE_JSON = guess_service_json_file(default='service.json')

# Create the ymir service from the service description
service = load_service_from_json(YMIR_SERVICE_JSON)

# Install the standard service operations
# (like create, terminate, provision, etc) as fabric commands
service.fabric_install()


@api.task
def deploy(branch='master'):
    """ example usage: "fab deploy:branch=master" """
    service.report("deploy for branch {0} -> {1} is not defined yet".format(
        branch, service))


@api.task
def tail_syslog():
    """ example: tail syslog on remote server """
    with service.ssh_ctx():
        api.sudo('tail /var/log/syslog')
