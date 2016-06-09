# -*- coding: utf-8 -*-
""" ymir.schema
"""

# TODO: enhance validation for `health_checks`.
# this is a dictionary like so:
#     d[check_name] = [ check_type, url ]

# TODO: enhance validation for the following fields, all lists of strings
#     `logs`

from voluptuous import Invalid

from ymir.base import report as base_report
from ymir import util
from .security_groups import sg_schema
from .base import Schema, BeanstalkSchema, EC2Schema, VagrantSchema

_report = lambda *args: base_report("ymir.schema", *args)
SGFileSchema = Schema(sg_schema)

default_schema = Schema(EC2Schema, name='ec2_schema')
eb_schema = Schema(BeanstalkSchema, name='beanstalk_schema',)
vagrant_schema = Schema(VagrantSchema, name='vagrant_schema')

def choose_schema(json, quiet=False):
    """ """
    report = util.NOOP if quiet else _report
    instance_type = json.get('instance_type')
    if instance_type in [u'elastic_beanstalk', u'elasticbeanstalk']:
        schema = eb_schema
    elif instance_type in ['vagrant']:
        schema = vagrant_schema
    else:
        schema = default_schema
    report("chose schema {0} based on instance_type `{1}`".format(
        schema.schema_name, instance_type))
    return schema
