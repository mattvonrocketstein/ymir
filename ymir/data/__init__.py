# -*- coding: utf-8 -*-
""" ymir.data
"""
import os
from fabric.colors import green, red, cyan, yellow

STATUS_DEAD = ['terminated', 'shutting-down']
OK = green('  ok')
WARN = WARNING = yellow("☛ ")
FAIL = FAILURE = red('✖ ')
SUCCESS = cyan('✓ ')
CLOCK = WAIT = WAITING = yellow(u"\u231A")
YMIR_SRC = os.path.dirname(os.path.dirname(__file__))
YMIR_SKELETON = SKELETON_DIR = os.path.join(YMIR_SRC, 'skeleton')
assert os.path.exists(YMIR_SKELETON)
