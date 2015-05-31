""" ymir.beanstalk
"""
import logging

from boto.s3.connection import Location
from fabric.api import lcd, local, prefix, hide
from goulash.cache import cached
from ymir.service import AbstractService

logging.captureWarnings(True)

class ElasticBeanstalkService(AbstractService):
    """ This is a wrapper so that elasticbeanstalk-managed stuff
        can look like the usual service definition.  The 'eb'
        commandline tool mostly just does it's own thing, but
        we want to keep the familiar create/setup/provision
        interface, regardless.  This implementation is only
        half complete because I haven't worked out how to do
        fabric-based authentication for the eb-instance yet.
    """
    S3_LOCATION = Location.DEFAULT
    ENV_NAME = None
    HEALTH_CHECKS = {'http://{host}' : 'http_200',
                     'http://{ip}'   : 'http_200' }

    def __init__(self, *args, **kargs):
        err = "ElasticBeanstalkService.ENV_NAME must be set"
        assert self.ENV_NAME != None, err
        super(ElasticBeanstalkService, self).__init__(*args, **kargs)

    @cached('ymir_status', timeout=10)
    def _status(self):
        """ retrieves service status information """
        basics = super(ElasticBeanstalkService, self)._status()
        basics.pop('supervisor', None)
        out = {}
        out.update(**basics)
        with hide('output', 'running'):
            with self._eb_ctx():
                result = local('eb status 2>&1', capture=True)
        result = result.split('\n')
        header = 'Environment details for:'
        assert result[0].strip().startswith(header),'weird output: '+str(result)
        #eb_env = result[0][len(header):].strip()
        result = [x.split(':') for x in result[1:]]
        result = [[ 'eb_' + x[0].strip().lower().replace(' ', '_'),
                   ':'.join(x[1:]).strip()] for x in result]
        result = dict(result)
        out.update(**result)
        return out

    def _report_name(self):
        return '{0} [{1}]'.format(
            super(ElasticBeanstalkService,self)._report_name(),
             self.ENV_NAME)

    def _eb_ctx(self):
        return prefix('eb use {0}'.format(self.NAME))

    def setup(self):
        """ add any s3 buckets this service requires, etc """
        self.report("ensuring buckets are created: " + str(self.S3_BUCKETS))
        self._setup_buckets()

    def provision(self):
        """ same as 'eb deploy' """
        with lcd(self.SERVICE_ROOT):
            with self._eb_ctx():
                local('eb deploy')

    def ssh(self):
        """ same as 'eb ssh' """
        with lcd(self.SERVICE_ROOT):
            with self._eb_ctx():
                local('eb ssh')

    def create(self, force=False):
        """ not implemented for beanstalk-based services """

    def _validate_keypairs(self):
        print "EB service does not validate keypairs"
