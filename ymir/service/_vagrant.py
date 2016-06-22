# -*- coding: utf-8 -*-
""" ymir.service._vagrant

    NB: this module is prefixed with an underscore to avoid
        confusion with the module from python-vagrant.
"""
import subprocess

from fabric import api
import vagrant as _vagrant

from ymir import util
from .base import AbstractService
from ymir import data as ydata
STATUS_NC = 'not_created'


class VagrantNotReady(object):

    def not_ready(self):
        return "not_ready"

    def status(self):
        return None  # [type('fakestatus',(object,),dict())]
    user = keyfile = hostname = port = not_ready


class VagrantService(AbstractService):

    _vagrant = None

    @property
    def _username(self):
        """ username data is accessible only as a property because
            it must overridden for i.e. vagrant-based services
        """
        return self.vagrant.user()

    @property
    def _pem(self):
        """ value available JIT """
        return util.unexpand(self.vagrant.keyfile())

    @property
    def _host(self):
        """ value available JIT: """
        return self.vagrant.hostname()

    @property
    def _port(self):
        """ value available JIT: """
        return self.vagrant.port()

    @property
    def vagrant(self):
        """ """
        if not self._vagrant:
            self._cache_vagrant_handle()
        return self._vagrant

    def _cache_vagrant_handle(self):
        try:
            tmp = _vagrant.Vagrant(
                quiet_stdout=self._debug_mode,
                quiet_stderr=self._debug_mode,)
            tmp.user()  # unlazify the handle
        except (subprocess.CalledProcessError,):
            self.report(
                ydata.WARN + "vagrant did not respond as expected!")
            self._vagrant = VagrantNotReady()
        else:
            self._vagrant = tmp

    @util.declare_operation
    def up(self):
        """ shortcut for `vagrant up` """
        self.report("invoking `vagrant up`")
        with api.lcd(self._ymir_service_root):
            with api.shell_env(YMIR_SERVICE_JSON=self._ymir_service_json_file):
                api.local('vagrant up')
        self._cache_vagrant_handle()

    def _status(self):
        """ retrieves service status information.
            use this instead of self.status() if you want to quietly
            retrieve information for use without actually displaying it
        """
        if not self._status_computed:
            self.report("handshaking with Vagrant..")
        else:
            return self._status_computed
        ip = None
        result = dict(
            instance=None, ip=ip,
            status='not_created',
            # perhaps provide for compatability with EC2?
            # private_ip=None, tags=[],
        )
        status = self.vagrant and self.vagrant.status()
        if status:
            # vagrant.status() is a list with potentially many items,
            # depending on if the Vagrantfile supports multi-vm
            status = status.pop()
            if status.state not in ['poweroff', STATUS_NC]:
                # DONT use self._host here, that's cyclic
                ip = self.vagrant.hostname()
            result.update(
                dict(
                    instance=str(self.vagrant),
                    status=status.state,
                    provider=status.provider,
                    name=status.name,
                    ip=ip,
                ))
        self._status_computed = result
        return result

    @util.declare_operation
    def create(self, force=False):
        """ create new instance of this service ('force' defaults to False) """
        self.report('creating vagrant instance', section=True)
        state = self._status()['status']
        assert not force, 'force=True not supported for vagrant yet'
        if state in ['not_created']:
            self.up()
        else:
            self.report(
                ydata.FAIL + "already created!  status={0}".format(state))
            if state == 'poweroff':
                self.report("use `fab up` to start the virtualmachine")
            raise SystemExit(1)

    def _get_instance(self, strict=False):
        """ """
        result = self.vagrant
        if strict and self._status()['status'] != 'running':
            err = "ERROR: could not acquire vagrant instance! Is the box started?"
            self.report(err)
            raise SystemExit(1)
        return result

    @util.declare_operation
    @util.require_running_instance
    def terminate(self, force=False):
        """ terminate this service (delete from virtualbox) """
        instance = self._instance
        self.report("{0} slated for termination.".format(instance))
        if force:
            return self.vagrant.destroy()
        else:
            msg = ("This will terminate the instance {0} ({1}) and can "
                   "involve data loss.  Are you sure? [y/n] ")
            answer = None
            name = self.template_data()['name']
            while answer not in ['y', 'n']:
                answer = raw_input(msg.format(instance, name))
            if answer == 'y':
                self.terminate(force=True)

    @util.declare_operation
    def shell(self):
        """ """
        return util.shell(
            Service=self, service=self)
