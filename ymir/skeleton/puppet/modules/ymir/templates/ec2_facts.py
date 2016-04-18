#!/usr/bin/env python
# -*- coding: utf-8 -*-
import os
URL = 'http://169.254.169.254/latest/meta-data/public-ipv4'
facts = dict(
    ec2_public_ipv4=os.popen('curl {0}'.format(URL)).read().strip())
for fact_name, fact_val in facts.items():
    print '{0}={1}'.format(fact_name, fact_val)
