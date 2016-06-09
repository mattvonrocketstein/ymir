# -*- coding: utf-8 -*-
""" ymir.service.amazon
"""

from ymir.service.base import AbstractService

class AmazonService(AbstractService):
    """ """
    def setup_ip(self, ip):
        """ """
        self.sync_tags()
        self.sync_buckets()
        self.sync_eips()
        super(AmazonService, self).setup_ip(ip)
