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
basics = {
    Required("name") : unicode,
    Required("instance_type") : unicode,
    Optional("org_name", default="org") : unicode,
    #Optional("elasticbeanstalk", default=False) : bool,
    Optional("app_name", default="app") : unicode,
    Optional("service_name", default="service") : unicode,
    Optional("service_defaults", default={}) : dict,
    Required("pem") : unicode,
    Required("health_checks") : dict, # dict like d[check_name] = [ check_type, url ]
    Required("username") : unicode,
    Optional("env_name", default='env') : unicode, }

schema =  basics.copy()
schema.update({
    Required("supervisor_pass") : unicode,
    Optional("supervisor_port", default='9001') : unicode,
    Required("supervisor_user") : unicode,
    Required("ami") : unicode,
    Required("key_name") : unicode,
    Required("setup_list") : list, # list of strings
    Required("security_groups") : list, # list of strings
    Required("provision_list") : list, # list of strings
    })
schema = default_schema = Schema(schema, default=dict(),)
default_schema.schema_name = 'default_schema'

eb_schema =  basics.copy()
eb_schema.update({
    Required("env_name", default='dev') : unicode,
    #Required("instance_type") : lambda x: x=='elasticbeanstalk',
    })
eb_schema = Schema(eb_schema, default=dict(),)
eb_schema.schema_name = 'eb_schema'
