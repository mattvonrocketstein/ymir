Title: Examples
Slug: examples
sortorder: 7
Authors: mvr

[TOC]

Ymir [source code](#) includes various demos that showcase functionality and can be used for integration testing ymir itself.

#### Polyglot demo

Ymir ships with a demo that is setup to work with AWS and vagrant, and shows how to configure a system with a combination of ansible and puppet using shared variables.  See [the README](https://github.com/mattvonrocketstein/ymir/blob/master/demos/polyglot/README.md) below for more information

<script src="https://gist-it.appspot.com/github/mattvonrocketstein/ymir/blob/vagrant/demos/polyglot/README.md"></script>

#### Custom Operations

**About the default fabfile**

If you only want to do provisioning with ymir then you need not worry about exactly how ymir uses [fabric](http://docs.fabfile.org/en/latest/tutorial.html), but if you want to implement custom command and control [service operations](service-operations.html) then it is worth understanding.

 Ymir fabfiles typically contain the same preamble which is responsible for loading the service object from the service definition, and publishing various methods on the service object as fabric commands.  All that is accomplished in the default `fabfile.by` which is created in `ymir init`.  You can view the standard code below:

    :::python
    import os
    from fabric import api
    from ymir import load_service_from_json

    # use service.json file from YMIR_SERVICE_JSON env var or look in cwd
    YMIR_SERVICE_JSON = guess_service_json_file(default='service.json')

    # Create the ymir service from the service description
    service = load_service_from_json(YMIR_SERVICE_JSON)

    # Install the standard service operations here
    # (like create, terminate, provision, etc) as fabric commands.
    # Custom service operations can be defined below this point.
    service.fabric_install()


#### Python

**Fabric tasks as service operations:**

Defining a custom service operation is mostly the same as [writing a normal fabric task](http://docs.fabfile.org/en/1.11/usage/tasks.html#the-task-decorator).  Here's an example deploy task, which uses a mixture of standard fabric remote execution, standard fabric local execution, and bits of the ymir api as helpers.  After the `deploy` operation below is defined in your fabfile it is available to you now just like other service operations, so you can invoke it with `fab deploy:branch_name`.

    :::python
    import os
    from fabric import api

    ## .. standard ymir preamble here, see previous examples ..

    SRC_ROOT = os.path.join(os.path.dirname(__file__), 'code')
    DEPLOY_PATH = "/srv/site/"

    @api.task
    def deploy(branch='master'):
        """ deploy operation """
        service.report("Rebuilding and deploying: {0}".format(branch))
        with api.lcd(SRC_ROOT):
            api.local("make build")
            service.put("build_result", DEPLOY_PATH)
        service.sudo("service daemon restart")

**Service context managers**:

Here's another example operation which verifies the default system user and `sudo` capabilities on the remote side and introduces

    :::python
    from fabric import api

    ## .. standard ymir preamble here, see previous examples ..

    def user_info():
      """ show remote user information """
      # to use normal fabric functions, use the service.ssh_ctx context manager
      with service.ssh_ctx():
        api.run("whoami")
        api.sudo("whoami")

      # if you use service helpers instead of vanilla fabric, you don't need a context manager
      service.run("whoami")
      service.sudo("whoami")



#### Footnotes
