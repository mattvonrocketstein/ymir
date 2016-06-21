# -*- coding: utf-8 -*-
""" ymir.data
"""

from fabric.colors import green, red, cyan, yellow

STATUS_DEAD = ['terminated', 'shutting-down']
OK = green('  ok')
WARN = WARNING = yellow("☛ ")
FAIL = FAILURE = red('✖ ')
SUCCESS = cyan('✓ ')
