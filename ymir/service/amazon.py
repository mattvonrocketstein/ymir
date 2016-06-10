# -*- coding: utf-8 -*-
""" ymir.service.amazon
"""

import copy
import boto

from ymir import util
from ymir.service.base import AbstractService
from ymir.util import NOOP


class AmazonService(AbstractService):
    """ """
    FABRIC_COMMANDS = copy.copy(AbstractService.FABRIC_COMMANDS) + \
        ['mosh', 's3', 'terminate',
         'sync_buckets', 'sync_eips', 'sync_tags', ]

    def __init__(self, conn=None, **kargs):
        """"""
        self.conn = conn or util.get_conn()
        super(AmazonService, self).__init__(**kargs)

    def setup_ip(self, ip):
        """ """
        self.sync_tags()
        self.sync_buckets()
        self.sync_eips()
        super(AmazonService, self).setup_ip(ip)

    def s3(self):
        """ show summary of s3 information for this service """
        buckets = self.sync_buckets(quiet=True).items()
        if not buckets:
            self.report("this service is not using S3 buckets")
        for bname, bucket in buckets:
            keys = [k for k in bucket]
            self.report("  {0} ({1} items) [{2}]".format(
                bname, len(keys), bucket.get_acl()))
            for key in keys:
                print ("  {0} (size {1}) [{2}]".format(
                    key.name, key.size, key.get_acl()))

    @property
    def _s3_conn(self):
        return boto.connect_s3()

    @property
    def _username(self):
        """ username data is accessible only as a property because
            it must overridden for i.e. vagrant-based services
        """
        return self._service_json['username']

    @property
    def _pem(self):
        """ pem-file is accessible only as a property because
            it must overridden for i.e. vagrant-based services
        """
        return self._service_json['pem']

    def sync_buckets(self, quiet=False):
        report = self.report if not quiet else NOOP
        buckets = self.template_data()['s3_buckets']
        report("synchronizing s3 buckets")
        if buckets:
            report('  buckets to create: {0}'.format(buckets))
        else:
            self.report("  no s3 buckets mentioned in service-definition")
        conn = self._s3_conn
        tmp = {}
        for name in buckets:
            report("  setting up s3 bucket: {0}".format(name))
            tmp[name] = conn.create_bucket(name, location=self.S3_LOCATION)
        return tmp

    def sync_eips(self, quiet=False):
        """ synchronizes elastic IPs with service.json data """
        report = self.report if not quiet else lambda *args, **kargs: None
        report("synchronizing elastic ip's")
        service_instance_id = self._status()['instance'].id
        eips = self.template_data()['elastic_ips']
        if not eips:
            report('  no elastic IPs mentioned in service-definition')
            return
        addresses = [x for x in self.conn.get_all_addresses()
                     if x.public_ip in eips]
        for aws_address in addresses:
            report(" Address: {0}".format(aws_address))
            if aws_address.instance_id is None:
                report("   -> currently unassigned.  "
                       "associating with this instance")
                aws_address.associate(instance_id=service_instance_id)
            elif aws_address.instance_id == service_instance_id:
                report("   -> already associated with this service")
            else:
                report("   -> assigned to another instance {0}! (that seems bad)".format(
                    aws_address.instance_id))
    sync_elastic_ips = sync_eips

    @util.require_running_instance
    def sync_tags(self):
        """ update aws instance tags from service.json `tags` field """
        self.report('updating instance tags: ')
        json = self.template_data(simple=True)
        tags = dict(
            description=json.get('service_description', ''),
            org=json.get('org_name', ''),
            app=json.get('app_name', ''),
            env=json.get("env_name", ''),
        )
        for tag in json.get('tags', []):
            tags[tag] = 'true'
        for tag in tags:
            if not tags[tag]:
                tags.pop(tag)
        self.report('  {0}'.format(tags.keys()))
        self._instance.add_tags(tags)

    @util.require_running_instance
    def terminate(self, force=False):
        """ terminate this service (delete from ec2) """
        instance = self._instance
        self.report("{0} slated for termination.".format(instance))
        if force:
            return self.conn.terminate_instances(
                instance_ids=[instance.id])
        else:
            msg = ("This will terminate the instance {0} ({1}) and can "
                   "involve data loss.  Are you sure? [y/n] ")
            answer = None
            name = self.template_data()['name']
            while answer not in ['y', 'n']:
                answer = raw_input(msg.format(instance, name))
            if answer == 'y':
                self.terminate(force=True)

    @util.require_running_instance
    def mosh(self):
        """ connect to this service with mosh """
        self.report('connecting with mosh')
        service_data = self.template_data()
        util.mosh(self.status()['ip'],
                  username=self._username,
                  pem=service_data['pem'])

    ssh = util.require_running_instance(AbstractService.ssh)
