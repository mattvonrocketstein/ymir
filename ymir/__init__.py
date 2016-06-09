# -*- coding: utf-8 -*-
""" ymir:

    this is a module containing utility functions/classes for working
    with EC2. A common interface for typical devops commands is provided
    (create, setup, provision, etc) by leveraging a combination of fabric,
    boto, & puppet.

"""
from ymir import loom
from .api import load_service_from_json, _load_service_from_json

__all__ = [x.__name__ for x in [
    loom, load_service_from_json, _load_service_from_json]]
