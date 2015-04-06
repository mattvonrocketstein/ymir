""" ymir.schema
    // sets namespace  for this service.
    // unused currently but should eventually
    // be used in tagging, etc
    "org_name":"",
    "app_name":"",
    "env_name":"",
"""
from voluptuous import Schema as _Schema
from voluptuous import Required, Optional, Invalid
class Schema(_Schema):
    def __init__(self, validator, default=None):
        self.default = default
        super(Schema, self).__init__(validator)

schema = Schema(
    {
        Required("instance_type") : unicode,
        Required("name") : unicode,
        Optional("app_name") : unicode,
        Optional("org_name") : unicode,
        Optional("env_name") : unicode,
        Required("supervisor_pass") : unicode,
        Required("supervisor_user") : unicode,
        Required("ami") : unicode,
        Required("username") : unicode,
        Required("pem") : unicode,
        Required("key_name") : unicode,
        Required("setup_list") : list, # list of strings
        Required("security_groups") : list, # list of strings
        Required("provision_list") : list, # list of strings
        },
    default=dict(),
    )
