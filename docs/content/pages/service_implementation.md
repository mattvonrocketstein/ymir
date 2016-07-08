Title: Service Implementations
slug: service-implementations
sortorder: 6
Authors: mvr
Summary: ymir service implementations

[TOC]

## Prerequisite reading

Provisioning your service is accomplished via the [service description](service-description.html) fields *setup_list* and *provision_list*, and via the [service operation](service-operations.html) `fab setup` and `fab provision`.  If you haven't reviewed what service descriptions and service operations are all about yet, you might want to read that first.

Also another bit of terminology.. on this page, **local** means you are executing a command that runs (for example) on your friendly neighborhood build bot or a developers laptop.  The service being provisioned is normally referred to as the **remote**.

Some of the examples on this page make use of the [templating capabilities of ymir service descriptions](service-description.html#templating).  <img width=24px src=../images/attention.gif>


## Puppet Provisioning

By default, the field *ymir_build_puppet* is set to true inside service-descriptions.  Whenever puppet support is enabled, puppet will be compiled from scratch by ymir during the `fab setup` phase, so you do not need to choose an AMI that includes it out of the box.  Note: The `fab setup` command uses [pacapt](https://github.com/icy/pacapt#description) to install system packages that are prerequisites for the puppet build, so in theory it doesn't matter whether the remote side is Ubuntu or Centos, etc.

To avoid the complexity of puppet masters, hiera, etc, Ymir always invokes puppet in "stand-alone" mode by copying puppet files from the local machine to the remote service with rsync, then using "puppet apply".  For better or worse (I think it's better) the overall effect is that puppet acts somewhat more like ansible.

#### Puppet Deps

Puppet dependencies are managed via [puppet-librarian](https://github.com/rodjek/librarian-puppet), specified in `<service_root>/puppet/metadata.json` and refreshed whenever the `fab setup` operation is invoked.  The default file generated during `ymir init` invocations is always visible [here](https://github.com/mattvonrocketstein/ymir/blob/master/ymir/skeleton/puppet/metadata.json).

#### Puppet Facts

Strings mentioned inside the **service_defaults** field of your `service.json` file are available as puppet facts.  You may also like to review how [service descriptions are themselves templated](service-description.html#templating).  For instance, if your `service.json` looks like this:


    {
      ... lots of ymir key/values here ...

      provision_list: [
        "puppet://puppet/install_daemon.pp",
      ],

      service_defaults : {
        daemon_port: "1337",
        daemon_config_file: "/etc/daemon.conf"
      },

      ...lots more ymir key/values here ...
    }


Then your puppet file at `<service_root>/puppet/install_daemon.pp` could use these variables like this:

    file { "${daemon_config_file}":
     ensure  => file,
     content => inline_template(" port = <%= @daemon_port %>"),
    }

## Ansible Provisioning

#### Ansible Deps

Ansible dependencies are managed via [ansible-galaxy](), specified in `<service_root>/ansible/requirements.yml`, and refreshed whenever the `fab setup` operation is invoked.  The default file generated during `ymir init` invocations is always visible [here](https://github.com/mattvonrocketstein/ymir/blob/master/ymir/skeleton/ansible/requirements.yml).

#### Ansible Facts

Strings mentioned inside the **service_defaults** field of your `service.json` file are available as ansible variables.  You may also like to review how [service descriptions are themselves templated](service-description.html#templating).  For instance, if your `service.json` looks like this:

    {
     ...lots of ymir key/values...

     provision_list: [
       'local://ansible -u {username} --private-key={pem} -i "{host}," -m some_ansible_module',
     ]

     ...lots of other ymir key/values...
    }

## Other Provisioning

To install a package on the remote side using a local command, your service.json file could look something like the example below.

    {
     ...lots of ymir key/values...

     provision_list: [
       "local://ssh -i {key_file} {username}@{host} sudo apt-get install some_package",
     ]

     ...lots of other ymir key/values...
    }


#### Local commands

#### Remote commands

To install a package on the remote side using a remote command, your service.json file could look something like the example below.


    {
     ...lots of ymir key/values...

     provision_list: [
       "remote://sudo apt-get install some_package",
     ]

     ...lots of other ymir key/values...
    }
