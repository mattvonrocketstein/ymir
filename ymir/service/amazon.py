# -*- coding: utf-8 -*-
""" ymir.service.amazon
"""
import os
import time
import boto

from fabric.colors import yellow

from ymir import util
from ymir.service.base import AbstractService


class AmazonService(AbstractService):
    """ """

    def __init__(self, conn=None, **kargs):
        """"""
        self.conn = conn or util.get_conn()
        super(AmazonService, self).__init__(**kargs)

    def _get_instance(self, strict=False):
        """ """
        conn = self.conn
        name = self.template_data()['name']
        i = util.get_instance_by_name(name, conn)
        if strict and i is None:
            err = "Could not acquire instance! Is the name '{0}' correct?"
            err = err.format(name)
            self.report(err)
            raise SystemExit(1)
        return i

    def setup_ip(self):
        """ """
        self.sync_tags()
        self.sync_buckets()
        self.sync_eips()
        super(AmazonService, self).setup_ip()

    @util.declare_operation
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
        return util.unexpand(self._service_json['pem'])

    @util.declare_operation
    def sync_buckets(self, quiet=False):
        report = self.report if not quiet else util.NOOP
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

    @util.declare_operation
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

    @util.declare_operation
    @util.require_running_instance
    def sync_tags(self):
        """ update aws instance tags from service.json `tags` field """
        self.report('updating instance tags: ')
        json = self.template_data()
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

    @util.declare_operation
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

    @util.declare_operation
    @util.require_running_instance
    def mosh(self):
        """ connect to this service with mosh """
        self.report('connecting with mosh')
        service_data = self.template_data()
        util.mosh(self.status()['ip'],
                  username=self._username,
                  pem=service_data['pem'])

    ssh = util.require_running_instance(AbstractService.ssh)

    def _status(self):
        """ retrieves service status information.
            use this instead of self.status() if you want to quietly
            retrieve information for use without actually displaying it
        """
        tdata = self._service_json  # NOT template_data(), that's cyclic
        if not self._status_computed and self._debug_mode:
            self.report("AWS profile: {0}".format(yellow(
                os.environ.get('AWS_PROFILE', 'default'))))
        name = tdata['name']
        instance = util.get_instance_by_name(name, self.conn)
        result = dict(
            instance=None, ip=None,
            private_ip=None, tags=[],
            status='terminated?',)
        if instance:
            result.update(
                dict(
                    instance=instance,
                    tags=instance.tags,
                    status=instance.update(),
                    ip=instance.ip_address,
                    private_ip=instance.private_ip_address,
                ))
        self._status_computed = result
        return result

    @util.declare_operation
    def create(self, force=False):
        """ create new instance of this service ('force' defaults to False)"""
        self.report('creating ec2 instance', section=True)
        conn = self.conn
        i = self._get_instance()
        if i is not None:
            msg = '  instance already exists: {0} ({1})'
            msg = msg.format(i, i.update())
            self.report(msg)
            if force:
                self.report('  force is True, terminating it & rebuilding')
                util._block_while_terminating(i, conn)
                # might need to block and wait here
                return self.create(force=False)
            self.report('  force is False, refusing to rebuild it')
            return

        service_data = self.template_data()
        # HACK: deal with unfortunate vpc vs. ec2-classic differences
        reservation_extras = service_data.get('reservation_extras', {}).copy()

        # set security group stuff in reservation extras
        sg_names = service_data['security_groups']
        if not sg_names:
            err = ('without `security_groups` in service.json, '
                   'cannot create instance reservation')
            raise SystemExit(err)
        self.report(
            "service description uses {0} as a security groups".format(sg_names))
        tmp = {}
        sgs = dict([[sg.id, sg.name] for sg in conn.get_all_security_groups()])
        for sg_name in sg_names:
            if sg_name not in sgs.values():
                err = "could not find {0} amongst security groups at {1}"
                err = err.format(sg_names, sgs.values())
                raise SystemExit(err)
            else:
                _id = [_id for _id in sgs if sgs[_id] == sg_name][0]
                self.report("  sg '{0}' is id {1}".format(sgs[_id], _id))
                tmp[_id] = sgs[_id]
        reservation_extras['security_group_ids'] = tmp.keys()

        reservation = conn.run_instances(
            image_id=service_data['ami'],
            key_name=service_data['key_name'],
            instance_type=service_data['instance_type'],
            **reservation_extras)

        instance = reservation.instances[0]
        self.report('  no instance found, creating it now.')
        self.report('  reservation-id:', instance.id)

        util._block_while_pending(instance)
        status = instance.update()
        name = self.template_data()['name']
        if status == 'running':
            self.report('  instance is running.')
            self.report('  setting tag for "Name": {0}'.format(
                name))
            instance.add_tag("Name", name)
        else:
            self.report('Weird instance status: ', status)
            return None

        time.sleep(5)
        self.report("Finished with creation.  Now run `fab setup`")

    @util.declare_operation
    def shell(self):
        """ """
        return util.shell(
            conn=self.conn,
            Service=self, service=self)
