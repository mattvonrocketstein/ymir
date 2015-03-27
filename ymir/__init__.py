""" ymir:

    this is a module containing utility functions/classes for working
    with EC2. A common interface for typical devops commands is created
    (create, setup, provision, etc) by leveraging a combination of fabric,
    boto, & puppet.

    TODO: support elastic IP's
"""
from ymir import loom
from .service import AbstractService
from .beanstalk import ElasticBeanstalkService

