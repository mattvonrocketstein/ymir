# -*- coding: utf-8 -*-
""" ymir.security_groups

    Helpers for security groups.  These helpers are used as in
    `ymir sg security_group.json` where the JSON schema is roughly:

        [ { "name":'security-group name',
            "description": 'security-group-description',
            "rules": [
                // ["protocol", "from_port", "to_port", "cidr_ip", ]
                ['tcp', 80, 80, '0.0.0.0/0'],        // http
                ['tcp', 22, 22, '0.0.0.0/0'],        // ssh
                ['tcp', 443, 443, '0.0.0.0/0'],      // https
                ['tcp', 1337, 1337, '0.0.0.0/0'],    // supervisor
                ['tcp', 27217, 27217, '0.0.0.0/0'],  // mongo
            ]
          }, ]


"""
import logging

import boto
import boto.vpc
from fabric import colors

from ymir import util

logger = logging.getLogger(__name__)


def get_or_create_security_group(c, group_name, description=""):
    """
    """
    groups = [g for g in c.get_all_security_groups() if g.name == group_name]
    group = groups[0] if groups else None
    if not group:
        print "Creating group '%s'..." % (group_name,)
        group = c.create_security_group(
            group_name, "A group for %s" % (group_name,))
    return group


def sg_rules(sg):
    """ return jsonified sg rules.
        (boto gives objects rather than strings)
    """
    current_rules = []
    for r in sg.rules:
        grants = map(str, r.grants)
        for g in grants:
            if not g.startswith('sg-'):
                current_rules.append([str(r.ip_protocol),
                                      str(r.from_port),
                                      str(r.to_port), ] + [g])
    rules = [tuple(r) for r in current_rules]
    return set(rules)


def sg_sync(name=None, description=None, rules=[], vpc=None, conn=None):
    """ http://boto.readthedocs.org/en/latest/security_groups.html """
    logger.debug("Synchronizing security group: {0} -- {1}".format(
        name, description))
    assert rules and name
    conn = conn or util.get_conn()
    description = description or name
    csg_kargs = {}
    if vpc is not None:
        conn = boto.vpc.connect_to_region('us-east-1')
        csg_kargs['vpc_id'] = vpc
    sg = get_or_create_security_group(conn, name, description)
    current_rules = sg_rules(sg)
    rules = set([tuple(map(str, r)) for r in rules])

    new_rules = rules - current_rules
    stale_rules = current_rules - rules

    if not stale_rules and not new_rules:
        print colors.blue("rules already synchronized:") + \
            " nothing to do."
    if stale_rules:
        print colors.blue("stale rules: ") + \
            "{0} total".format(len(stale_rules))
    if new_rules:
        print colors.blue("new rules: ") + \
            "{0} total".format(len(new_rules))

    for rule in new_rules:
        print colors.blue('authorizing') + ' new rule: {0}'.format(rule),
        util.catch_ec2_error(lambda rule=rule: sg.authorize(*rule))

    for rule in stale_rules:
        print colors.red('revoking:') + \
            ' old rule: {0}'.format(rule)
        util.catch_ec2_error(lambda rule=rule: sg.revoke(*rule))
