# -*- coding: utf-8 -*-
import os
import pytest
from ymir.schema import validators as v
from ymir import schema
from ymir import api as yapi
import tests.common as test_common

Invalid = v.Invalid


@test_common.mock_aws
def test_derived_schema(**extra_json_fields):
    with test_common.demo_service() as ctx:
        ctx.rewrite_json(
            name="original-service",
            org_name='original-org')
        service = ctx.get_service()
        efile = os.path.join(service._ymir_service_root, "extension.json")
        import json
        extension_data = dict(
            extends=service._ymir_service_json_file,
            name="extension-service")
        extension_data.update(extra_json_fields)
        with open(efile, 'w') as fhandle:
            fhandle.write(json.dumps(extension_data))
        ex_service = yapi.load_service_from_json(efile, die=False)
        assert ex_service.template_data()['name'] == extension_data['name']
        assert ex_service.template_data()['org_name'] == 'original-org'


def test_illegal_derived_schema():
    with pytest.raises(Exception):
        test_derived_schema(
            name="bad-extension-service",
            very_bad_field="field not allowed")
