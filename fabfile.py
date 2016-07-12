#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# fabfile for ymir
#
# this file is a self-hosting fabfile, meaning it
# supports direct invocation with standard option
# parsing, including --help and -l (for listing commands).
#
# summary of commands/arguments:
#
#   * fab pypi_repackage: update this package on pypi
#   * fab version_bump: bump the package version

#
import os

from fabric import api
from fabric.contrib.console import confirm
from fabric.colors import red

from ymir.loom import create_version_bump_cmd

_ope = os.path.exists
_mkdir = os.mkdir
_expanduser = os.path.expanduser
_dirname = os.path.dirname

ldir = _dirname(__file__)

VERSION_DELTA = .01

version_bump = create_version_bump_cmd(
    pkg_name='ymir', version_delta=VERSION_DELTA)
version_bump = api.task(version_bump)


@api.task
def pypi_repackage():
    ldir = _dirname(__file__)
    print red("warning:") + (" by now you should have commited local"
                             " master and bumped version string")
    ans = confirm('proceed with pypi update in "{0}"?'.format(ldir))
    if not ans:
        return
    with api.lcd(ldir):
        with api.settings(warn_only=True):
            # in case this has never been done before
            api.local("git checkout -b pypi")
        api.local("git reset --hard master")
        api.local("python setup.py register -r pypi")
        api.local("python setup.py sdist upload -r pypi")


@api.task
def test():
    with api.lcd(os.path.dirname(__file__)):
        api.local('py.test --cov-config .coveragerc '
                  '--cov=ymir --cov-report=term -v '
                  '--pyargs ./tests')


@api.task
def vulture():
    with api.lcd(os.path.dirname(__file__)):
        api.local(
            'vulture ymir --exclude fabfile.py|grep -v _provision_|grep -v ymir/checks.py')

if __name__ == '__main__':
    # a neat hack that makes this file a "self-hosting" fabfile,
    # ie it is invoked directly but still gets all the fabric niceties
    # like real option parsing, including --help and -l (for listing
    # commands). note that as of fabric 1.10, the file for some reason
    # needs to end in .py, despite what the documentation says.  see:
    # http://docs.fabfile.org/en/1.4.2/usage/fabfiles.html#fabfile-discovery
    #
    # the .index() manipulation below should make this work regardless of
    # whether this is invoked from shell as "./foo.py" or "python foo.py"
    import sys
    from fabric.main import main as fmain
    patched_argv = ['fab', '-f', __file__, ] + \
        sys.argv[sys.argv.index(__file__) + 1:]
    sys.argv = patched_argv
    fmain()
