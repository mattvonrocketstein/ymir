""" ymir.schema.security_groups
"""

from voluptuous import Invalid
from .validators import list_of_dicts
def _validate_sg_entry(dct, index=0):
    expected_keys = 'name description rules'.split()
    optional_keys = 'vpc'.split()
    if not isinstance(dct, dict):
        raise Invalid("security_groups entry {0} must be either"
                      " string-name or full dictionary "
                      "specification".format(index))
    for x in expected_keys:
        if x not in dct:
            raise Invalid(
                ("security_group entry #{0} in dictionary format"
                 " is malformed: missing required key `{1}`").format(
                    index, x))
    leftover = set(dct.keys()) - set(expected_keys) - set(optional_keys)
    if leftover:
        raise Invalid(
            ('found unexpected keys in'
             ' security-group entry #{0}: {1}').format(
                index, leftover))
    rules = dct['rules']
    if not isinstance(rules, list):
        raise Invalid("`rules` field must contain list")

    for rule in rules:
        validate_single_rule(rule)


def sg_schema(lst):
    """ bulk-verification for security-group lists """
    list_of_dicts(lst, key='security_group_file')
    for x in lst:
        _validate_sg_entry(x, lst.index(x))

def validate_single_rule(rule):
    """ validate a single aws security group rule"""
    if not isinstance(rule, list):
        err = "every item in `rules` must be a list but {0} is {1}"
        err = err.format(rule, type(rule))
        raise Invalid(err)
    # rule list looks like: ['tcp', 80, 80, '0.0.0.0/0'],
    if len(rule) != 4:
        err = ("individual rules should be lists. "
               "ex: ['tcp', 80, 80, '0.0.0.0/0']")
        raise Invalid(err)
    for i, _type in enumerate([basestring, int, int, basestring]):
        if not isinstance(rule[i], _type):
            err = 'rule {0} is malformed'.format(rule)
            raise Invalid(err)
