# -*- coding: utf-8 -*-
"""
"""
import os


def unexpand(path):
    """ the opposite of os.path.expanduser """
    home = os.environ.get('HOME')
    if home:
        path = path.replace(home, '~')
    return path
