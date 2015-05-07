""" ymir.schema
"""

# TODO: enhance validation for `health_checks`.
# this is a dictionary like so:
#     d[check_name] = [ check_type, url ]

# TODO: enhance validation for the following fields, all lists of strings
#     `provision_list`,`setup_list`, `security_groups`
#     `logs`, `log_dirs`

from voluptuous import Schema as _Schema
#from voluptuous import Invalid
from voluptuous import Required, Optional, Undefined

class Schema(_Schema):
    def __init__(self, validator, default=None):
        self.default = default
        super(Schema, self).__init__(validator)

    def get_default(self, name):
        tmp = [k for k in BaseSchema.keys() if str(k)==name]
        if tmp:
            default=tmp[0].default
            if default == Undefined:
                return None
            return default

BaseSchema = {
    Required("name") : unicode,
    Required("instance_type") : unicode,
    Required("service_name") : unicode,
    Required("service_description") : unicode,
    Required("health_checks") : dict,
    Required("username") : unicode,
    Required("pem") : unicode,
    Optional("logs", default=[]) : list,
    Optional("log_dirs", default=[]) : list,
    Optional("org_name", default="org") : unicode,
    #Optional("elasticbeanstalk", default=False) : bool,
    Optional("app_name", default="app") : unicode,
    Optional("service_defaults", default={}) : dict,
    Optional("supervisor_port", default='9001') : unicode,
    Optional("env_name", default='env') : unicode, }

schema =  BaseSchema.copy()
schema.update({
    Required("supervisor_user") : unicode,
    Required("supervisor_pass") : unicode,
    Required("ami") : unicode,
    Required("key_name") : unicode,
    Required("setup_list") : list,
    Required("security_groups") : list,
    Required("provision_list") : list,
    })

schema = default_schema = Schema(schema, default=dict(),)
default_schema.schema_name = 'default_schema'

eb_schema =  BaseSchema.copy()

eb_schema.update({
    Optional("supervisor_user") : unicode,
    Optional("supervisor_pass") : unicode,
    Required("env_name", default='dev') : unicode,
    #Required("instance_type") : lambda x: x=='elasticbeanstalk',
    })
eb_schema = Schema(eb_schema, default=dict(),)
eb_schema.schema_name = 'eb_schema'
