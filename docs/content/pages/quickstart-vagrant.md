Title: Quick Start: Vagrant
sortorder: 3
Slug: vagrant
Authors: mvr
Summary: quickstart: working with Vagrant

[TOC]

## Prerequisites

 **1. Install vagrant and virtualbox**

Ymir is known to work well with at least [vagrant 1.8.1](https://releases.hashicorp.com/vagrant/1.8.1/) and virtualbox [4.3.38](http://download.virtualbox.org/virtualbox/4.3.38/).  You will probably need a 64 bit host.  Installing these may or may not be complicated depending on your platform but this is outside of the scope of this documentation.

-----------------------------------------------------------

## Create boilerplate

**3. Create a service template**

Initializing a new service template with ymir copies boilerplate that you'll find useful.  The following command will create a new folder `demo_service` with your project skeleton:


    $ ymir init demo_service

-----------------------------------------------------------

## Customize things

**4. Customize your service description**

Most of the instance specifics (RAM, base-box) are configured inside of `Vagrantfile` (this file was created for you in step 3).  Inside `vagrant.json`, make sure the **instance_type** field is always set to "vagrant", and that the **name** field matches the **vm.hostname** value inside `Vagrantfile`.  For more detailed information about the fields and what they do, see the [service description](service-description.html#vagrant-summary) section of this documentation.

### **5** Customize your service implementation

Customize your service implementation.  You can do this with shell, ansible, or puppet or fabric tasks depending on your preference.  Consult the [service implementation](service-implementations.html) section of this documentation.

-----------------------------------------------------------

## Validate and create

**6.  Validate your service description so far**

To make sure your setup is sane so far, run

    $ ymir validate

See the [validation docs](misc.html#validation) for more information.

**7. Add customized service operations**

If you're willing to write code you can define new operations of any kind, but you get lots of basic operations out of the box.  To show a list of default operations, make sure you are in the service directory and run this command: `fab -l`.  For instance, to build out your service based on the `service.json` file, run

    $ fab create

**8. Instantiate your service, setup & provision it**

Run the create/setup/provision operations one by one, proceeding at each stage if all is well.  Initially it's better to run these separately, because despite retry-behaviours, if you have a bad internet connection then something is liable to timeout and it might be useful to inspect the output more carefully.

    $ fab create
    $ fab setup
    $ fab provision

If you have a great internet connection, try running everything at once:

    fab create wait:30 setup provision

Footnotes
=============
