# -*- coding: utf-8 -*-
"""
"""
import mock
import pytest
import requests

from ymir import checks
from .common import mock_service


def test_invalid_check_type():
    check = checks.Check(
        name='doesnt_matter',
        check_type='doesnt-exist',
        url_t='',
    )
    with pytest.raises(checks.InvalidCheckType):
        check.run(mock_service())


@mock.patch('ymir.checks._get_request')
def test_timeouts(request_mock):
    request_mock.side_effect = requests.exceptions.ConnectionError('timed out')
    check = checks.Check(
        name='test-json',
        check_type='json_200',
        url_t='',)
    assert check.run(mock_service()).failed
    request_mock.side_effect = requests.exceptions.ReadTimeout("zooom")
    assert check.run(mock_service()).failed


@mock.patch('ymir.util.is_port_open')
def test_port_open(fake_is_port_open):
    fake_is_port_open.return_value = False
    check = checks.Check(
        name='test-port-open',
        check_type='port_open',
        url_t='',)
    assert check.run(mock_service()).failed


@mock.patch('ymir.checks._get_request')
def test_json(request_mock):
    response = mock.Mock()
    request_mock.return_value = response
    response.status_code = 200
    check = checks.Check(
        name='test-json',
        check_type='json_200',
        url_t='',)
    result = check.run(mock_service())
    assert result.success
    assert response.json.called
    response.status_code = 300
    assert check.run(mock_service()).failed
    response.status_code = 200
    response.json = mock.Mock(side_effect=Exception)
    assert check.run(mock_service()).failed


def _test_factory(status_code):
    @mock.patch('ymir.checks._get_request')
    def test_xxx(request_mock):
        response = mock.Mock()
        request_mock.return_value = response
        response.status_code = status_code + 125
        srv = mock_service()
        check = checks.Check(
            name='test-{0}'.format(status_code),
            check_type='http_{0}'.format(status_code),
            url_t='',)
        result = check.run(srv)
        assert not result.success
        response.status_code = status_code
        srv = mock_service()
        result = check.run(srv)
        assert result.success
    test_xxx.__name__ = "test_{0}".format(status_code)
    return test_xxx

test_301 = _test_factory(301)
test_401 = _test_factory(401)
test_403 = _test_factory(403)
test_200 = _test_factory(200)
