[about](#about) | [installation](#installation) | [usage](#usage) | [testing](#testing) |


<a name="about">ABOUT</a>
=========================
Ymir is an automation tool.  Or less generally, it is a service description library/framework that combines the power of fabric, puppet, and boto to create, setup, provision, and control EC2 instances.

  * The [boto](#) library is used for AWS automation (say creating EC2 instance from AMI)
  * The [puppet](#) DSL describes how the instance will be provisioned <sub>(ex: installing system packages)</sub>
  * [Fabric](#) framework is used for command execution on local and remote hosts

Ymir is glue code that can help with automation by generating boilerplate, laying out projects, and giving you a vocabulary you can use to describe your services.

<a name="installation">INSTALLATION</a>
=======================================

```shell
  $ git clone https://github.com/mattvonrocketstein/ymir.git
  $ cd ymir
  $ virtualenv venv
  $ source venv/bin/activate
  $ pip install -r requirements.txt
  $ python setup.py develop
  $ ymir version
```

<a name="usage">USAGE OVERVIEW</a>
===================================

1. Before ymir can work with boto, you'll need to have boto setup.  Follow the [instructions here](http://boto.readthedocs.org/en/latest/boto_config_tut.html) to setup your `aws_access_key_id` and `aws_secret_access_key`

2. Think about how you want to setup your AWS keypairs for accessing the service.  Some people may want one keypair per app, others may want one keypair per service and you may or may not want to change your keypairs per environment.  You can create a keypair by issuing the following command:

```shell
    $ ymir keypair <app_name>
```


3. Initialize a new service with ymir.  This will create a new folder with your project skeleton:

```shell
    $ ymir init demo_service
```

4. Customize your *service description* by making changes to the boilerplate `demo_service/service.json` (this file was created in step 3). The `service.json` file controls important service metadata like the service name, the base AMI, the EC2 instance size, and how health checks should be performed.  Most of the options are illustrated in the default `service.json`.  In particular you will want to change the `name`, `key_name`, and `pem` fields.  For more detailed information about the fields and what they do, see the [service description](#) section of this documentation.

5. Customize your *service implementation* by making changes to the puppet provisioning code in the `demo_service/puppet` directory.  Puppet is the best place to install system packages for your service, add daemons, configure users, etc etc.  Eventually ymir may support chef or shell, but at the moment if you want to invoke that kind of provisioning you'll have to invoke it with puppet (or fork ymir and write some python code.. pull requests are welcome!).  For more detailed information about common provisioning tasks with puppet, see the [service implementation](#) section of this documentation.

6.  At this point you have a pretty good starting place for infrastructure as code: everything is declarative, and the approach leaves you with a good amount of descriptive power and flexibility.  Now it's time to actually test out *service operations*.  If you're willing to write code you can define new operations, but you get lots of basic operations out of the box.  To show a list of operations, make sure you are in the service directory and run this command:

```shell
    $ fab -l
```

To build out your service based on it's description, run

```shell
    $ fab create
```

<a name="service-description">SERVICE OPERATIONS</a>
=====================================================

*Service operations* are "command and control" helpers for your service.  Operations are always [fabric commands](#) which are invoked from your local environment or from a buildbot like [jenkins](#) but executed on your AWS-based service.  Authentication with the remote side happens transparently and automatically, provided your keypair is setup correctly in your [service description](#).  Several operations are defined for you automatically.  If you are familiar with python, adding new operations is as easy as changing your service's `fabfile.py`.  Typical operations are described below.

    * The *create* operation creates your EC2 instance according to the specification in the `service.json' file (which is in the same directory as the fabfile).  To force creation even when your service is already present, use `fab create:force=True`

    * The *setup* operation should typically occur after `create` and before `provision`.  Setup is often slow because it needs to do things like updates for apt or yum.  Setup must be reinvoked if puppet dependencies change.

    * The *provision* operation typically occurs after setup and executes the bulk of the puppet code.  This step should do things like clone or update code repos on the service host, add or update files from templates, etc.  It should run fast and be idempotent.

    * The *status* operation shows service status, including IP address, EC2 status, etc.  It should also display (but not check) URLs which might be useful when running health tests on this service.

    * The *check* operation runs health checks on the service.  The idea is to provide a simple starting point for integration with more sophisticated health monitoring with stuff like nagios.

    * The *ssh* operation simply connects to the service.  Apart from normal system administration or inspecting the service, this is good to use when you suspect that other operations might be failing because of AWS keypair issues.

    * The *run* operation runs a single command on the remote host as the default user.  Very useful for tailing logs and such.

    * The *show* operation integrates with your local browser to opens every webpage that *check* operation would have been looking at.

    * The *test* operation is intended to be an entry point for running integration tests on your service.  By default the *test* operation looks at everything that the *check* operation does, plus extra stuff (see [this section](#) of the service description documentation for more information about how to configure integration tests).

    * The *s3* operation will summarize aspects of the contents of the s3 buckets your service defines, if any.


<a name="service-description">SERVICE DESCRIPTION</a>
=======================================================

Service descriptions are structured service metadata which you can find stored in `service.json` files.  Currently supported fields are described below.

The *security_groups* field defines which AWS security groups this service will belong to.  Ymir may eventually contain helpers for *building* security groups, but at the moment these should probably be constructed by hand in advance.

Both the *setup_list* and *provision_list* fields both describe a list puppet files which will be invoked in standalone-mode on the remote host, in the order they are listed.  For more information on the difference between setup and provisioning, please see [this section](#) of the *service operations* documentation.

The *key_name* and *pem* fields are critical for authenticating with your service to complete updates, etc.  The *key_name* field refers to a named AWS key, and the *pem* field should be a path that points to your corresponding AWS private key file.  If you don't already have a key and pem file, you can create this data using ymir: see [this section](#) of the usage-overview documentation.

<a name="service-implementation">SERVICE IMPLEMENTATION</a>
=========================================================
