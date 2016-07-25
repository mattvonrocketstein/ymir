# -*- coding: utf-8 -*-
"""
"""
from fabric import api


def list_dir(dir_=None):
    """ returns a list of files in a directory (dir_) as absolute paths """
    dir_ = dir_ or api.env.cwd
    if not dir_.endswith('/'):
        dir_ += '/'
    string_ = api.run("for i in %s*; do echo $i; done" % dir_)
    files = string_.replace("\r", "").split("\n")
    return files


def has_gem(name):
    """ tests whether localhost has a gem by the given name """
    with api.quiet():
        x = api.local('gem list|grep {0}'.format(name), capture=True)
    error = x.return_code != 0
    return not error
