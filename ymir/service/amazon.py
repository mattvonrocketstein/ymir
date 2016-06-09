# -*- coding: utf-8 -*-
""" ymir.service.amazon
"""

from ymir import util
from ymir.service.base import AbstractService


class AmazonService(AbstractService):
    """ """

    def __init__(self, conn=None, **kargs):
        """"""
        super(AmazonService, self).__init__(**kargs)
        self.conn = conn or util.get_conn()

    def setup_ip(self, ip):
        """ """
        self.sync_tags()
        self.sync_buckets()
        self.sync_eips()
        super(AmazonService, self).setup_ip(ip)
