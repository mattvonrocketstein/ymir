# -*- coding: utf-8 -*-
""" ymir.mixins._fabric
"""
import time
import webbrowser

from fabric import api
from peak.util.imports import lazyModule

from ymir import util
from ymir import checks as ychecks
from ymir import data as ydata

yapi = lazyModule('ymir.api')


class FabricMixin(object):

    @util.declare_operation
    def status(self):
        """ shows IP, running status, tags, etc for this service """
        self.report('checking status', section=True)
        result = self._status()
        for k, v in result.items():
            self.report('  {0}: {1}'.format(k, v))
        return result

    @util.declare_operation
    @util.require_running_instance
    def tail(self, filename):
        """ tail a file on the service host """
        with self.ssh_ctx():
            api.run('tail -f ' + filename)

    @util.declare_operation
    @util.require_running_instance
    def put(self, src, dest="~", *args, **kargs):
        """ thin wrapper around fabric's scp command
            just to use this service ssh context
        """
        with self.ssh_ctx():
            owner = kargs.pop('owner', None)
            if owner:
                kargs['use_sudo'] = True
            with self.ssh_ctx():
                result = api.put(src, dest, *args, **kargs)
            if result.succeeded and owner:
                for remote_fname in result:
                    api.sudo('chown {0}:{0} "{1}"'.format(
                        owner, remote_fname))
            return result.succeeded

    @util.declare_operation
    @util.require_running_instance
    def get(self, fname, local_path='.'):
        """ thin wrapper around fabric's scp command
            just to use this service ssh context
        """
        with self.ssh_ctx():
            return api.get(fname, local_path=local_path, use_sudo=True)

    @util.declare_operation
    def wait(self, delay=30):
        """ useful for inserting a delay between fabric commands """
        try:
            delay = int(delay)
        except ValueError:
            raise SystemExit("wait command requires integer delay")
        self.report("waiting for {0} seconds".format(delay))
        time.sleep(delay)

    @util.declare_operation
    def ssh(self):
        """ connect to this service with ssh """
        self.report('connecting with ssh')
        util.ssh(
            self._host,
            username=self._username,
            pem=self._pem,
            port=self._port,)

    @util.declare_operation
    @util.require_running_instance
    def show(self):
        """ open health-check webpages for this service in a browser """
        def _show_url(url):
            self.report("showing: {0}".format(url))
            webbrowser.open(url)
        self.report('showing webpages')
        health_checks = self.template_data()['health_checks']
        for check_name in health_checks:
            check, url = health_checks[check_name]
            _show_url(yapi.str_reflect(url, self.template_data()))

    @util.declare_operation
    @util.require_running_instance
    def check(self, name=None, failfast=False):
        """ reports health for this service """
        # TODO: include relevant sections of status results
        # for x in 'status eb_health eb_status'.split():
        #    if x in data:
        #        out['aws://'+x] = ['read', data[x]]
        def fail():
            raise SystemExit(1)
        service_health_checks = self.template_data()['health_checks']
        self.report('running health checks ({0} total)'.format(
            len(service_health_checks)))
        names = [name] if name is not None else service_health_checks.keys()
        success = True
        for check_name, (_type, url_t) in service_health_checks.items():
            if check_name in names:
                check_obj = ychecks.Check(
                    url_t=url_t, check_type=_type, name=check_name)
                result = check_obj.run(self)
                success = success and result.success
                if failfast and not success:
                    fail()
            else:
                self.report(ydata.WARNING + "skipped: " + check_name)
        if not success:
            fail()

    @util.declare_operation
    def integration_test(self):
        """ runs integration tests for this service """
        self.report('running integration tests')
        data = self._status()
        if data['status'] == 'running':
            return self._test_data(data)
        else:
            self.report('no instance is running for this'
                        ' service, start (or create) it first')

    @util.declare_operation
    @util.require_running_instance
    def reboot(self):
        """ TODO: blocking until reboot is complete? """
        self.report('rebooting service')
        with self.ssh_ctx():
            api.run('sudo reboot')
