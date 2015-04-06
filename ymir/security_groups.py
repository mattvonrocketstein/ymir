""" ymir.security_groups

    Helpers for security groups.. these are not used currently
"""
import collections

import boto

def _sg_update(sg=None, conn=None, rules=RULES):
    print '  setting up sg rules'
    for r in rules:
        try:
            sg.authorize(*r)
        except boto.exception.EC2ResponseError:
            print "  warning: could not set rule (maybe dupe): ",r
        else: print "  set new rule:",r
    return sg


#https://gist.github.com/steder/1498451
SecurityGroupRule = collections.namedtuple(
    "SecurityGroupRule",
    ["ip_protocol", "from_port",
     "to_port", "cidr_ip", "src_group_name"])

def sg_update(conn=None):
    print 'editing security group'
    conn = conn or _get_conn()
    groups = conn.get_all_security_groups(['fae_sg'])
    assert groups, 'security group does not exist yet.'
    print '  syncing security group, creating it'
    sg = groups[0]
    return _sg_update(sg, conn)

def sg_create(conn=None, force=False):
    """ http://boto.readthedocs.org/en/latest/security_groups.html """
    print 'creating security group'
    conn = conn or _get_conn()
    groups = conn.get_all_security_groups(['fae_sg'])
    if groups and force:
        print '  fae sg already exists, deleting it and rebuilding'
        groups[0].delete()
    if groups and not force:
        print '  fae sg already exists, updating it'
        sg = groups[0]
    else:
        print '  fae sg doesnt exist, creating it'
        sg = conn.create_security_group('fae_sg', 'Free Album Engine')
    _sg_update(sg, conn)
    for x in sg.rules:
        print '  rule:', x
