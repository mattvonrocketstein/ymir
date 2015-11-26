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
from fabric import colors

from ymir.util import get_conn

logger = logging.getLogger(__name__)

def _sg_update(sg=None, conn=None, rules=[]):
    assert rules
    logger.debug('  setting up rules for sg {0}'.format(sg))
    return sg


"""
def sg_update(sg_name, conn=None):
    print 'editing security group'
    conn = conn or _get_conn()
    groups = conn.get_all_security_groups([sg_name])
    assert groups, 'security group does not exist yet.'
    print '  syncing security group, creating it'
    sg = groups[0]
    return _sg_update(sg, conn)
"""
import boto.vpc

def get_or_create_security_group(c, group_name, description=""):
    """
    """
    groups = [g for g in c.get_all_security_groups() if g.name == group_name]
    group = groups[0] if groups else None
    if not group:
        print "Creating group '%s'..."%(group_name,)
        group = c.create_security_group(
            group_name, "A group for %s"%(group_name,))
    return group

def sg_rules(sg):
    """ return jsonified sg rules.
        (boto gives objects rather than strings)
    """
    current_rules = []
    for r in sg.rules:
        tmp = [str(r.ip_protocol),
               str(r.from_port),
               str(r.to_port),
               map(str, r.grants)]
        if len(tmp[-1])==1:
            tmp[-1] = tmp[-1][0]
        current_rules.append(tmp)
    return set([tuple(r) for r in current_rules])

def sg_sync(name=None, description=None, rules=[], vpc=None, conn=None):
    """ http://boto.readthedocs.org/en/latest/security_groups.html """
    logger.debug("Synchronizing security group: {0} -- {1}".format(
        name, description))
    assert rules and name
    conn = conn or get_conn()
    description = description or name
    csg_kargs = {}
    if vpc is not None:
        conn = boto.vpc.connect_to_region('us-east-1')
        csg_kargs['vpc_id'] = vpc
    sg = get_or_create_security_group(conn, name, description)
    current_rules = sg_rules(sg)
    rules = set([tuple(map(str, r)) for r in rules])

    new_rules = rules - current_rules
    for rule in new_rules:
        print colors.red('authorizing')+' new rule: {0}'.format(r)
        sg.authorize(*r)

    stale_rules = current_rules - rules
    for r in stale_rules:
        print colors.red('revoking')+' old rule: {0}'.format(r)
        sg.revoke(*r)
