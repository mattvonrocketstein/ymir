""" ymir.checks

    This file describes 'check_types' which are available for
    use with integration tests or health checks.

      | Check type  | Description
      |-------------|-----------------------------
      | http        | check a http, yield status code
      | http_200    | check for http 200. yield bool
      | json        | check that response is json.  yield bool
      | json_200    | check that response is json, code is 200. yield bool
      | port_open   | check that port is open.  yield bool

   Every checker can optionally include it's own validation.  This validation
   is NOT run during `ymir check` invocations but will be run during the
   `ymir validate` invocation.
"""

import requests

def _get_request(url, **kargs):
    return requests.get(url, timeout=10, verify=False, **kargs)

def port_open(service, port):
    ip  = service._status()['ip']
    url = 'is_open://{0}:{1}'.format(ip, port)
    return url, str(service.is_port_open(ip, port))
def _port_open_validate(port):
    if not isinstance(port, int):
        try: int(port)
        except ValueError:
            err = ("the `port_open` check requires a single argument "
                   "(the port number) which can be converted to an integer. "
                   "  Got {0} instead").format(port)
            return err
port_open.validate = _port_open_validate

def supervisor(service, url):
    url = 'http://{0}:{1}@{2}:{3}'.format(
        service.SUPERVISOR_USER, service.SUPERVISOR_PASS,
        service._host(), '9001')
    return http_200(service, url)

def http(service, url, assert_json=False, codes=[]):
    try:
        resp = _get_request(url)
    except requests.exceptions.ConnectionError, e:
        if 'timed out' in str(e):
            msg = 'requests.exceptions.ConnectionError (timed out)'
        else:
            msg = str(e)
    except requests.exceptions.ReadTimeout, e:
        if 'timed out' in str(e):
            msg = 'requests.exceptions.ReadTimeout'
        else:
            msg = str(e)
    else:
        if codes:
            msg = str(resp.status_code in codes)
        else:
            msg = str(resp.status_code)
        if assert_json:
            resp.json()
            msg = 'ok'
    return url, msg

def json(service, url, **kargs):
    kargs.update(assert_json=True)
    return http(service, url, **kargs)

def http_200(service, url):
    return http(service, url, codes=[200])

def http_401(service, url):
    return http(service, url, codes=[401])

def json_200(service, url):
    return json(service, url, codes=[200])
