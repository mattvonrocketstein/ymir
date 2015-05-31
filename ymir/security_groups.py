""" ymir.security_groups

    Helpers for security groups.. not used currently
"""
import collections

import boto
import logging

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
        group = c.create_security_group(group_name, "A group for %s"%(group_name,))
    return group

def sg_sync(name=None, description=None, rules=[], conn=None, vpc=None, force=False):
    """ http://boto.readthedocs.org/en/latest/security_groups.html """
    logger.debug("Synchronizing security group: {0} -- {1}".format(
        name, description))
    assert rules
    assert name
    if not description:
        description = sg_name
    csg_kargs = {}
    conn = conn or get_conn()
    if vpc is not None:
        conn = boto.vpc.connect_to_region('us-east-1')
        csg_kargs['vpc_id'] = vpc
    sg = get_or_create_security_group(conn, name, description)
    #try:
    #    sg = conn.create_security_group(name, description, **csg_kargs)
    #except boto.exception.EC2ResponseError:
    #    logger.debug('error creating security, maybe it already exists?')
    #    groups = conn.get_all_security_groups([name])
    #    if not groups:
    #        raise
    #    sg = groups[0]
    for r in rules:
        try:
            sg.authorize(*r)
        except boto.exception.EC2ResponseError:
            logger.warning("could not set rule (maybe dupe): {0}".format(r))
        else:
            logger.debug("set new rule: {0}".format(r))
    for x in sg.rules:
        print ('  rule: {0}'.format(x))
    print 'created security group', sg.id
