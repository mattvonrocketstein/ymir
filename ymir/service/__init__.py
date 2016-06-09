# -*- coding: utf-8 -*-
""" ymir.service
"""
from .base import AbstractService
from ._vagrant import VagrantService
from .amazon import AmazonService

__all__ = [
    x.__name__ for x in
    [AbstractService, VagrantService, AmazonService] ]
