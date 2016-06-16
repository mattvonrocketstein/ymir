# -*- coding: utf-8 -*-
"""
"""
import mock
import pytest
import requests

import tests.common as test_common


@test_common.mock_aws
def test_basic_templating():
    with test_common.demo_service() as ctx:
        uid = "08002798dcaa"
        ctx.rewrite_json(service_name=uid, name="{{service_name}}")
        service = ctx.get_service()
        tdata = service.template_data()
        err = 'templating inside json did not take effect'
        assert tdata['name'] == uid, err
        err = "classname for constructed service does not match templated json"
        assert service.__class__.__name__ == uid, err


@test_common.mock_aws
def test_templating_in_provision_list():
    with test_common.demo_service() as ctx:
        uid = "08002798dcaa"
        # {host} template var is derived JIT, but should not cause an error
        ctx.rewrite_json(name=uid, provision_list=[
                         "local://echo {{name}}, {{host}}"])
        tdata = ctx.get_service().template_data()
        err = 'templating inside provision_list did not take effect'
        assert uid in tdata['provision_list'][0]
        ctx.rewrite_json(provision_list=["local://{{bad_variable}} {{name}}"])
        with pytest.raises(Exception):
            # this should raise an exception, because {bad_variable} is
            # not a whitelisted JIT-variable like host/username/pem.
            # TODO: raise a more specific exception
            ctx.get_service().template_data()


@test_common.mock_aws
def test_templating_in_setup_list():
    with test_common.demo_service() as ctx:
        uid = "08002798dcaa"
        # {host} template var is derived JIT, but should not cause an error
        ctx.rewrite_json(name=uid, setup_list=[
                         "local://echo {{name}}, {{host}}"])
        tdata = ctx.get_service().template_data()
        err = 'templating inside setup_list did not take effect'
        assert uid in tdata['setup_list'][0]
        ctx.rewrite_json(setup_list=["local://{{bad_variable}} {{name}}"])
        with pytest.raises(Exception):
            # this should raise an exception, because {bad_variable} is
            # not a whitelisted JIT-variable like host/username/pem.
            # TODO: raise a more specific exception
            ctx.get_service().template_data()


@test_common.mock_aws
def test_templating_in_checks():
    pass
