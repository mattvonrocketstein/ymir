""" ymir.beanstalk
"""
from fabric.api import lcd, local, prefix

import logging
logging.captureWarnings(True)

from boto.s3.connection import Location
from .service import AbstractService

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
    #from boto.s3.key import Key

    def _setup_buckets(self):
        import boto
        conn = boto.connect_s3()
        tmp = {}
        for name in self.S3_BUCKETS:
            self.report("setting up s3 bucket: {0}".format(name))
            tmp[name] = conn.create_bucket(name, location=self.S3_LOCATION)
        return tmp

    def _eb_ctx(self):
        return prefix('eb use {0}'.format(self.NAME))

    def setup(self):
        """ same as 'eb deploy' """
        with lcd(self.SERVICE_ROOT):
            with self._eb_ctx():
                local('eb deploy')

    def provision(self):
        """ provision this service """
        self.report("ensuring buckets are created: "+str(self.S3_BUCKETS))
        self._setup_buckets()

    def check(self):
        """ not implemented yet """
        with lcd(self.SERVICE_ROOT):
            with self._eb_ctx():
                local('eb status')

    def ssh(self):
        """ same as 'eb ssh' """
        with lcd(self.SERVICE_ROOT):
            with self._eb_ctx():
                local('eb ssh')
