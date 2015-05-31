""" ymir.schema.base
"""
from voluptuous import Schema as _Schema
from voluptuous import Required, Optional, Undefined
from .util import list_of_strings

BaseSchema = {
    Required("name") : unicode,
    Required("instance_type") : unicode,
    Required("service_name") : unicode,
    Required("service_description") : unicode,
    Required("health_checks") : dict,
    Required("username") : unicode,
    Required("pem") : unicode,
    Optional("logs", default=[]) : list_of_strings,
    Optional("log_dirs", default=[]) : list_of_strings,
    Optional("ymir_debug", default=False) : bool,
    Optional("s3_buckets", default=[]) : list_of_strings,
    Optional("elastic_ips", default=[]) : list_of_strings,
    Optional("org_name", default="org") : unicode,
    Optional("app_name", default="app") : unicode,
    Optional("service_defaults", default={}) : dict,
    Optional("reservation_extras", default={}) : dict,
    Optional("supervisor_port", default='9001') : unicode,
    Optional("env_name", default='env') : unicode, }

class Schema(_Schema):
    """ """
    def __init__(self, validator, default=None):
        self.default = default
        super(Schema, self).__init__(validator)

    def get_default(self, name):
        default=None
        tmp = [k for k in BaseSchema.keys() if str(k)==name]
        if tmp:
            default=tmp[0].default
            if default == Undefined:
                return None
        if callable(default): return default()
        return default
