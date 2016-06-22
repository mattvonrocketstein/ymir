# -*- coding: utf-8 -*-
""" ymir.schema.data
"""
from voluptuous import Required, Optional


from ymir.schema import validators

AWS_DATA = {
    Required("username"): unicode,
    Required("pem"): unicode,
    Optional("aws_region"): unicode,
    Optional("s3_buckets", default=[]): validators.list_of_strings,
    Optional("elastic_ips", default=[]): validators.list_of_strings,
    Optional("tags", default=[]): validators.list_of_strings,
    Optional("reservation_extras", default={}): dict,
    Required("security_groups", default=[]): validators._validate_sg_field,
    Required("key_name"): unicode,
}

PROVISION_DATA = {
    Required("setup_list", default=[]): validators._validate_sl_field,
    Required("provision_list", default=[]): validators._validate_pl_field,
    Optional("puppet_parser", default="future"): validators._validate_puppet_parser,
}

BASE_DATA = {
    Required("name"): unicode,
    Optional("port", default='22'): unicode,
    Required("service_name"): unicode,
    Required("service_description"): unicode,
    Required("instance_type"): unicode,
    Required("health_checks"): dict,
    Optional("logs", default=[]): validators.list_of_strings,
    Optional("ymir_debug", default=False): bool,
    Optional("ymir_build_puppet", default=True): bool,
    Optional("volumes", default=[]): dict,
    Optional("org_name", default="org"): unicode,
    Optional("app_name", default="app"): unicode,
    Optional("service_defaults", default={}): dict,
    Optional("env_name", default='env'): unicode,
}

VAGRANT_DATA = BASE_DATA.copy()
VAGRANT_DATA.update(PROVISION_DATA)
VAGRANT_DATA.update(
    {Required("vagrant"): validators.nested_vagrant_validator})
