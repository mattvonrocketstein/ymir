# -*- coding: utf-8 -*-
""" ymir._ansible

    Defines a ansible mixin for the base ymir service service class
"""

import json


class AnsibleMixin(object):
    """ """

    def ansible_inventory(self):
        """ """
        data = self.template_data()
        print json.dumps({data['name']: data['host']})
