Title: About
Slug: intro
sortorder: 1
Authors: mvr
save_as: index.html
URL:

[//]: # (ALL LINKS ON THIS PAGE MUST BE like pages/foo.html)

[TOC]

What is it?
======================================

**Ymir** is an automation tool that stitches together other automation tools.  It can be used to quickly generate project boilerplate which combines [fabric](http://docs.fabfile.org/en/latest/tutorial.html), [boto](http://boto.readthedocs.org/en/latest/), and the [configuration-management language of your choice](https://en.wikipedia.org/wiki/Comparison_of_open-source_configuration_management_software) to create, setup, provision, test and control EC2 and Vagrant services (and more experimentally, Elasticbeanstalk services).

Ymir tries to be agnostic about your choice of the configuration management language used for service provisioning, but realistically has the best support for puppet and ansible.  There is currently not any explicit or in-depth support for chef/salt, but insofar as these tools can be invoked via shell commands on the local or remote host, implicit support does exist.

Ymir also has some features for supporting polyglot infracode which you may find interesting if you use a combination of puppet/ansible and would like to simplify storage of configuration variables for both systems.  See the [feature list](#features) below.

Think of ymir as "glue code" that can help lay out project skeletons and give you a concise and relevant vocabulary for service description.   It's designed to help with creation, provisioning, etc, regardless of other technology choices, but it does require some version of *nix, and it's currently only tested with CentOS and Ubuntu.  After services are instantiated, there is [lots of functionality](pages/service-operations.html) for command/control out of the box.

More specifically,

  * [Boto](http://boto.readthedocs.org/en/latest/) is used for AWS automation (ex: creating EC2 instance from AMI).
  * [Fabric](http://docs.fabfile.org/en/latest/tutorial.html) is used for command execution on local and remote hosts, and control automation after services are created.
  * [Testinfra](https://github.com/philpep/testinfra/) provides a quick way to make assertions about server setup/behaviour.
  * Project initialization lays out [service definition JSON](pages/service-description.html) as well as skeletons for beginning work with [puppet](https://docs.puppet.com/puppet/) / [ansible](http://docs.ansible.com/ansible/).
  * [python-vagrant](https://pypi.python.org/pypi/python-vagrant/0.5.14) is used to automate calls into vagrant.

Who is it for?
==============

Ymir is obviously Yet Another Devops Tool in a rapidly expanding and [sometimes](https://github.com/AcalephStorage/awesome-devops) [bewildering](https://xebialabs.com/the-ultimate-devops-tool-chest/open-source/) [toolbox](https://github.com/joubertredrat/awesome-devops), which may or may not make you sigh in frustration.  It was originally built while scratching my own itch for an automation tool, but in the end it's become more than a learning project, and is stable enough for production use.  Is it for you though?  Well, Ymir is probably most suitable for:

1. Small operations, just looking to just keep things simple.  These organizations are perhaps characterized by still having "[pets not cattle](http://www.theregister.co.uk/2013/03/18/servers_pets_or_cattle_cern/)" (and they are mostly unapologetic about that since it works well for them).  Perhaps these organizations are interested in having better-specified pets that are terminated/resurrected/restructured reliably with infrastructure-as-code, but are mostly **not** interested in having truly immutable infrastructure because they don't have time/money to restructure applications or rearchitect their CI / CD workflows.

2. Transitional operations or hackers, who are experimenting with infrastructure-as-code, but are unable (or unwilling) to limit themselves to only one do-everything CM language.  Sometimes the main idea is to deliver a server or "golden image" quickly, and having maintainable infracode is just a bonus that management (unfortunately) doesn't really understand or care about.  Under these circumstances picking a "favorite" CM language makes little sense, and you just want to use the one that's already closest to providing a complete solution for your problem.

3. Anyone who is addicted to puppet, but who is frustrated by the lack of fail-fast behaviour and the obnoxious requirements of agents, additional servers, etc to get basic work done.


Under the hood
================

Ymir has two parts: a command line utility, and a library.

The functionality of the command line utility is sparse, because it's main purpose is to generate project boilerplate using [the *ymir init* invocation](pages/misc.html#ymir_init).  But, as a command line tool, ymir does have a few other [helper functions](pages/misc.html) such as project validation, AWS key generation, etc.

Service boilerplate generated by the ymir command line includes a two very important files: **service.json** and **fabfile.py**.

The **service.json** file, aka the [service description](pages/service-description.html) describes the details of the service you are building including the instance type / size, plus other details that will be used in creating and provisioning the service.  You can read more about that file and its schema [here](pages/service-description.html).

The **fabfile** allows you to interact with your service via fabric and ymir-as-a-library.  How does this work?  Basically ymir-as-a-library creates a "service object" from the service description JSON, then publishes the service object instance methods into the fabric namespace to automatically generate command-and-control functions, aka the [service operations](pages/service-operations.html).

Features
=========

So is ymir like [docker](https://www.docker.com/) or maybe [packer](https://www.packer.io/)?  How does it compare with [vagrant](https://www.vagrantup.com/) or [cloud formation](https://aws.amazon.com/cloudformation/) or [terraform](http://www.terraform.io)?  Why doesn't it use [salt](https://saltstack.com/) or [chef](https://www.chef.io)?  OMG, I don't know!  There's a lot of stuff in the ecosystem and even building a taxonomy for the huge number of tools is difficult.  Ymir probably closest to vagrant, but when work began on ymir, most of the available tooling felt unstable or stifling.[ref] For instance: Missing vagrant plugins for puppet-librarian support, AWS options conspicuously missing from vagrant-aws, terraform has poor support for ansible and for [reprovisioning existing resources](http://stackoverflow.com/questions/37865979/terraform-how-to-run-the-provisioner-on-existing-resources) [/ref].  Besides, it's well known that **sufficiently advanced abstractions are indistinguishable from obfuscation** and this seems like a bad thing.  Therefore...

Here's a quick list of features and (equally importantly) non-features.

1. **Ymir .**  Specific support for docker, digital ocean, rackspace, etc, will never be a priority but there is some support for [working with Vagrant](pages/examples.html#vagrant).

2. **Ymir has a focus on building servers, not building multi-server clusters with complex, contingent, and entangled configurations.**  Simple orchestration is easily possible, but if you need really complex things you should probably look elsewhere (or perhaps use ymir to drive an external tool such as terraform).

3.  **Ymir has no server-side agents, and no additional servers/daemons CM key-alue stores**.  No ansible towers, vaults, puppet-masters, mcollectives, etc, etc.  There's no RESTful API for ymir, but there's also no server to harden/firewall, certificates to setup, or access-control DSLs to learn before you can get started using it.

4.  **Ymir's configuration format supports [reflective templating](pages/service-description.html#templating), but is free of logic, macros, etc, and only supports a very limited concept of extension/inclusion.** [ref] For comparison, see [inclusion in ansible](http://docs.ansible.com/ansible/playbooks_roles.html#task-include-files-and-encouraging-reuse) and the [built-in functions for terraform's language](https://www.terraform.io/docs/configuration/interpolation.html). [/ref] Logic, macros, and all the rest inevitably creep into declarative configuration because it encourages reuse, but has the down-side of encouraging fragmentation and increasing overall complexity. Reuse for ymir configuration is not a priority because this configuration is not code.. reuse should happen instead at the layer with ansible/puppet/python source code.

5. **Ymir as driver for provisioning makes it easier to use puppet in stand-alone mode on remote hosts, agent-free**, similar to how you might use ansible.  More specifically, when *ymir_build_puppet* is enabled in service JSON, puppet is installed from scratch on the remote side (thus you aren't restricted to images with puppet pre-installed).  Puppet files in your ymir project are rsync'ed to the remote, and executed via ssh and puppet-apply.

6. **Ymir as a driver for provisioning can help make "the puppet paradigm" less astonishing.**  Puppet has a an active community but the language has many quirks.  The most common complaints are probably: a) it operates as a state-machine, potentially ignoring errors to achieve the most complete state possible and b) that the execution order of statements is not guaranteed.  Since ymir puppet provisioning works with multiple sequential puppet-apply instructions both of these behaviours are mitigated.

6. **Ymir reads configuration variables from JSON in file on VCS**, and instance configuration variables (such as *AMI*, *instance_type*, etc), can optionally live side-by-side with infracode configuration variables (such as *daemon_listen_port* or *use_ssl*).  Depending on [how your write your deploy operations](pages/examples.html#deploy_operation) it often makes sense to put application secrets here as well because, whereas your application may be open source, your infracode repo probably is not.

7. **Ymir can publish configuration variables to both puppet and ansible**.  The motivation for this is that, while larger organizations will not want to maintain polyglot CM langs, smaller organizations and experimenters simply want to leverage as much prior art as possible to build out servers faster.

8. **Ymir's invocation is simple** and is designed to be used on-demand by your standard impatient, amnesiac human.  A policy of "one server, one ymir JSON file" means you don't need to memorize or copy/paste hostnames, ip addresses, hashes, or AWS instance IDs.  You also won't need to export dozens environment variables or use dozens of command line flags to get stuff done.  You can obviously invoke ymir from a buildbot if you so choose, but other than that there are no ambitions to daemonize, serverize, or premptively "auto synchronize" infracode changes onto servers.

9. **Adding extra command/control automation is simple**, and the place extra automation should go is clear.  Just edit the fabfile.  If you don't want command/control automation written in python, you can parse the output of the ymir dynamic inventory script as in [this example](pages/broken_link.html).

10. **Ymir has is built-in support for making assertions about infrastructure**.  You can use these while you're developing new provisioning infracode to verify your changes are working as expected, or use them in CI or monitoring.

Contributing
=============

**Pull requests and feature requests are welcome**, just use [the githubs](https://github.com/mattvonrocketstein/ymir/issues).

**Testing:**.   All tests are run with tox.  Afterwards, you can view the coverage results in the `htmlcov` folder.

    $ pip install tox
    $ tox


**Commit hooks**: To maintain consistent style in the library, please use the same precommit hooks as me.  To install precommit hooks after cloning the source repository, run these commands:

    $ pip install pre-commit
    $ pre-commit install


**Documentation:**  Contributions to this documentation (in the `docs` folder of the source root) are also welcome.  If you make significant changes, run the documentation test-server and the script to check for broken links.
    $ cd docs
    $ fab run # runs the auto-updating test server for the markdown docs

In another terminal, run the crawler script against the test server

    $ fab check_links

Footnotes
=============
