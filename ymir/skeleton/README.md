Service Description
===================

A high level description of your service goes here.  What does it do?

Caveats
=======

Place any known bugs or design flaws in this section in the list below.

    * The service is passworded by default, but..
    * Automation does not configure..

Accessing the Service
======================

Which ports are meant to be accessible?  Is that public or only from certain security groups?  Do you need to authenticate to use the service?  Where can information be found about the credentials?

Service Automation in General
=============================

All services have similar automation that can help you create, destroy, provision, and control service instances.  These automation commands are implemented with a combination of fabric, boto and puppet.  To get started issuing commands, you'll need system packages like python and python-dev, python-virtualenv, and python-pip (NOTE: you already have most of these if you're using the EB CLI).

1. Build an environment:

```
$ cd $project_root
$ virtualenv devops --no-site-packages.
$ source devops/bin/activate # always run this command before "fab" commands
$ pip install -r automation_requirements.txt
```

2. Choose a service to work with and list the available commands:

```
$ source devops/bin/activate # always run this command before "fab" or "ymir" commands
$ cd demo_service_directory
$ fab -l
```

Typical commands:

* fab validate # attempts to make sure configuration files have all necessary settings, useful to execute before `fab create`
* fab create # create a new instance
* fab create:force=True # for creating a new instance, overwriting if necessary
* fab status # show status for current instance (assuming it exists)
* fab setup # for (re)setup'ing an instance (useful when dependencies change)
* fab provision # for reprovisioning an instance (useful after making code changes)
* fab ssh # connection to the service instance
* fab check # verify that the instance is up and working (possible template for nagios code)

Service implementation
=======================

*All services* are defined in folders which contain a `fabfile.py`.  This file describes the fabric commands for that service, a directory for puppet/ansible files which store the host configuration, directories, file templates, etc, which are used in the implementation of that service.

**The demo service** is implemented with..
