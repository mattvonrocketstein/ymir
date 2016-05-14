# -*- coding: utf-8 -*-
""" ymir.loom

    factories for fabric commands
"""
import os
from fabric.colors import red
from fabric.contrib.console import confirm


def create_version_bump_cmd(pkg_name=None, version_delta=0.1, **kargs):
    """ a factory for generating a 'version-bump' function,
        which can be called from service fabfiles """
    assert pkg_name is not None
    verbose_name = kargs.pop('verbose_name', pkg_name)

    def version_bump():
        """ bump the version number for """ + verbose_name
        sandbox = {}
        version_file = os.path.join(pkg_name, 'version.py')
        err = 'version file not found in expected location: ' + version_file
        assert os.path.exists(version_file), err
        # running "import pkg.version" should have no side-effects,
        # so there's little point in parsing the file.  just exec
        execfile(version_file, sandbox)
        current_version = sandbox['__version__']
        new_version = current_version + version_delta
        with open(version_file, 'r') as fhandle:
            version_file_contents = [x for x in fhandle.readlines()
                                     if x.strip()]
        new_file = version_file_contents[:-1] + \
            ["__version__={0}".format(new_version)]
        new_file = '\n'.join(new_file)
        print red("warning:") + \
            " version will be changed to {0}".format(new_version)
        print
        print red("new version file will look like this:\n")
        print new_file
        ans = confirm('proceed with version change?')
        if not ans:
            print 'aborting.'
            return
        with open(version_file, 'w') as fhandle:
            fhandle.write(new_file)
            print 'version has been rewritten.'
    return version_bump
