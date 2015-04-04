""" ymir.checks

    This file describes 'check_types' which are available for
    use with integration tests or health-checking.

      | Check type  | Description
      |-------------|-----------------------------
      | http        | check a http, yield status code
      | http_200    | check for http 200. yield bool
      | json        | check that response is json.  yield bool
      | json_200    | check that response is json, code is 200. yield bool
      | port_open   | check that port is open.  yield bool
"""

import requests

def _get_request(url, **kargs):
    return requests.get(url, timeout=2, verify=False, **kargs)

def port_open(service, port):
    ip = service._status()['ip']
    url= 'is_open://{0}:{1}'.format(ip, port)
    return url, str(service.is_port_open(ip, port))

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
            msg = 'timed out'
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
