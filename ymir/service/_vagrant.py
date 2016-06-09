"""
"""
import copy
import vagrant as _vagrant
from ymir import util
from .base import AbstractService


class VagrantService(AbstractService):

    _vagrant = None
    FABRIC_COMMANDS = copy.copy(AbstractService.FABRIC_COMMANDS)
    FABRIC_COMMANDS.remove('mosh')

    def _status(self):
        """ retrieves service status information.
            use this instead of self.status() if you want to quietly
            retrieve information for use without actually displaying it
        """
        if not self._status_computed:
            self.report("handshaking with Vagrant..")
        ip=None
        result = dict(
            instance=None, ip=ip,
            status='terminated?',
            # perhaps provide for compatability with EC2?
            # private_ip=None, tags=[],
        )
        status = self.vagrant and self.vagrant.status()
        if status:
            # a list with potentially many items, depending
            # on if the Vagrantfile supports multi-vm
            status = status.pop()
            if status.state not in ['poweroff']:
                ip = self.vagrant.hostname()
            result.update(
                dict(
                    instance=str(self.vagrant),#instance,
                    #tags=instance.tags,
                    status=status.state,
                    provider=status.provider,
                    name=status.name,
                    ip=ip,
                ))
        self._status_computed = result
        return result


    @property
    def vagrant(self):
        if not self._vagrant:
            self.report("caching vagrant handle..")
            self._vagrant = _vagrant.Vagrant()
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
