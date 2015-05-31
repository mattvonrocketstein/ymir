""" ymir.jenkins

    Several quick hacks for controlling jenkins CI server.  Doesn't really
    belong in ymir except insofar as both topics are devops.. if this file
    gets big enough then this might get it's own repo.

    Unfortunately python-jenkins is not very close to feature complete.
    I'd just commit these upstream, but despite adoption the library code
    is not that nice to work with.
"""
from __future__ import print_function
import urlparse
import logging
logger = logging.getLogger(__name__)

import requests
try:
    from jenkins import Jenkins as _Jenkins
except ImportError:
    err = ("Cannot import 'jenkins'.  Try using pip "
           "to install python-jenkins first")
    raise SystemExit(err)

class RequestsMixin(object):
    def _request(self, url='', **kargs):
        method = kargs.pop('method', 'get')
        kargs['verify'] = False
        if url.startswith('/'):
            url = url[1:]
        logger.debug('_request {0} with initial url: {1}'.format(
            method, url))
        url = self.base_url + url
        logger.debug('_request with transformed url: '+url)
        method = getattr(requests, method)
        #logger.debug('method {0} '.format(method))
        resp = method(url, **kargs)
        self.last_resp = resp
        return resp

    def _get(self, url='', **kargs):
        kargs['method'] = 'get'
        return self._request(url=url, **kargs)

    def _post(self, url='', **kargs):
        kargs['method'] = 'post'
        return self._request(url=url, **kargs)


class Jenkins(_Jenkins, RequestsMixin):

    STATUS_READY = 'ready'
    STATUS_REBOOT = 'rebooting'
    STATUS_UNKNOWN = 'unknown'

    def __init__(self, base_url, user, _pass):
        """ base_url should be fully specified,
            something like `http://user:api_key@host:port`
        """
        tmp = urlparse.urlparse(base_url)
        self.base_url = '{0}://{3}{4}'.format(
            tmp.scheme, user, _pass, tmp.netloc, tmp.path)
        #raise Exception,self.base_url
        if not self.base_url.endswith('/'):
            self.base_url += '/'
        self.last_resp = None
        super(Jenkins, self).__init__(base_url, user, _pass)

    def jobs(self):
        """ python-jenkins version of get_jobs is inconvenient """
        job_list = self.get_jobs()
        jobs = [[j['name'], j] for j in job_list]
        return dict(jobs)

    def job_xml(self, name):
        return self.get_job_config(name)

    def restart(self):
        # NB: unlike other methods, the value of resp.status_code
        # here will always be 503, even when everything is normal
        resp = self._post('/safeRestart')
        return resp

    def status(self):
        """ answers whether jenkins instance is ready """
        resp = self._get()
        rebooting = "Please wait while Jenkins is getting ready to work"
        if resp.status_code==200:
            return self.STATUS_READY
        elif rebooting in resp.content:
            return self.STATUS_REBOOT
        else:
            return self.STATUS_UNKNOWN

    def install_plugin(self, plugin):
        if '@' not in plugin:
            raise ValueError(
                ('plugin must include version'
                 ' info, got: "{0}"').format(plugin))
        payload = """<jenkins><install plugin="{0}" /></jenkins>"""
        payload = payload.format(plugin)
        resp = self._post(
            '/pluginManager/installNecessaryPlugins',
            data=payload, headers={'Content-Type': 'text/xml'})
        return resp
