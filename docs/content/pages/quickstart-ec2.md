Title: Quickstart: EC2
sortorder: 3
Slug: ec2
Authors: mvr
Summary: quickstart: working with ec2

[TOC]

##Prerequisites

**1. Setup Amazon API keys**

Before ymir can work with boto, you'll need to have boto setup (unless you use multiple amazon accounts, this only happens once).  Follow the [instructions here](http://boto.readthedocs.org/en/latest/boto_config_tut.html) to setup your `aws_access_key_id` and `aws_secret_access_key`

**2. Setup Amazon keypairs**

Think a bit about how you want to setup your AWS keypairs for accessing the service.  Some people may want one keypair per app, others may want one keypair per service and you may or may not want to change your keypairs per environment.  You can create a keypair by issuing the following command:


    $ ymir keypair <app_name>


-----------------------------------------------------------

## Create Boilerplate



**3 Create a service template**

Initializing a new service template with ymir copies boilerplate that you'll find useful.  The following command will create a new folder `demo_service` with your project skeleton:


    $ ymir init demo_service

-----------------------------------------------------------

## Customize things

**4 Customize your service description**

Customize your service description by making changes to the boilerplate in `demo_service/service.json` (this file was created in step 3) you can tune the instance size, tags, and other attributes for your service. The `service.json` file specifies other important service metadata like the service name, the base AMI, the EC2 instance size, and how health checks should be performed.  Most of the options are illustrated in the [default service.json](https://github.com/mattvonrocketstein/ymir/blob/master/ymir/skeleton/service.json).

In particular you will want to change the `name`, `key_name`, and `pem` fields at minimum, where `key_name` and `pem` match what you setup in [step 2](#create_keypairs)  For more detailed information about the fields and what they do, see the [service description](service-description.html#ec2-summary) section of this documentation.

**5. Customize your *service implementation* **

Customize your service implementation.  You can do this with shell, ansible, or puppet or fabric tasks depending on your preference.  Consult the [service implementation](service-implementations.html) section of this documentation.

**7.  Customize and synchronize your AWS security groups**

Open the `security_groups.json` file inside the demo_service directory.  Name your security group, then and add any extra firewall rules you'd like to have apply to your service.  To synchronize your security rules, run the following command:

    $ ymir sg

Make sure the "security_group""* field inside of `service.json` matches whatever name you used here.

**6. Add any customized service operations**

If you're willing to write new code you can define new operations of any kind, but you get lots of basic operations out of the box.  To show a list of default operations, make sure you are in the service root and run this command:

    $ fab -l

For an example of how you might write a deploy operation, see [this example](examples.html#custom-operation).

-----------------------------------------------------------

## Validate and create

**7.  Validate your service description so far**

To make sure your setup is sane so far, run

    $ ymir validate

This will tell you if your AWS keys, security groups, pem files, etc are all setup correctly and will attempt to validate some of your provisioning code.  See the [validation docs](misc.html#validating-boilerplate) for more information.

**8. Instantiate your service, setup & provision it**

Run the create/setup/provision operations one by one, proceeding at each stage if all is well.  Initially it's better to run these separately, because despite retry-behaviours, if you have a bad internet connection then something is liable to timeout and it might be useful to inspect the output more carefully.

    $ fab create
    $ fab setup
    $ fab provision

If you have a great internet connection, try running everything at once:

    fab create wait:30 setup provision

Footnotes
=============
