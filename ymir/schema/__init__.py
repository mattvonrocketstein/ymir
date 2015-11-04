""" ymir.schema
"""

# TODO: enhance validation for `health_checks`.
# this is a dictionary like so:
#     d[check_name] = [ check_type, url ]

# TODO: enhance validation for the following fields, all lists of strings
#     `provision_list`,`setup_list`, `security_groups`
#     `logs`, `log_dirs`

from voluptuous import Invalid
from voluptuous import Schema as _Schema
from voluptuous import Required, Optional#, Undefined

from .base import BaseSchema, Schema
from .util import list_of_strings, list_of_dicts

def _choose_schema(json):
    json = json.copy()
    if json.get('instance_type') in [u'elastic_beanstalk', u'elasticbeanstalk']:
        schema = eb_schema
    else:
        schema = default_schema
    return schema


def _validate_sg_entry(dct, index=0):
    if not isinstance(dct, dict):
        raise Invalid("security_groups entry {0} must be either"
                      " string-name or full dictionary "
                      "specification".format(index))
    expected_keys = 'name description rules'.split()
    optional_keys = 'vpc'.split()
    for x in expected_keys:
        if x not in dct:
            raise Invalid(
                ("security_group entry #{0} in dictionary format"
                 " is malformed: missing required key `{1}`").format(
                    index, x))
    leftover = set(dct.keys()) - set(expected_keys) -set(optional_keys)
    if leftover:
        raise Invalid(
            ('found unexpected keys in'
             ' security-group entry #{0}: {1}').format(
                index, leftover))
    rules = dct['rules']
    if not isinstance(rules, list):
        raise Invalid("`rules` field must contain list")
    for rule in rules:
        if not isinstance(rule, list):
            raise Invalid("every item in `rules` must be a list")
        #['tcp', 80, 80, '0.0.0.0/0'],
        if len(rule) != 4:
            err = ("individual rules should be lists. "
                   "ex: ['tcp', 80, 80, '0.0.0.0/0']")
            raise Invalid(err)
        for i, _type in enumerate([basestring,int, int,basestring]):
            if not isinstance(rule[i], _type):
                err = 'rule {0} is malformed'.format(rule)
                raise Invalid(err)

_validate_sg_field = lambda lst: list_of_strings(lst, key = 'security_groups')
_validate_pl_field = lambda lst: list_of_strings(lst, key = 'provision_list')
_validate_sl_field = lambda lst: list_of_strings(lst, key = 'setup_list')

def sg_schema(lst):
    list_of_dicts(lst, key='security_group_file')
    for x in lst:
        _validate_sg_entry(x, lst.index(x))

def _validate_puppet_parser(x):
    if x!='future':
        err = "puppet_parser has only one acceptable value: 'future'"
        raise Invalid(err)

SGFileSchema = _Schema(sg_schema)

schema =  BaseSchema.copy()
schema.update({
    Required("supervisor_user") : unicode,
    Required("supervisor_pass") : unicode,
    Required("ami") : unicode,
    Required("key_name") : unicode,
    Required("setup_list") : _validate_sl_field,
    Required("security_groups") : _validate_sg_field,
    Required("provision_list") : _validate_pl_field,
    Optional("puppet_parser") : _validate_puppet_parser,
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
