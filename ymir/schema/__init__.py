# -*- coding: utf-8 -*-
""" ymir.schema
"""

# TODO: enhance validation for `health_checks`.
# this is a dictionary like so:
#     d[check_name] = [ check_type, url ]

from ymir import util
from ymir.base import report as base_report
from .security_groups import sg_schema
from .base import Schema, BeanstalkSchema, EC2Schema
from .data import VAGRANT_DATA

NOOP = util.NOOP
_report = lambda *args: base_report("ymir.schema", *args)
SGFileSchema = Schema(sg_schema)

default_schema = Schema(EC2Schema, name='EC2-Schema')
eb_schema = Schema(BeanstalkSchema, name='BeanstalkSchema',)
vagrant_schema = Schema(VAGRANT_DATA, name='VagrantSchema')


def choose_schema(json):
    """ """
    instance_type = json.get('instance_type')
    if instance_type in [u'elastic_beanstalk', u'elasticbeanstalk']:
        schema = eb_schema
    elif instance_type in ['vagrant', ]:
        schema = vagrant_schema
    else:
        schema = default_schema
    return schema
