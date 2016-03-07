# -*- coding: utf-8 -*-
""" ymir.schema.base
"""
from voluptuous import Schema as _Schema
from voluptuous import Required, Optional, Undefined, Invalid
from .util import list_of_strings
_validate_sl_field = lambda lst: list_of_strings(lst, key='setup_list')
_validate_sg_field = lambda lst: list_of_strings(lst, key='security_groups')
_validate_pl_field = lambda lst: list_of_strings(lst, key='provision_list')


def _validate_puppet_parser(x):
    """ """
    if x != 'future':
        err = "puppet_parser has only one acceptable value: 'future'"
        raise Invalid(err)

AWSSchema = {
    Optional("s3_buckets", default=[]): list_of_strings,
    Optional("elastic_ips", default=[]): list_of_strings,
    Optional("reservation_extras", default={}): dict,
    Required("security_groups", default=[]): _validate_sg_field,
    Required("key_name"): unicode,
}
ProvisionSchema = {
    Required("setup_list", default=[]): _validate_sl_field,
    Required("provision_list", default=[]): _validate_pl_field,
    Optional("puppet_parser", default="future"): _validate_puppet_parser,
}
BaseSchema = {
    Required("name"): unicode,
    Required("instance_type"): unicode,
    Required("service_name"): unicode,
    Required("service_description"): unicode,
    Required("health_checks"): dict,
    Required("username"): unicode,
    Required("pem"): unicode,
    Optional("tags", default=[]): list_of_strings,
    Optional("logs", default=[]): list_of_strings,
    Optional("ymir_debug", default=False): bool,
    Optional("volumes", default=[]): dict,
    Optional("org_name", default="org"): unicode,
    Optional("app_name", default="app"): unicode,
    Optional("service_defaults", default={}): dict,
    Optional("env_name", default='env'): unicode,
    Optional("aws_region"): unicode,
}
SupervisorSchema = {
    Optional("supervisor_user", default='admin'): unicode,
    Optional("supervisor_pass", default='676be646-c477-11e5-bfdc-0800272dfc6a'): unicode,
    Optional("supervisor_port", default='9001'): lambda x: isinstance(x, (unicode, int)),
}
EC2Schema = BaseSchema.copy()
EC2Schema.update(SupervisorSchema)
EC2Schema.update(AWSSchema)
EC2Schema.update(ProvisionSchema)
EC2Schema.update({
    Required("ami"): unicode,
})

BeanstalkSchema = BaseSchema.copy()
BeanstalkSchema.update({
    Required("aws_secret_key"): unicode,
    Required("aws_access_key"): unicode,
})


class Schema(_Schema):
    """ """

    def __init__(self, schema, name='unknown_schema', required=False, extra=0):
        self.schema_name = name
        super(Schema, self).__init__(schema, required=required, extra=extra)

    def __str__(self):
        return "<Schema:{0}>".format(self.schema_name)
    __repr__ = __str__

    def get_field(self, name):
        return [x for x in self.schema.keys() if str(x) == name][0]

    def __getitem__(self, name):
        for x in self.schema:
            if str(x) == name:
                return x.default

    def get_default(self, name):
        """ """
        default = None
        tmp = [k for k in BaseSchema.keys() if str(k) == name]
        if tmp:
            default = tmp[0].default
            if default == Undefined:
                return None
        if callable(default):
            return default()
        return default
