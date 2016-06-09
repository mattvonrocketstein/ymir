# -*- coding: utf-8 -*-
""" ymir.schema.base
"""

from voluptuous import Schema as _Schema
from voluptuous import Required, Optional, Undefined, Invalid


from ymir.schema import data
from ymir.schema import validators

SupervisorSchema = {
    Optional("supervisor_user", default='admin'): unicode,
    Optional("supervisor_pass", default='676be646-c477-11e5-bfdc-0800272dfc6a'): unicode,
    Optional("supervisor_port", default='9001'): validators.string_or_int,
}

VagrantSchema = data.BASE_DATA.copy()
VagrantSchema.update(data.PROVISION_DATA)

EC2Schema = data.BASE_DATA.copy()
EC2Schema.update(SupervisorSchema)
EC2Schema.update(data.AWS_DATA)
EC2Schema.update(data.PROVISION_DATA)
EC2Schema.update({
    Required("ami"): unicode,
})

BeanstalkSchema = data.BASE_DATA.copy()
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

    def get_service_class(self, service_json):
        from ymir.service import AmazonService, VagrantService
        _map = {
            ('vagrant',): VagrantService,
            }
        kls = AmazonService
        for itypes,proposed_kls in _map.items():
            if service_json['instance_type'] in itypes:
                kls = proposed_kls
                break
        return kls

    def get_field(self, name):
        return [x for x in self.schema.keys() if str(x) == name][0]

    def __getitem__(self, name):
        for x in self.schema:
            if str(x) == name:
                return x.default

    def get_default(self, name):
        """ """
        default = None
        tmp = [k for k in data.BASE_DATA.keys() if str(k) == name]
        if tmp:
            default = tmp[0].default
            if default == Undefined:
                return None
        if callable(default):
            return default()
        return default
