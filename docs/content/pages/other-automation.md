Title: Misc.
Slug: misc
sortorder: 7
Authors: mvr
Summary: ymir commandline and other automation helpers

[TOC]

## Automation Helpers

Primarily you will interact with your services using [service operations](service-operations.html) which are generated for you based on your [service description](service-description.html).  This section describes other, generic automation helpers  which are provided by the ymir command line utility and which do *not* interact with a specific concrete service.

## Validating boilerplate

To validate ymir service boilerplate simply use `ymir validate` in the working directory for your service.

** Validation that runs only for the EC2-schema JSON includes:**

* Confirmation for the "pem" service description field, i.e. confirmation that your local key file actually exists.
* Confirmation for the "keypair"service description field, i.e. confirmation that the AWS keypair mentioned exists according to the AWS API.


**Generic validation includes:**

* If "service.json" exists, confirmation that it conforms to the appropriate JSON schema
* If "vagrant.json" exists, confirmation that it conforms to the appropriate JSON schema
* Confirmation for "security_groups" service description entries, i.e. confirmation that the security groups mentioned exist according to the AWS API.
* Confirmation that puppet metadata.json is well-formed (uses the [metadata-json-lint gem](https://github.com/voxpupuli/metadata-json-lint))
* Confirmation that puppet provisioning code is lint-free (uses [puppet-lint](http://puppet-lint.com))
* *Heuristic confirmation* that puppet templates only use facts which are defined somewhere in "service.json"


## Creating Keypairs

To create a new AWS keypair, use `ymir keypair <keypair_name>`.  The pem file will be saved in the current working directory.  Use `ymir keypair -f <keypair_name>` to force creation (and possibly overwrite a local file) without asking for confirmation.


## Synchronizing security groups

By using either `ymir sg security_groups.json` or `ymir security_groups security_groups.json` you can synchronize AWS security groups with provided JSON file.  Note that this is true synchronization in the sense that it doesn't just add rules.. rules discovered for this security group via the AWS API that are not mentioned in `security_groups.json` will be removed.  To learn about `security_group.json` schema, see the example json below or view it on github [here](https://github.com/mattvonrocketstein/ymir/blob/master/ymir/skeleton/security_groups.json).  This file is exactly what's included in the boilerplate generated by the `ymir init` command.


<script src="https://gist-it.appspot.com/github/mattvonrocketstein/ymir/blob/master/ymir/skeleton/security_groups.json"></script>

----------------------------------------------------
