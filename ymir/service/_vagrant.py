# -*- coding: utf-8 -*-
""" ymir.service._vagrant

    this module is prefixed with an underscore to avoid confusion with
    the module from python-vagrant.
"""
import copy
import vagrant as _vagrant
from ymir import util
from .base import AbstractService


class VagrantService(AbstractService):

    _vagrant = None
    FABRIC_COMMANDS = copy.copy(AbstractService.FABRIC_COMMANDS) + \
        ['up']

    def up(self):
        """ shortcut for vagrant up """
        self.vagrant.up()

    def _status(self):
        """ retrieves service status information.
            use this instead of self.status() if you want to quietly
            retrieve information for use without actually displaying it
        """
        if not self._status_computed:
            self.report("handshaking with Vagrant..")
        ip = None
        result = dict(
            instance=None, ip=ip,
            status='terminated?',
            # perhaps provide for compatability with EC2?
            # private_ip=None, tags=[],
        )
        status = self.vagrant and self.vagrant.status()
        if status:
            # vagrant.status() is a list with potentially many items,
            # depending on if the Vagrantfile supports multi-vm
            status = status.pop()
            if status.state not in ['poweroff', 'not_created']:
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

    def create(self, force=False):
        """ create new instance of this service ('force' defaults to False)"""
        self.report('creating vagrant instance', section=True)
        state = self._status()['status']
        assert not force, 'force=True not supported for vagrant yet'
        if state in ['not_created']:
            self.vagrant.up()
        else:
            self.report("already created!  status={0}".format(state))

    @property
    def vagrant(self):
        if not self._vagrant:
            self.report("caching vagrant handle..")
            self._vagrant = _vagrant.Vagrant(
                quiet_stdout=False,
                quiet_stderr=False,)

        return self._vagrant

    def _get_instance(self, strict=False):
        result = self.vagrant
        if strict and self._status()['status'] != 'running':
            err = "Could not acquire instance! Is the box started?"
            self.report(err)
            raise SystemExit(1)
        return result

    @property
    def _hostname_port(self):
        return self.vagrant.user_hostname_port().split('@')[-1]

    def ssh_ctx(self):
        """ """
        return util.ssh_ctx(
            self._hostname_port,
            user=self._username,
            pem=self._pem,)

    @property
    def _username(self):
        """ username data is accessible only as a property because
            it must overridden for i.e. vagrant-based services
        """
        return self.vagrant.user()

    @property
    def _pem(self):
        return self.vagrant.keyfile()

    def ssh(self):
        """ connect to this service with ssh """
        self.report('connecting with ssh')
        util.ssh(self._hostname_port,
                 username=self._username,
                 pem=self._pem)
