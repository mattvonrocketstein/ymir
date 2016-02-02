[about](#about) | [installation](#installation) | [usage](#usage) | [testing](#testing) |


<a name="about">ABOUT</a>
=========================
Ymir can be used to generate project boilerplate which combines fabric, boto, and puppet to create, setup, provision and control EC2 instances and, to a lesser extent, Elasticbeanstalk instances.  Think of it as "glue code" that can help lay out project skeletons and give you a concise and relevant vocabulary for service description.  Is it like ansible?  Or maybe packer?  How does it compare with vagrant or cloud formation or terraform?  Why doesn't it use salts or chefs?  OMG, I don't know!  It seems useful though, and you might think so too.  It's designed to (at least theoretically) help with creation, provisioning, etc *in general* regardless of the instance OS, but realistically some parts of it are specific to Ubuntu running on EC2.

  * The [Boto](http://boto.readthedocs.org/en/latest/) library is used for AWS automation (ex: creating EC2 instance from AMI)
  * The [Puppet](https://puppetlabs.com/puppet/what-is-puppet) DSL describes how the instances will be setup (ex: installing system packages)
  * The [Fabric](http://docs.fabfile.org/en/latest/tutorial.html) library / framework is used for command execution on local and remote hosts

Ymir is "opinionated" in the sense that it mainly supports puppet for structured provisioning (or perhaps fabric for more adhoc provisioning) and it encourages daemonizing your services with [supervisord](#).  I'm not religious about any of these points though, and for instance the day when I find a big pile of prior art in the form of a chef script with no puppet equivalent then ymir will start to support chef.

And yes, ymir is obviously Yet Another Devops Tool in a rapidly expanding and sometimes confusing toolbox which may or may not make you sigh in frustration.  Probably ymir configuration will eventually supprt "compiling" to terraform or cloudformation.

<a name="installation">INSTALLATION</a>
=======================================

**Prerequisites:** A simple python setup for your platform, basically python, python-dev, & python-virtualenv.  For debian you can use a one-liner like `sudo apt-get install python python-dev python-virtualenv`.

**Installation:**

```shell
  $ git clone https://github.com/mattvonrocketstein/ymir.git
  $ cd ymir
  $ virtualenv venv
  $ source venv/bin/activate
  $ pip install -r requirements.txt
  $ python setup.py develop
```

To test if it worked, try running `ymir version`.

**Suggested software:**
    * [Puppet metadata validator](https://rubygems.org/gems/metadata-json-lint)

<a name="usage">USAGE OVERVIEW</a>
===================================

**1** Before ymir can work with boto, you'll need to have boto setup (unless you use multiple amazon accounts, this only happens once).  Follow the [instructions here](http://boto.readthedocs.org/en/latest/boto_config_tut.html) to setup your `aws_access_key_id` and `aws_secret_access_key`

**2** Think a bit about how you want to setup your AWS keypairs for accessing the service.  Some people may want one keypair per app, others may want one keypair per service and you may or may not want to change your keypairs per environment.  You can create a keypair by issuing the following command:

```shell
    $ ymir keypair <app_name>
```

**3** Initialize a new service with ymir.  This will create a new folder with your project skeleton:

```shell
    $ ymir init demo_service
```

**4** Customize your *service description* by making changes to the boilerplate `demo_service/service.json` (this file was created in step 3). The `service.json` file controls important service metadata like the service name, the base AMI, the EC2 instance size, and how health checks should be performed.  Most of the options are illustrated in the default `service.json`.  In particular you will want to change the `name`, `key_name`, and `pem` fields at minimum.  For more detailed information about the fields and what they do, see the [service description](#service-description) section of this documentation.

**5** Customize your *service implementation* by making changes to the puppet provisioning code in the `demo_service/puppet` directory (this directory was created in step 3).  Puppet is the best place to install system packages for your service, add daemons, configure users, etc etc.  Eventually ymir may support chef or shell, but at the moment if you want to invoke that kind of provisioning you'll have to invoke it with puppet (or fork ymir and write some python code.. pull requests are welcome!).  For more detailed information about common provisioning tasks with puppet, see the [service implementation](#service-implementation) section of this documentation.

**6**  At this point you have a pretty good starting place for infrastructure as code: everything is declarative, and the approach leaves you with a lot of descriptive power and flexibility.  Now it's time to actually test out *service operations*.  If you're willing to write code you can define new operations of any kind, but you get lots of basic operations out of the box.  To show a list of default operations, make sure you are in the service directory and run this command: `fab -l`.  For instance, to build out your service based on the `service.json` file, run `$ fab create`.

<a name="service-operations">SERVICE OPERATIONS</a>
=====================================================

*Service operations* are "command and control" helpers for your service.  Operations are always [fabric commands](http://docs.fabfile.org/en/latest/usage/fab.html) which are _invoked_ from your local environment (or from a buildbot like [jenkins](https://jenkins-ci.org/)) but are _executed_ on your AWS-based service.  Authentication with the remote side happens transparently and automatically, provided your keypair is setup correctly in your [service description](#service-description).   *To execute operations*, cd into the directory for your your service and type `fab operation_name`.  If you're willing to write code and especially if you're familiar with python and fabric, you can define new operations of any kind at any time.  By default though, several operations are already defined for you automatically and they are described below.

| Operation     | Description           |
| ------------- |:-------------:|
| fab *validate*    | attempts to validate configuration files for sanity, useful to execute before `fab create`
| fab *create*      | creates your EC2 instance according to the specification in the `service.json` file (which is in the same directory as the fabfile).  To force creation even when your service is already present, use `fab create:force=True` |
| *setup*       | operation should typically occur after `create` and before `provision`.  Setup is often slow because it needs to do things like updates for apt or yum.  Setup must be reinvoked if puppet dependencies change |
| fab *provision*   | typically occurs after setup and executes the bulk of the puppet code.  This step should do things like clone or update code repos on the service host, add or update files from templates, etc.  It should run fast and be idempotent |
| fab *status*      | shows service status, including IP address, EC2 status, etc.  It should also display (but not check) URLs which might be useful when running health tests on this service. |
| fab *check*       | runs health checks on the service.  The idea is to provide a simple starting point for integration with more sophisticated health monitoring with stuff like nagios |
| fab *ssh*         | operation simply connects to the service.  Apart from normal system administration or inspecting the service, this is good to use when you suspect that other operations might be failing because of AWS keypair issues |
| fab *run*         | operation runs a single command on the remote host as the default user.  Very useful for tailing logs and such |
| fab *show*        | operation integrates with your local browser to opens every webpage that fab *check* operation would have been looking at |
| fab *test*        | operation is intended to be an entry point for running integration tests on your service.  By default the *test* operation looks at everything that the *check* operation does, plus extra stuff (see [this section](#) of the service description documentation for more information about how to configure integration tests) |
| fab *s3*      | summarizes contents of the s3 buckets your service defines, if any |
| fab *get*      | scp "get" for this service.  takes one argument (the remote file) and always saves to the working directory |
| fab *put*      | scp "put" for this service.  (not fully implemented yet) |
| fab  *freeze*      | freeze a (running) service to an AMI (not fully implemented yet) |




<a name="service-description">SERVICE DESCRIPTION</a>
=======================================================

Service descriptions are structured service metadata which you can find stored in `service.json` files.  Particularly important fields which you will definitely want to override are described in the paragraphs below.

The *security_groups* field defines which AWS security groups this service will belong to.  Ymir may eventually contain helpers for *building* security groups, but at the moment these should probably be constructed by hand in advance.

Both the *setup_list* and *provision_list* fields both describe a list puppet files which will be invoked in standalone-mode on the remote host, in the order they are listed.  For more information on the difference between setup and provisioning, please see [this section]() of the *service operations* documentation.

The *key_name* and *pem* fields are critical for authenticating with your service to complete updates, etc.  The *key_name* field refers to a named AWS key, and the *pem* field should be a path that points to your corresponding AWS private key file.  If you don't already have a key and pem file, you can create this data using ymir: see [this section](#) of the usage-overview documentation.


| Field name | Description |
-------------|-------------|

<a name="service-implementation">SERVICE IMPLEMENTATION</a>
============================================================

*Service implementation* is currently achieved with puppet code, but eventually ymir might support chef or shell.
  Pull requests welcome!  Until this feature is added, invoking shell or chef *from* puppet may be the best option.
