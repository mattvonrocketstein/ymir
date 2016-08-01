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
#   * fab release: update this package on pypi
#   * fab version_bump: bump the package version

#
import os

from fabric import api, colors
from fabric.contrib.console import confirm


_ope = os.path.exists
_mkdir = os.mkdir
_expanduser = os.path.expanduser
_dirname = os.path.dirname

ldir = _dirname(__file__)
PKG_NAME = 'ymir'
VERSION_DELTA = .01


@api.task
def version_bump(force=False):
    """ bump the version number for """ + PKG_NAME
    sandbox = {}
    version_file = os.path.join(PKG_NAME, 'version.py')
    err = 'version file not found in expected location: ' + version_file
    assert os.path.exists(version_file), err
    # running "import pkg.version" should have no side-effects,
    # so there's little point in ASTing the file.  just exec it
    execfile(version_file, sandbox)
    current_version = sandbox['__version__']
    new_version = current_version + VERSION_DELTA
    with open(version_file, 'r') as fhandle:
        version_file_contents = [
            x for x in fhandle.readlines() if x.strip()]
    new_file = version_file_contents[:-1] + \
        ["__version__={0}".format(new_version)]
    new_file = '\n'.join(new_file)
    if not force:
        print colors.red("warning:"),
        print " version will be changed to {0}\n".format(new_version)
        print colors.red("new version file will look like this:\n")
        print new_file
        ans = confirm('proceed with version change?')
        if not ans:
            print 'aborting.'
            raise SystemExit(1)
    with open(version_file, 'w') as fhandle:
        fhandle.write(new_file)
        print 'version rewritten to {0}'.format(new_version)


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
