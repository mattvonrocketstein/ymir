# -*- coding: utf-8 -*-
""" ymir.util

    Mostly AWS utility functions
"""
from __future__ import print_function

import os
import inspect
import shutil
import socket
from functools import wraps

import yurl
from fabric import api
from fabric.contrib.files import exists as remote_exists

from ._report import eprint
from ._fabric import has_gem, list_dir
from .shell import unexpand
from .backports import TemporaryDirectory
from ymir.data import OPERATION_MAGIC
from . import aws

NOOP = lambda *args, **kargs: None

remote_path_exists = remote_exists

__all__ = [x.__name__ for x in [
    aws,
    TemporaryDirectory, NOOP,
    unexpand, list_dir,
    has_gem,
]]


def declare_operation(fxn):
    """ """
    setattr(fxn, OPERATION_MAGIC, True)
    return fxn


def is_operation(obj, name):
    """ """
    try:
        # get things from the parent class, because we don't
        # want to trigger the evaluation of properties by
        # retrieving from the object instance
        obj = getattr(obj.__class__, name)
    except AttributeError:
        # only instance methods can be declared operations,
        # and naturally all instance methods should be present
        # on the parent class
        return False
    return callable(obj) and hasattr(obj, OPERATION_MAGIC)


def split_instruction(instruction):
    """ here, `instruction` is an item from either
        setup_list or provision_list
    """
    protocol = yurl.URL(instruction).scheme
    # protocol is used to determine instance-method for
    # dispatch, so there are no dashes allowed
    protocol = protocol.replace('-', '_')
    assert protocol, "protocol is missing: " + str(instruction)
    raw_instruction = instruction[
        len(protocol) + len('://'):]
    return protocol, raw_instruction
split_check = split_instruction


def report(label, msg, *args, **kargs):
    """ 'print' shortcut that includes some color and formatting """
    if 'section' in kargs:
        eprint('-' * 80)
    template = '\x1b[31;01m{0}:\x1b[39;49;00m {1} {2}'
    # if Service subclasses are embedded directly into fabfiles, there
    # is a need for a lot of private variables to control the namespace
    # fabric publishes as commands.
    label = label.replace('_', '')
    eprint(template.format(label, msg, args or ''))


def require_running_instance(fxn):
    """ a decorator you can apply to service operations that
        can only work when the service is already up and running.
        this decorator is ONLY for use with Service instance methods!
        it should work on any type of service-subclass as long as that
        subclass has a correctly written _status() method
    """
    @wraps(fxn)
    def newf(self, *args, **kargs):
        cm_data = self._status()
        if cm_data['status'] == 'running':
            return fxn(self, *args, **kargs)
        else:
            self.report(
                "need an instance to run `{0}` command".format(fxn.__name__))
            self.report("no instance found!")
            raise SystemExit(1)
    return newf


def shell(**namespace):
    """ """
    try:
        from smashlib import embed
        embed(user_ns=namespace)
    except ImportError as e:
        eprint('you need smashlib or ipython installed to run the shell!')
        eprint("original error: " + str(e))
        raise


def mosh(ip, username='ubuntu', pem=None):
    """ connect to remote host using mosh """
    assert ip is not None
    pem = '-i ' + pem if pem else ''
    cmd = 'mosh --ssh="ssh {pem}" {user}@{host}'.format(
        pem=pem, user=username, host=ip)
    with api.settings(warn_only=True):
        return api.local(cmd)


def ssh(ip, username='ubuntu', port='22', pem=None):
    """ connect to remote host using ssh """
    assert ip is not None
    if ':' in ip:
        ip, port = ip.split(':')
    cmd = "ssh -o StrictHostKeyChecking=no -p {2} -l {0} {1}".format(
        username, ip, port)
    if pem is not None:
        cmd += ' -i {0}'.format(pem)
    with api.settings(warn_only=True):
        api.local(cmd)


def ssh_ctx(ip, user='ubuntu', pem=None):
    """ context manager for use with fabric """
    assert ip is not None
    ctx = dict(user=user, host_string=ip)
    if pem is not None:
        ctx.update(key_filename=pem)
    return api.settings(**ctx)


def is_port_open(host, port):
    """ used by ymir.checks """
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex((host, int(port)))
    return result == 0

# http://stackoverflow.com/questions/1868714/how-do-i-copy-an-entire-directory-of-files-into-an-existing-directory-using-pyth


def copytree(src, dst, symlinks=False, ignore=None):
    """ shutil.copytree is broken/weird """
    if not os.path.exists(dst):
        os.makedirs(dst)
    for item in os.listdir(src):
        s = os.path.join(src, item)
        d = os.path.join(dst, item)
        if os.path.isdir(s):
            copytree(s, d, symlinks, ignore)
        else:
            if not os.path.exists(d) or \
                    os.stat(src).st_mtime - os.stat(dst).st_mtime > 1:
                shutil.copy2(s, d)


class InvalidValidator(Exception):
    pass


def get_or_guess_service_json_file(base_dir=None, default='service.json', insist=True):
    """ NB: only to be used from fabfiles! """
    if base_dir is None:
        frame = inspect.stack()[1]
        module = inspect.getmodule(frame[0])
        base_dir = os.path.dirname(module.__file__)
    service_json_file = os.environ.get(
        'YMIR_SERVICE_JSON',
        os.path.join(base_dir, default))
    if insist and not os.path.exists(service_json_file):
        raise SystemExit("service JSON does not exist: {0}".format(
            service_json_file))
    return service_json_file

guess_service_json = get_or_guess_service_json_file


def declare_validator(fxn):
    @wraps(fxn)
    def newf(*args, **kargs):
        result = fxn(*args, **kargs)
        try:
            errors, warnings, messages = result
        except ValueError:
            raise InvalidValidator(
                ("{0} should return a tuple of "
                 "errors/warnings/messages if it"
                 " is declared a validator!").format(
                    fxn.__name__))
        if not errors and not warnings and not messages:
            messages.append("no problems found")
        return result
    return newf
