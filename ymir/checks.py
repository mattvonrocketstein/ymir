# -*- coding: utf-8 -*-
""" ymir.checks

    This file describes 'check_types' which are available for
    use with integration tests or health checks.

      | Check type  | Description
      |-------------|-----------------------------
      | http        | check a http, yield status code
      | http_200    | check for http 200. yield bool
      | http_301    | check for http 301. yield bool
      | json        | check that response is json.  yield bool
      | json_200    | check that response is json, code is 200. yield bool
      | port_open   | check that port is open.  yield bool

   Every checker can optionally include it's own validation.  This validation
   is NOT run during `ymir check` invocations but will be run during the
   `ymir validate` invocation.
"""

import requests
from ymir import util
from fabric.colors import blue, yellow, red, cyan


class Check(object):

    def __init__(self, name=None, check_type=None, url_t=None):
        self.name = name
        self.check_type = check_type
        self.url_t = url_t

    def __repr__(self):
        return "<Check: {0}>".format(self.name)
    __str__ = __repr__

    def run(self, service):
        import ymir.checks as modyool
        data = service._service_data
        self.url = self.url_t.format(**data)
        try:
            checker = getattr(modyool, self.check_type)
        except AttributeError:
            err = 'Cannot find checker "{0}"'.format(
                self.check_type, self.url)
            raise SystemExit(err)
        else:
            _url, success, message = checker(service, self.url)
        print '  {4} [{0}] [?{1}] -- {2} {3} '.format(
            yellow(self.name),
            blue(self.check_type),
            self.url,
            message if message else '',
            red('✖ fail') if not success else cyan('✓ ok')
        )
        return self


def _get_request(url, **kargs):
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


def http(service, url, assert_json=False, codes=[]):
    success = False
    # might get handed ints or strings, need to normalize
    codes = map(unicode, codes)
    try:
        resp = _get_request(url)
    except requests.exceptions.ConnectionError, e:
        if 'timed out' in str(e):
            message = 'requests.exceptions.ConnectionError (timed out)'
        else:
            message = str(e)
    except requests.exceptions.ReadTimeout, e:
        if 'timed out' in str(e):
            message = 'requests.exceptions.ReadTimeout'
        else:
            message = str(e)
    else:
        if codes:
            success = unicode(resp.status_code) in codes
            message = 'code={0}'.format(resp.status_code) \
                      if success else 'bad code: {0}'.format(resp.status_code)
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
    kargs.update(assert_json=True)
    return http(service, url, **kargs)


def http_200(service, url):
    return http(service, url, codes=[200])


def http_301(service, url):
    return http(service, url, codes=[301])


def http_401(service, url):
    return http(service, url, codes=[401])


def http_403(service, url):
    return http(service, url, codes=[403])


def json_200(service, url):
    return json(service, url, codes=[200])
