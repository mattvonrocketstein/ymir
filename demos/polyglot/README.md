Polyglot
========

### Service Description

This folder contains "polyglot", a demonstration of a ymir project suitable for AWS or
vagrant, which is provisioned with both ansible and puppet using shared variables.

## What gets provisioned on this service

1. via playbook.yml, ansible pushes a *file* to `/tmp/ansible_tmp_file`
2. via playbook.yml, ansible pushes a *template* to `/etc/motd`
3. via playbook.yml, ansible installs a system package "tree"
4. via playbook.yml & [an ansible-galaxy role](https://galaxy.ansible.com/geerlingguy/nginx/), ansible installs a service "nginx"
5. via demo.pp, puppet pushes a template to `/tmp/puppet_tmp_file`
6. via demo.pp, puppet installs a system package "nmap"
7. via demo.pp, puppet appends content to `/etc/motd`

### Quickstart: Vagrant

You need to have vagrant/virtualbox already installed.  Afterwards, run these commands:

    $ cd ymir/demos/polyglot
    $ export YMIR_SERVICE_JSON=vagrant.json
    $ fab create

### TODO:

1. try the vagrant-quickstart with a missing basebox
