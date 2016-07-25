# -*- coding: utf-8 -*-
""" ymir.util._ansible
"""
import os
import json
from tempfile import NamedTemporaryFile

from fabric import api
from peak.util.imports import lazyModule

from ymir import data as ydata
from ymir.base import report as base_report
from ymir.util._report import eprint

yapi = lazyModule('ymir.api')

PLAYBOOK_CONTENT = '\n'.join([
    "- hosts: all",
    # "  user: {{user}}",
    "  become: yes",
    "  become_method: sudo",
    "  roles:",
    "  - {role: {{role_path}}{{env}}}",
])


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
        "ansible role '{0}' installed to ".format(role_name, role_dir))


def get_playbook_for_role(role_name, role_dir, report=base_report, **env):
    """ this provisioner applies a single ansible role.  this is more
        complicated than it sounds because there's no way to do this
        without a playbook, and so a temporary playbook is created just
        for this purpose.

        To pass ansible variables through to the role, you can use kwargs
        to this function.

        see also:
          https://groups.google.com/forum/#!topic/ansible-project/h-SGLuPDRrs
    """
    env = env.copy()
    env_string = ''
    for k, v in env.items():
        if isinstance(v, (bool, basestring, list)):
            v = json.dumps(v)
        else:
            err = ("ansible-role apply only supports passing "
                   "simple environment variables (strings or bools). "
                   "Found type '{0}' at name '{1}'")
            raise SystemExit(err.format(type(v), k))
        env_string += ', ' + ': '.join([k, v])
    ctx = dict(
        env=env_string,
        role_path=os.path.join(role_dir, role_name),
    )
    playbook_content = yapi.jinja_env.from_string(
        PLAYBOOK_CONTENT).render(**ctx)
    return playbook_content


def apply_ansible_role(role_name, role_dir, ansible_args='', report=base_report, **env):
    """ """
    assert isinstance(role_name, (basestring,))
    assert isinstance(role_dir, (basestring,))
    playbook_content = get_playbook_for_role(
        role_name, role_dir, report=report)
    require_ansible_role(role_name, role_dir, report=report)
    with NamedTemporaryFile() as tmpf:
        tmpf.write(playbook_content)
        tmpf.seek(0)
        msg = "created playbook {0} for applying role: {1}"
        report(ydata.SUCCESS + msg.format(tmpf.name, role_name))
        if env:
            report("dynamic playbook content:")
            eprint(playbook_content)
            eprint("\n")
        report("applying ansible role '{0}'".format(role_name))
        ansible_args = ansible_args if isinstance(ansible_args, (list,)) \
            else ansible_args.split()
        cmd = ['ansible-playbook', tmpf.name] + ansible_args
        cmd = " ".join(cmd)
        with api.settings(warn_only=True):
            success = api.local(cmd).succeeded
        icon = ydata.SUCCESS if success else ydata.FAIL
        msg = 'succeeded' if success else 'failed'
        report(icon + msg +
               " applying ansible role: {0}".format(role_name))
        return success
