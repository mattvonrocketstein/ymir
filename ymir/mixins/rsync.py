# -*- coding: utf-8 -*-

import os

from ymir import data as ydata
from ymir.data import BadProvisionInstruction

from fabric import api
from fabric.contrib.project import rsync_project


class RsyncMixin(object):

    def _provision_rsync(self, instruction):
        """ """
        args = instruction.split(',')
        if len(args) > 2:
            raise BadProvisionInstruction(
                ("'{0}' should be formatted as "
                 "'local_path,remote_path' or 'local_path'").format(
                    instruction))
        elif len(args) == 1:
            src, dest = args[0], "~"
        else:
            src, dest = args
        # TODO: move this to _rsync.
        assert os.path.exists(src)
        if os.path.isdir(src):
            tmp = [x for x in os.path.split(src) if x]
            tmp = tmp[-1]
            src = os.path.join(src, '*')
            if not dest.endswith(tmp):
                dest = os.path.join(dest, tmp)
        return self._rsync(src=src, dest=dest)

    def _rsync(self, src=None, dest=None, delete=True, **kargs):
        """ """
        assert src and dest
        self._require_rsync()
        self.report("rsync {0} -> {1}".format(
            src, dest))
        with self.ssh_ctx():
            result = rsync_project(
                dest,
                local_dir=src,
                delete=True,
                ssh_opts=ydata.RSYNC_SSH_OPTS,
                exclude=ydata.RSYNC_EXCLUDES,)
        self.report(ydata.SUCCESS + "sync finished")
        return result

    def _has_rsync(self):
        """ answers whether the remote side has rsync """
        with api.quiet():
            return api.run('rsync --version').succeeded

    def _require_rsync(self):
        """ """
        has_rsync = self._has_rsync()
        if not has_rsync:
            self.report(
                ydata.FAIL + "remote side is missing rsync.  installing it")
            self._update_system_packages()
            with api.settings(warn_only=True):
                success = self._provision_apt("rsync")
                if not success:
                    self._provision_yum("rsync")
        else:
            self.report(ydata.SUCCESS + "remote side already has rsync")
