#!/usr/bin/env python
# -*- coding: utf-8 -*-
""" setup.py for ymir
"""
import os
import sys
from setuptools import setup

# make sure that finding packages works, even
# when setup.py is invoked from outside this dir
this_dir = os.path.dirname(os.path.abspath(__file__))
if not os.getcwd() == this_dir:
    os.chdir(this_dir)

# make sure we can import the version number so that it doesn't have
# to be changed in two places. ymir/__init__.py is also free
# to import various requirements that haven't been installed yet
sys.path.append(os.path.join(this_dir, 'ymir'))
from version import __version__ as release_version  # flake8: noqa
sys.path.pop()

base_url = 'https://github.com/mattvonrocketstein/ymir/'
setup(
    name='ymir',
    version=release_version,
    license='apache',
    description='an automation tool for your automation tools',
    long_description='http://mattvonrocketstein.github.io/ymir',
    author='mattvonrocketstein',
    author_email='$author@gmail',
    url=base_url,
    download_url=base_url + '/tarball/master',
    packages=['ymir'],
    keywords=[
        'ymir', 'devops',
        'ansible', 'puppet',
    ],
    entry_points={
        'console_scripts':
        ['ymir = ymir.bin._ymir:entry',
         ]},
    # install_requires=reqs,
    install_requires=[
        "ansible==2.1.0.0",
        "ansible-role==0.24",
        "awsebcli==3.1.2",
        "boto==2.36.0",
        "demjson==2.2.4",
        "Fabric==1.10.1",
        "Importing==1.10",
        "Jinja2==2.8",
        "pycrypto==2.6.1",
        "pyterminalsize==0.1.0",
        "python-vagrant==0.5.13",
        "requests==2.5.1",
        "retrying==1.3.3",
        "testinfra==1.3.0",
        "voluptuous==0.8.11",
        "Werkzeug==0.11.10",      # used for caching
        "YURL==0.13",
    ],
    # package_data={'ymir': ['skeleton/*']},
    # this will use MANIFEST.in during install where we specify additional
    # files
    include_package_data=True,
    classifiers=[
        'Development Status :: 4 - Beta',
        'Environment :: Console',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Operating System :: POSIX',
        'Programming Language :: Python :: 2.7',
        'Topic :: Software Development :: Bug Tracking',
        'Topic :: System :: Installation/Setup',
        'Topic :: System :: Systems Administration',
        'Topic :: Utilities',
    ],
    zip_safe=False,
)
