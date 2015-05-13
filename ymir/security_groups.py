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


def sg_sync(name=None, description=None, rules=[], conn=None, force=False):
    """ http://boto.readthedocs.org/en/latest/security_groups.html """
    logger.debug("Synchronizing security group: {0} -- {1}".format(
        name, description))
    assert rules
    assert name
    if not description:
        description = sg_name
    conn = conn or get_conn()
    try:
        sg = conn.create_security_group(name, description)
    except boto.exception.EC2ResponseError:
        logger.debug('error creating security, maybe it already exists?')
        groups = conn.get_all_security_groups([name])
        if not groups:
            raise
        sg = groups[0]
    for r in rules:
        try:
            sg.authorize(*r)
        except boto.exception.EC2ResponseError:
            logger.warning("could not set rule (maybe dupe): {0}".format(r))
        else:
            logger.debug("set new rule: {0}".format(r))
    for x in sg.rules:
        print ('  rule: {0}'.format(x))
