""" ymir.checks
"""

import requests

def check_http(url):
    try:
        resp = requests.get(url, timeout=2, verify=False)
    except requests.exceptions.ConnectionError, e:
        if 'timed out' in str(e):
            msg = 'timed out'
        else:
            msg = str(e)
    else:
        msg = str(resp.status_code)
    return msg
