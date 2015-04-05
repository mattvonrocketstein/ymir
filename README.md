[about](#about) | [installation](#installation) | [usage](#usage) | [testing](#testing) |


<a name="about">ABOUT</a>
=========================
Ymir is a service description library/framework that combines the power of fabric, puppet, and boto to create, setup, provision, and control EC2 instances.

  * The [boto](#) library is used for AWS automation <sub>(ex creating EC2 instance from AMI)</sub>
  * The [puppet](#) DSL describes how the instance will be provisioned <sub>(ex: installing system packages)</sub>
  * [Fabric](#) framework is used for command execution on local and remote hosts


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

<a name="usage">USAGE</a>
==========================

```shell
    $ ymir init foo # create service directory tree / project layout
```

<a name="testing">TESTING</a>
=============================
