""" ymir.checks

    This file describes 'check_types' which are available for
    use with integration tests or health-checking.

      | Check type  | Description
      |-------------|-----------------------------
      | http        | check a http, yield status code
      | http_200    | check for http 200. yield bool
      | json        | check that response is json.  yield bool
      | json_200    | check that response is json, code is 200. yield bool
"""

import requests

def _get_request(url, **kargs):
    return requests.get(url, timeout=2, verify=False, **kargs)

def http(url, assert_json=False, codes=[]):
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
    return msg

def json(url, **kargs):
    kargs.update(assert_json=True)
    return http(url, **kargs)

def http_200(url):
    return http(url, codes=[200])

def json_200(url):
    return json(url, codes=[200])
