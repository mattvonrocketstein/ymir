# -*- coding: utf-8 -*-
""" ymir.mixins
"""

from .packages import PackageMixin
from ._ansible import AnsibleMixin
from ._fabric import FabricMixin
from .puppet import PuppetMixin
from .rsync import RsyncMixin

__all__ = [
    tmp.__name__ for tmp in
    [PackageMixin, AnsibleMixin,
     PuppetMixin, FabricMixin,
     RsyncMixin,
     ]]
