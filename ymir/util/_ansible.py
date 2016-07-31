# -*- coding: utf-8 -*-
""" ymir.util._ansible
"""
import os

from fabric import api
from peak.util.imports import lazyModule

from ymir import data as ydata
from ymir.base import report as base_report

yapi = lazyModule('ymir.api')


def require_ansible_role(role_name, role_dir, report=base_report):
    """ """
    if role_name not in os.listdir(role_dir):
        report(ydata.FAIL +
               "role '{0}' not found in {1}".format(role_name, role_dir))
        result = api.local('ansible-galaxy install -p {role_dir} {role_name}'.format(
            role_dir=role_dir, role_name=role_name))
        if not result.succeeded:
            err = "missing role {0} could not be installed".format(
                role_name)
            raise RuntimeError(err)
    report(
        ydata.SUCCESS +
        "ansible role '{0}' installed to '{1}'".format(role_name, role_dir))
