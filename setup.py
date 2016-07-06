#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" setup.py for ymir
"""
import os
import sys
from setuptools import setup
try:
    from pip.req import parse_requirements  # flake8: noqa
except ImportError:
    raise SystemExit("please install pip before installing ymir")
install_reqs = parse_requirements(os.path.join(
    os.path.dirname(__file__), 'requirements.txt'), session=False)
reqs = [str(ir.req) for ir in install_reqs]

# make sure that finding packages works, even
# when setup.py is invoked from outside this dir
this_dir = os.path.dirname(os.path.abspath(__file__))
if not os.getcwd() == this_dir:
    os.chdir(this_dir)

# make sure we can import the version number so that it doesn't have
# to be changed in two places. ymir/__init__.py is also free
# to import various requirements that haven't been installed yet
sys.path.append(os.path.join(this_dir, 'ymir'))
from version import __version__
sys.path.pop()

base_url = 'https://github.com/mattvonrocketstein/ymir/'
setup(
    name='ymir',
    version=__version__,
    description='',
    author='mattvonrocketstein',
    author_email='$author@gmail',
    url=base_url,
    download_url=base_url + '/tarball/master',
    packages=['ymir'],
    keywords=['ymir'],
    entry_points={
        'console_scripts':
        ['ymir = ymir.bin._ymir:entry', ]},
    install_requires=reqs,

    # package_data={'ymir': ['skeleton/*']},
    # this will use MANIFEST.in during install where we specify additional
    # files
    include_package_data=True,

)
