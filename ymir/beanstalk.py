# -*- coding: utf-8 -*-
""" ymir.beanstalk
"""
import logging

from fabric import api
from fabric.api import lcd, local, prefix, hide
from peak.util.imports import lazyModule

from ymir.caching import cached
from ymir.service import AbstractService


logging.captureWarnings(True)

ebssh = lazyModule('ebssh')
ebssh_decorators = lazyModule('ebssh.decorators')
ebssh_fabric = lazyModule('ebssh.fabric_commands')


class ElasticBeanstalkService(AbstractService):

    """ This is a wrapper so that elasticbeanstalk-managed stuff
        can look like the usual service definition.  The 'eb'
        commandline tool mostly just does it's own thing, but
        we want to keep the familiar create/setup/provision
        interface, regardless.  This implementation is only
        half complete because I haven't worked out how to do
        fabric-based authentication for the eb-instance yet.
    """

    def put(self, *args, **kargs):
        """ """
        return ebssh_fabric.put(*args, **kargs)

    def get(self, *args, **kargs):
        """ """
        return ebssh_fabric.get(*args, **kargs)

    def run(self, *args, **kargs):
        return ebssh_fabric.run(*args, **kargs)

    def _host(self, data=None):
        """ NB: overridden from base because only
                beanstalk has eb_cname attribute
        """
        data = data or self._status()
        return data.get('eb_cname', data.get('ip'))

    @property
    def ebssh(self):
        """

        from ebssh.fabric_commands import run_sysenv as run
        from ebssh.fabric_commands import put, sudo, get
        """
        service_data = self.template_data()
        region = service_data['aws_region']
        try:
            ebssh.config.update(
                EB_APP=service_data['app_name'],
                EB_ENV=service_data['env_name'],
                EB_USER=service_data['username'],
                EB_KEY=service_data['pem'],
                AWS_DEFAULT_REGION=region,
                AWS_ACCESS_KEY=service_data['aws_access_key'],
                AWS_SECRET_KEY=service_data['aws_secret_key'],)
        except ImportError:
            self.report(
                "the ebssh library is required to dynamically "
                "open/close beanstalk ssh firewalls.  see "
                "https://github.com/mattvonrocketstein/ebssh")
            raise
        return ebssh

    def ssh_ctx(self):
        """ """
        raise Exception(
            "ssh_ctx is not used with beanstalk-backed services yet")

    def __init__(self, *args, **kargs):
        err = "ElasticBeanstalkService.ENV_NAME must be set"
        assert self.ENV_NAME is not None, err
        super(ElasticBeanstalkService, self).__init__(*args, **kargs)

    @cached('ymir_status', timeout=10)
    def _status(self):
        """ retrieves service status information
            NB: this should be cached because it relies on
            `eb status`, which is slow
        """
        basics = super(ElasticBeanstalkService, self)._status()
        basics.pop('supervisor', None)
        out = {}
        out.update(**basics)
        with hide('output', 'running'):
            with self._eb_ctx():
                with api.settings(warn_only=True):
                    result = local('eb status 2>&1', capture=True)
                    if result.failed:
                        if 'You appear to have no credentials' in str(result):
                            self.report(
                                "Error running `eb status` "
                                "(this can happen if your system "
                                "clock is incorrect)")
                        raise SystemExit(str(result))

        result = result.split('\n')
        header = 'Environment details for:'
        err = 'weird output: ' + str(result)
        assert result[0].strip().startswith(
            header), err
        result = [x.split(':') for x in result[1:]]
        result = [['eb_' + x[0].strip().lower().replace(' ', '_'),
                   ':'.join(x[1:]).strip()] for x in result]
        result = dict(result)
        out.update(**result)
        return out

    def _report_name(self):
        """ """
        return '{0} [{1}]'.format(
            super(ElasticBeanstalkService, self)._report_name(),
            self.template_data()['env_name'])

    def _eb_ctx(self):
        return prefix('eb use {0}'.format(self.NAME))

    def setup(self):
        """ add any s3 buckets this service requires, etc """
        self.report("ensuring buckets are created: " + str(self.S3_BUCKETS))
        self._setup_buckets()

    def provision(self):
        """ same as 'eb deploy' """
        with lcd(self._ymir_service_root):
            with self._eb_ctx():
                local('eb deploy')

    def ssh(self):
        """ same as 'eb ssh' """
        with lcd(self._ymir_service_root):
            with self._eb_ctx():
                local('eb ssh')

    def create(self, force=False):
        """ not implemented for beanstalk-based services """
