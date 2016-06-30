# -*- coding: utf-8 -*-
""" ymir.checks

    This file describes 'check_types' which are available for
    use with integration tests or health checks.

      | Check type    | Description
      |---------------|---------------------------------------------------------
      | http          | check a http, yield status code
      | http_200      | check for http 200. yield bool
      | http_301      | check for http 301. yield bool
      | json          | check that response is json.  yield bool
      | json_200      | check response is json, code is 200. yield bool
      | port_open     | check that port is open.  yield bool
      | file-exists   | check that file exists.  yield bool
      | file-contains | check that file exists.  yield bool
      | testinfra     | testinfra assertions.  yield exceptions
      |---------------|---------------------------------------------------------

   Every checker can optionally include it's own validation, which will be invoked
   during calls to `ymir validate`.  This validation is NOT run during `fab check`
   invocations.  Validators should simply return None if everything is fine or a string
   if there is an error.  Find the ".validate" assignments below for further example.
"""

import requests
from tempfile import NamedTemporaryFile

import testinfra as testinfra_mod
from fabric.colors import blue, yellow
from peak.util.imports import lazyModule

from ymir import util
from ymir import data as ydata
import yurl

backend_cache = {}
yapi = lazyModule('ymir.api')


class InvalidCheckType(RuntimeError):
    pass


class InvalidCheck(RuntimeError):
    pass


class Check(object):

    def __init__(self, name=None, check_type=None, url_t=None):
        self.name = name
        self.check_type = check_type
        self.url_t = url_t
        self.failed = None
        self.success = None

    def __repr__(self):  # pragma: nocover
        return "<Check: {0}>".format(self.name)
    __str__ = __repr__

    def run(self, service, quiet=False):
        import ymir.checks as modyool
        data = service.template_data()
        data.update(service.facts)
        self.url = yapi.str_reflect(self.url_t, ctx=data)

        try:
            checker = getattr(modyool, self.check_type.replace('-', '_'))
        except AttributeError:
            err = 'Cannot find checker "{0}"'.format(
                self.check_type, self.url)
            raise InvalidCheckType(err)

        _url, success, message = checker(service, self.url)
        self.success = success
        self.failed = not self.success
        if not quiet:
            print '  {4} [{0}] {1}{2} {3} '.format(
                yellow(self.name),
                blue(self.check_type + '://'),
                self.url,
                message if message else '',
                ydata.FAIL + 'fail' if not success else ydata.SUCCESS + 'ok'
            )
        return self


def _get_request(url, **kargs):  # pragma: nocover
    return requests.get(
        url, timeout=10, verify=False,
        allow_redirects=False, **kargs)


def port_open(service, port):
    """ """
    ip = service._status()['ip']
    url = 'is_open://{0}:{1}'.format(ip, port)
    success = util.is_port_open(ip, port)
    return url, success, ''


def _port_open_validate(port):
    if not isinstance(port, int):
        try:
            int(port)
        except ValueError:
            err = ("the `port_open` check requires a single argument "
                   "(the port number) which can be converted to an integer. "
                   "  Got {0} instead").format(port)
            return err
port_open.validate = _port_open_validate


def http(service, url, assert_json=False, codes=[]):  # NOQA
    """ an ugly function but this is the single core implementation
        that drives the other checks (like http_200, http_301, etc).
        without the `NOQA` directive above git-hooks will not allow us
        to commit any changes.
    """
    success = False
    # might get handed ints or strings, need to normalize
    codes = map(unicode, codes)
    try:
        resp = _get_request(url)
    except requests.exceptions.ConnectionError, e:
        success = False
        if 'timed out' in str(e):
            message = 'requests.exceptions.ConnectionError (timed out)'
        else:
            message = str(e)
    except requests.exceptions.ReadTimeout, e:
        success = False
        if 'timed out' in str(e):
            message = 'requests.exceptions.ReadTimeout'
        else:
            message = str(e)
    else:
        if codes:
            success = unicode(resp.status_code) in codes
            message = 'code={0}'.format(resp.status_code) \
                      if success else 'bad code: {0}'.format(resp.status_code)
            if not success:
                return url, success, message
        else:
            success = True
            message = str(resp.status_code)
        if assert_json:
            try:
                resp.json()
            except:
                success = False
                message = 'cannot convert response to JSON'
            else:
                success = True
    return url, success, message


def json(service, url, **kargs):
    """ """
    kargs.update(assert_json=True)
    return http(service, url, **kargs)


def http_200(service, url):
    return http(service, url, codes=[200])


def http_301(service, url):
    return http(service, url, codes=[301])


def http_401(service, url):
    return http(service, url, codes=[401])


def http_403(service, url):
    """ """
    return http(service, url, codes=[403])


def json_200(service, url):
    """ """
    return json(service, url, codes=[200])


def _url_validator(instruction):
    try:
        yurl.URL(instruction).validate()
    except Exception as exc:
        return str(exc)

for _fxn in [json, json_200, http_200, http_301, http_401, http_403]:
    _fxn.validate = _url_validator


def file_exists(service, instruction):
    """ a checker for whether a given file exists
        ex: file-exists://remote_filename
    """
    return testinfra(
        service,
        "File('{0}').exists".format(instruction),
        _type='file_exists')


def _file_exists_validator(instruction):
    base_err = "check `file-exists` should "
    if not instruction.startswith('/'):
        err = "have an absolute path as it's instruction'"
        return base_err + err
file_exists.validate = _file_exists_validator


def socket_listening(service, instruction):
    """ a checker for whether a given socket is listening.
        this is executed on the remote side, and so can
        be very useful
        for testing firewalled AWS stuff or vagrant
        w/o port-forwarding

        see: http://testinfra.readthedocs.io/en/latest/modules.html#socket
    """
    new_instruction = "Socket('{0}').is_listening".format(instruction)
    return testinfra(service, new_instruction, _type='socket_listening')


def _socket_listening_validator(instruction):
    pass


def file_contains(service, instruction):
    """ a checker for whether a given file contains a given string.
        ex: file-contains://remote_filename,some_string
    """
    parts = instruction.split(",")
    fname, string = parts
    new_instruction = "File('{0}').contains('{1}')".format(fname, string)
    return testinfra(service, new_instruction, _type='file_contains')


def _file_contains_validator(instruction):
    parts = instruction.split(",")
    if len(parts) != 2:
        err = "Expected formatting: file_contains://filename,string"
        return err
    fname, string = parts
    if '"' in string or "'" in string:
        err = "please, dont use quotes in arguments for file-contains:// checks"
        return err

file_contains.validate = _file_contains_validator


def testinfra(service, instruction, _type="testinfra"):
    """ a checker for raw testinfra assertions
        ex: testinfra://File('/etc/passwd').exists
    """
    try:
        exec('assert ' + instruction, _testinfra_namespace(service))
    except Exception as exc:
        success = False
        message = str(exc)
    else:
        success = True
        message = ''
    return instruction, success, message


def _testinfra_validator(instruction):
    """ """
    try:
        compile(instruction, '_testinfra_validator', 'exec')
    except SyntaxError as exc:
        return str(exc)
testinfra.validate = _testinfra_validator


def _testinfra_backend(service):
    """ this call is very expensive in terms of
        time and I/O, so cache carefully
    """
    cache_key = id(service)
    if cache_key in backend_cache:
        return backend_cache[cache_key]
    config = service._ssh_config_string
    with NamedTemporaryFile() as tmpf:
        tmpf.file.write(config)
        tmpf.file.seek(0)
        backend = testinfra_mod.get_backend(
            "paramiko://default", ssh_config=tmpf.name, sudo=True)
        # this call is necessary to unlazy-ify the testinfra
        # backend before we leave the context manager
        backend.get_module('File')
        backend_cache[cache_key] = backend
        return backend


def _testinfra_namespace(service):
    """ testinfra primitives like {File, Package, Service} etc are defined differently
        for each backend, so they cannot be imported directly.  need to create a
        namespace containing all of these primitives, so one has to use inspection
        to avoid listing them out explicitly.
    """
    cache_key = -id(service)
    if cache_key in backend_cache:
        return backend_cache[cache_key]
    backend = _testinfra_backend(service)
    namespace = [
        x for x in dir(testinfra_mod.modules)
        if '_' not in x and x[0].upper() == x[0]]
    namespace = dict(
        [[name, backend.get_module(name)]
         for name in namespace])
    backend_cache[cache_key] = namespace
    return namespace
