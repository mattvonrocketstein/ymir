Title: Service Operations
Slug: service-operations
sortorder: 5
Authors: mvr
Summary: ymir service operations

[TOC]

-----------------------------------------------------------

### Overview


*Service operations* are "command and control" helpers for your service.  Operations are always [fabric commands](http://docs.fabfile.org/en/latest/usage/fab.html) which are _invoked_ from your local environment (or from a buildbot like [jenkins](https://jenkins-ci.org/)) but are typically _executed_ on the remote service.  Authentication with the remote side happens transparently and automatically, provided your [service description](service-description.html) is setup correctly.   To list operations, cd into the service root and run

    $ fab --list

Executing individual operations is normally as simple as running

    $ fab <operation_name>

Passing arguments to operations is also possible, and occasionally desirable.  For instance to tail syslog on the remote service, you can use a command like this:

    $ fab tail:/var/log/syslog

The syntax above might look a little funny, but that's so each fabric task can have separate options. See [the fabric documentation here](http://docs.fabfile.org/en/1.11/usage/fab.html#per-task-arguments) for more information.

Note that the **global** arguments of fabric (to specify hosts, keyfiles, etc) should generally not be used with ymir at all, because these are implied your `service.json` or `vagrant.json` configurations.  <img width=24px src=../images/attention.gif>

If you're willing to write code and especially if you're familiar with python and fabric, you can easily define new operations of any kind at any time (take a look at code for a [custom operation here](examples.html#custom_operations)).  By default though, several operations are already defined for you automatically and they are described below.

-----------------------------------------------------------

### Built-in Operations

<table>
<tr><th>Operation</th><th>Description</th></tr>

<tr><td class=td_operation>fab create</td><td>
Creates your EC2 instance according to the specification in the `service.json` file (which is normally in the same directory as the fabfile).  To force creation even when your service is already present, use `fab create:force=True`
</td></tr>

<tr><td class=td_operation>fab setup</td><td>
The setup operation should typically occur after "create" and before "provision".  Setup is safe to invoke repeatedly, but is separated from "provision" because it often involves very slow steps like updates for apt or yum.  Setup can be reinvoked if <a href=#>puppet dependencies</a> change, or if you wish to resynchronize things like tags, s3 buckets, or elastic IPs.  More information about the "setup" phase is available <a href=#setup>here</a>.
</td></tr>

<tr><td class=td_operation>fab provision</td><td>
The provision operation typically occurs after "setup" and executes the bulk of provisioning code.  This step should do things like clone or update code repos on the service host, add or update files from templates, etc.  It should always run fast and be idempotent.  More information about the "provision" phase is available <a href=#>here</a>.
</td></tr>

<tr><td class=td_operation> fab status</td><td>
The "status" operation shows service status, including IP address, EC2 status, etc.  It also displays (but does not check) URLs which might be useful when running health tests on this service.</td></tr>

<tr><td class=td_operation> fab check</td><td>
The "check" operation runs health checks on the service.<br/>
The idea is to provide a simple starting point for integration with more sophisticated health monitoring via stuff like periodic jenkins jobs, nagios, etc.  See [this section](service-description.html#health-checks) of the service-description documentation for more information.
</td></tr>

<tr><td class=td_operation>fab ssh</td><td>
The "ssh" operation simply connects to the service.<br/>
Apart from normal system administration or inspecting the service, this is good to use when you suspect that other operations might be failing because of AWS keypair issues.
</td>
</tr>

<tr><td class=td_operation>fab mosh</td><td>
The "mosh" operation connects to the service using <a href="https://mosh.mit.edu/">mosh</a>.  <br/>
Only defined for Amazon-based services, not supported with vagrant.  It is required that mosh already be installed on the remote side, and your security group has openings for the correct ports.
</td></tr>

<tr><td class=td_operation>fab run</td><td>
The "run" operation runs a single command on the remote host as the default user.  Useful for tailing logs and such.<br/>
For example: <code>fab run:"whoami"</code>
</td></tr>

<tr><td class=td_operation>fab show</td><td>
The "show" operation invokes your local webbrowser to open every webpage that `fab check` operation would have been looking at.
</td></tr>

<tr><td class=td_operation>fab s3</td><td>
The "s3" operation summarizes contents of the s3 buckets your service defines, if any.
</td></tr>
<tr><td class=td_operation>fab get</td><td>
The "get" operation is a shortcut for "scp get" commands against this service.   It takes one argument (the remote file) and always saves to the working directory.  Under the hood, this uses <a href="http://docs.fabfile.org/en/1.0.0/api/core/operations.html#fabric.operations.get">fabric.operations.get</a>.
</td></tr>

<tr><td class=td_operation>fab put</td><td>
The "put" operation is a shortcut for "scp put" commands against this service.  It takes two arguments, namely the local file and the remote destination.  Under the hood, this uses <a href="http://docs.fabfile.org/en/1.0.0/api/core/operations.html#fabric.operations.put">fabric.operations.put</a>.<br/>
Examples: <code>fab put:local_fname,remote_dir,owner=user</code> <code>fab put:local_fname,remote_fname</code>
</td></tr>
<tr><td class=td_operation>fab freeze</td><td>
The "freeze" operation saves the current service to an AMI <font color=red>(not implemented yet)</font>
</td></tr>
</table>

<hr/>

### Setup Operation

Invoke this operation from the root directory of your service with the command

    $ fab setup

.The **setup** operation's primary responsibility is to update dependencies which the **provision** operation requires.  This includes:

* Updating ansible dependencies on the local side, based on `ansible/requirements.yml`
* Synchronizing / updating puppet dependencies on the remote side, based on `puppet/metadata.json`
* Building puppet itself on the remote if it is found to be missing.
* Executing additional custom setup operations which are specified inside the *setup_list* field of `service.json`

You can read about the file format for ansible's `requirements.yml` [here](http://docs.ansible.com/ansible/galaxy.html#advanced-control-over-role-requirements-files), and the file format for puppet's metdata.json [here](#).

Ansible dependencies are **always** updated during the **setup** operation.  Puppet will be built and it's dependencies are updated only if *ymir_build_puppet* is true inside `service.json`.

The **setup** operation is differentiated from the **provision** operation mainly just because it is likely to be slow and should run less frequently.  **Therefore while you're experimenting with new infracode, most changes you make to `service.json` should be to *provision_list* not *setup_list*.**  Work that has been completed in a previous run (like installing git or ruby) will be very fast in subsequent runs, but depending on your base image and your internet connection, building puppet may also involve downloading and compiling all kinds of other build-tools.

### Provision Operation

Invoke this operation from the root directory of your service with the command

    $ fab provision

.The **provision** operation's sole responsibility is to configure the service using all of the instructons mentioned in `service.json` under the *provision_list* field.

### Check Operation

Invoke this operation from the root directory of your service with the command

    $ fab check

.The **check** operation is used to execute health checks for this service.

### Custom Operations

[See this section of the examples page](examples.html#custom_operation)

### Footnotes
