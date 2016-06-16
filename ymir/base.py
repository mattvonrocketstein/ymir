# -*- coding: utf-8 -*-
""" ymir.base
"""
from __future__ import print_function
import sys


def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


class Reporter(object):

    def _report_name(self):
        return self.__class__.__name__

    def report(self, msg, *args, **kargs):
        """ 'print' shortcut that includes some color and formatting """
        if 'section' in kargs:
            eprint('-' * 80)
        template = '\x1b[31;01m{0}:\x1b[39;49;00m {1} {2}'
        name = self._report_name()
        # if Service subclasses are embedded directly into fabfiles, there
        # is a need for a lot of private variables to control the namespace
        # fabric publishes as commands.
        name = name.replace('_', '')
        eprint(template.format(
            name, msg, args or ''))


def report(title, msg, *args, **kargs):
    """ FIXME: display hack """
    _reporter = type(title, (Reporter,), dict())()
    _reporter.report(msg)
