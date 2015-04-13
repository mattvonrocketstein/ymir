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
        Optional("org_name", default="org") : unicode,
        Optional("app_name", default="app") : unicode,
        Optional("service_name", default="service") : unicode,
        Optional("env_name", default='env') : unicode,
        Required("supervisor_pass") : unicode,
        Optional("supervisor_port", default='9001') : unicode,
        Optional("service_defaults", default={}) : dict,
        Required("supervisor_user") : unicode,
        Required("ami") : unicode,
        Required("username") : unicode,
        Required("pem") : unicode,
        Required("key_name") : unicode,
        Required("setup_list") : list, # list of strings
        Required("security_groups") : list, # list of strings
        Required("provision_list") : list, # list of strings
        Required("health_checks") : dict, # dict like d[check_name] = [ check_type, url ]
        },
    default=dict(),
    )
