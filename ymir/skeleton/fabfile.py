#!/usr/bin/env python
"""
\x1b[31mFreeAlbumEngine Automation:\x1b[0m
  This is the \x1b[35mCache\x1b[0m Service
"""
# TODO: nix commands: flushdb, flushall
import os, sys
import urlparse

SERVICE_ROOT = os.path.dirname(__file__)
PROJECT_ROOT = os.path.dirname(SERVICE_ROOT)
sys.path.insert(0, PROJECT_ROOT)

import ymir
from automation import naxos

class _Redis(naxos.NaxosService):
    NAME = 'naxos-fae-cache'
    PUPPET   = ["puppet/cache.pp"]
    SERVICE_ROOT = SERVICE_ROOT

    def _status(self):
        """ add redis entries """
        result = super(_Redis, self)._status()
        if result:
            result.update(
                dict(redis='redis://{0}:{1}'.format(
                    result['ip'], naxos.RPORT)))
        return result

    def check_ip(self, ip, data):
        super(_Redis,self).check_ip(ip, data)
        redis = data['redis']
        tmp = urlparse.urlparse(redis)
        if self.is_port_open(tmp.hostname,tmp.port):
            redis_status = 'connected'
        else:
            redis_status = 'unknown'
        self.report(' .. ', redis, redis_status)

conn = ymir.util.get_conn()
_cache = _Redis(conn=conn)
ssh = _cache.ssh
show = _cache.show
status = _cache.status
create = _cache.create
reboot = _cache.reboot
setup = _cache.setup
provision = _cache.provision
check = _cache.check
