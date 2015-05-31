""" ymir.validation
"""
import os
import logging

from fabric.api import (local, quiet,)
from boto.exception import EC2ResponseError

from ymir import checks
from ymir import util
logger = logging.getLogger(__name__)


class ValidationMixin(object):
    def _validate_named_sgs(self):
        """ validation for security groups.
            NB: this requires AWS credentials
        """
        errs = []
        sgs = [x for x in self.SECURITY_GROUPS if isinstance(x, basestring)]
        try:
            self.conn.get_all_security_groups(sgs)
        except EC2ResponseError:
            errs.append("could not find security groups: "\
                   + str(self.SECURITY_GROUPS))
        #for x in set(self.SECURITY_GROUPS)-set(sgs):
        #    errs.append('sg entry {0} is complex, ignoring it'.format(
        #        x.get('name')))
        return errs

    def _validate_health_checks(self):
        errs = []
        # fake the host value just for validation because we don't know
        # whether this service has been bootstrapped or not
        service_json = self._template_data(simple=True)
        service_json.update(host='host_name')
        errs = []
        for check_name in service_json['health_checks']:
            check_type, url = service_json['health_checks'][check_name]
            try:
                checker = getattr(checks, check_type)
            except AttributeError:
                err = '  check-type "{0}" does not exist in ymir.checks'
                err = err.format(check_type)
                errs.append(err)
            tmp = service_json.copy()
            tmp.update(dict(host='host'))
            try:
                url = url.format(**service_json)
            except KeyError, exc:
                msg = 'url "{0}" could not be formatted: missing {1}'
                msg = msg.format(url, str(exc))
                errs.append(msg)
            else:
                checker_validator = getattr(
                    checker, 'validate', lambda url: None)
                err = checker_validator(url)
                if err: errs.append(err)
        return errs

    def _validate_puppet(self, recurse=False):
        """ when recurse==True,
              all puppet under SERVICE_ROOT/puppet will be checked

            otherwise,
              only validate the files mentioned in SETUP_LIST / PROVISION_LIST
        """
        errs = []
        pdir = os.path.join(self.SERVICE_ROOT, 'puppet')
        if not os.path.exists(pdir):
            msg = 'puppet directory does not exist @ {0}'
            msg = msg.format(pdir)
            errs.append(msg)
        else:
            with quiet():
                result = local('find {0}|grep .pp$'.format(pdir), capture=True)
                for filename in result.split('\n'):
                    logger.debug("validating {0}".format(filename))
                    result = local('puppet parser validate {0}'.format(
                        filename), capture=True)
                    error = result.return_code!=0
                    if error:
                        errs.append('{0}'.format(filename))
        return errs

    def _validate_keypairs(self):
        errors = []
        if not os.path.exists(os.path.expanduser(self.PEM)):
            errors.append('  ERROR: pem file is not present: ' + self.PEM)
        keys = [k.name for k in util.get_conn().get_all_key_pairs()]
        if self.KEY_NAME not in keys:
            errors.append('  ERROR: aws keypair not found: ' + self.KEY_NAME)
        return errors
