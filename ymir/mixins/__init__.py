# -*- coding: utf-8 -*-
""" ymir.service.mixins
"""

from .packages import PackageMixin
from ._ansible import AnsibleMixin
__all__ = [tmp.__name__ for tmp in
           [PackageMixin, AnsibleMixin,
            ]]
