Title: Installation
Slug: installation
sortorder: 2
Authors: mvr
Summary: ymir installation

[TOC]

### Prerequisites

A simple python setup for your platform, basically python, python-dev, & python-virtualenv.  For debian you can use a one-liner like this:


    $ sudo apt-get install python python-dev python-virtualenv


### Installation


    $ git clone https://github.com/mattvonrocketstein/ymir.git
    $ cd ymir
    $ virtualenv venv
    $ source venv/bin/activate
    $ pip install -r requirements.txt
    $ python setup.py develop


To test if it worked, try running `ymir version`.

### Suggested software

There's other stuff that you might need, depending on if you want to use vagrant, how you intend to provision stuff, and what kinds of [validation](misc.html#validation) you want ymir to do later.

* [Ansible](https://www.ansible.com/)
* [Puppet linter](http://puppet-lint.com/)
* [Puppet metadata validator](https://rubygems.org/gems/metadata-json-lint)
* [Vagrant](#) and [Virtualbox](#)
