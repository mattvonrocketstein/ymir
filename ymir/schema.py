""" ymir.schema
"""
from voluptuous import Schema as _Schema
from voluptuous import Required, Invalid
class Schema(_Schema):
    def __init__(self, validator, default=None):
        self.default = default
        super(Schema, self).__init__(validator)

schema = Schema(
    {
        Required("instance_type") : unicode,
        Required("name") : unicode,
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
    default=dict()
    )
