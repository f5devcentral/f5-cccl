#!/usr/bin/env python
# Copyright (c) 2017,2018, F5 Networks, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from f5_cccl.resource.ltm.policy import Condition
from mock import Mock
import pytest


conditions = {
    'http_host': {
        'httpHost': True,
        'host': True,
        'equals': True,
        'values': ["www.my-site.com", "www.your-site.com"],
    },
    'http_uri': {
        'httpUri': True,
        'host': True,
        'equals': True,
        'values': ["bar.com", "foo.com"],
    },
    'http_uri_path': {
        'httpUri': True,
        'path': True,
        'not': True,
        'equals': True,
        'values': ["/", "/home.htm"]
    },
    'http_uri_path_segment': {
        'httpUri': True,
        'pathSegment': True,
        'index': 2,
        'startsWith': True,
        'values': ["articles"],
    },
    'http_uri_extension': {
        'httpUri': True,
        'extension': True,
        'startsWith': True,
        'values': ["htm"]
    },
    'http_uri_unsupported': {
        'httpUri': True,
        'queryString': True,
        'equals': True,
        'values': ["expandSubcollections=true"]
    },
    'http_unsupported_operand_type': {
        'httpMethod': True,
        'equals': True,
        'values': ["GET"]
    },
    'http_cookie': {
        'httpCookie': True,
        'tmName': "Cookie",
        'contains': True,
        'values': ["sessionToken=abc123"]
    },
    'http_header': {
        'httpHeader': True,
        'tmName': "Host",
        'contains': True,
        'values': ["www.acme.com"]
    },
    'tcp_address': {
        'tcp': True,
        'address': True,
        'matches': True,
        'values': ["10.10.10.10/32", "10.0.0.0/16"]
    }
}


@pytest.fixture
def bigip():
    bigip = Mock()
    return bigip


def test_create_http_host_match():
    name="0"
    condition = Condition(name, conditions['http_host'])
    data = condition.data

    assert condition.name == "0"
    assert not condition.partition
    assert data.get('httpHost')
    assert data.get('host')
    assert data.get('equals')
    assert data.get('values') == ["www.my-site.com",
                                  "www.your-site.com"]

    assert not data.get('startsWith')
    assert not data.get('endsWith')
    assert not data.get('contains')

    assert 'httpUri' not in data
    assert 'httpCookie' not in data
    assert 'httpHeader' not in data

    assert not data.get('index')
    assert not data.get('path')
    assert not data.get('pathSegment')
    assert not data.get('extension')
    assert not data.get('httpCookie')
    assert not data.get('httpHeader')
    assert not data.get('tmName')


def test_create_http_uri_match():
    name="0"
    condition = Condition(name, conditions['http_uri'])
    data = condition.data

    assert condition.name == "0"
    assert not condition.partition
    assert data.get('httpUri')
    assert data.get('host')
    assert data.get('equals')
    assert data.get('values') == ["bar.com", "foo.com"]

    assert not data.get('startsWith')
    assert not data.get('endsWith')
    assert not data.get('contains')

    assert 'httpHost' not in data
    assert 'httpCookie' not in data
    assert 'httpHeader' not in data

    assert not data.get('index')
    assert not data.get('path')
    assert not data.get('pathSegment')
    assert not data.get('extension')
    assert not data.get('httpCookie')
    assert not data.get('httpHeader')
    assert not data.get('tmName')


def test_create_http_uri_path_match():
    name="0"
    condition = Condition(name, conditions['http_uri_path'])
    data = condition.data

    assert condition.name == "0"
    assert not condition.partition

    assert data.get('httpUri')
    assert data.get('path')
    assert data.get('values') == ["/", "/home.htm"]

    assert 'httpHost' not in data
    assert 'httpCookie' not in data
    assert 'httpHeader' not in data

    assert data.get('equals')
    assert not data.get('startsWith')
    assert not data.get('endsWith')
    assert not data.get('contains')

    assert not data.get('missing')
    assert data.get('not')
    assert not data.get('caseSensitive')

    assert not data.get('index')
    assert not data.get('pathSegment')
    assert not data.get('extension')
    assert not data.get('httpCookie')
    assert not data.get('httpHeader')
    assert not data.get('tmName')


def test_create_http_uri_unsupported_match():
    name="0"

    with pytest.raises(ValueError):
        Condition(name, conditions['http_uri_unsupported'])


def test_create_http_unsupported_operand_type():
    name="0"
    with pytest.raises(ValueError):
        Condition(name, conditions['http_unsupported_operand_type'])


def test_create_http_uri_path_segment_match():
    name="0"
    condition = Condition(name, conditions['http_uri_path_segment'])
    data = condition.data

    assert condition.name == "0"
    assert not condition.partition

    assert data.get('httpUri')
    assert data.get('pathSegment')
    assert data.get('values') == ["articles"]
    assert data.get('index') == 2

    assert 'httpHost' not in data
    assert 'httpCookie' not in data
    assert 'httpHeader' not in data

    assert not data.get('equals')
    assert data.get('startsWith')
    assert not data.get('endsWith')
    assert not data.get('contains')

    assert not data.get('missing')
    assert not data.get('not')
    assert not data.get('caseSensitive')

    assert not data.get('path')
    assert not data.get('extension')
    assert not data.get('httpCookie')
    assert not data.get('httpHeader')
    assert not data.get('tmName')


def test_create_http_uri_extension_match():
    name="0"
    condition = Condition(name, conditions['http_uri_extension'])
    data = condition.data

    assert condition.name == "0"
    assert not condition.partition

    assert data.get('httpUri')
    assert data.get('extension')
    assert data.get('values') == ["htm"]

    assert 'httpHost' not in data
    assert 'httpCookie' not in data
    assert 'httpHeader' not in data

    assert not data.get('equals')
    assert data.get('startsWith')
    assert not data.get('endsWith')
    assert not data.get('contains')

    assert not data.get('missing')
    assert not data.get('not')
    assert not data.get('caseSensitive')

    assert not data.get('index')
    assert not data.get('path')
    assert not data.get('pathSegment')
    assert not data.get('httpCookie')
    assert not data.get('httpHeader')
    assert not data.get('tmName')


def test_create_http_cookie_match():
    name="0"
    condition = Condition(name, conditions['http_cookie'])
    data = condition.data

    assert condition.name == "0"
    assert not condition.partition

    assert data.get('httpCookie')
    assert data.get('tmName') == "Cookie"
    assert data.get('values') == ["sessionToken=abc123"]

    assert 'httpHost' not in data
    assert 'httpUri' not in data
    assert 'httpHeader' not in data

    assert not data.get('equals')
    assert not data.get('startsWith')
    assert not data.get('endsWith')
    assert data.get('contains')

    assert not data.get('missing')
    assert not data.get('not')
    assert not data.get('caseSensitive')

    assert not data.get('index')
    assert not data.get('path')
    assert not data.get('pathSegment')


def test_create_http_header_match():
    name="0"
    condition = Condition(name, conditions['http_header'])
    data = condition.data

    assert condition.name == "0"
    assert not condition.partition

    assert data.get('httpHeader')
    assert data.get('tmName') == "Host"
    assert data.get('values') == ["www.acme.com"]

    assert 'httpHost' not in data
    assert 'httpUri' not in data
    assert 'httpCookie' not in data

    assert not data.get('equals')
    assert not data.get('startsWith')
    assert not data.get('endsWith')
    assert data.get('contains')

    assert not data.get('missing')
    assert not data.get('not')
    assert not data.get('caseSensitive')

    assert not data.get('index')
    assert not data.get('path')
    assert not data.get('pathSegment')


def test_equal_conditions():
    name="0"
    condition_1 = Condition(name, conditions['http_host'])
    condition_2 = Condition(name, conditions['http_host'])

    assert id(condition_1) != id(condition_2)
    assert condition_1 == condition_2

    condition_1.data['values'].pop()

    assert not condition_1 == condition_2
    assert condition_1 != condition_2

    fake_condition = {
        "httpHost": False,
        "values": ["www.my-site.com"]
    }

    assert condition_1 != fake_condition
    assert condition_1 != conditions['http_uri_path']


def test_str_condition():
    name="0"
    condition = Condition(name, conditions['http_host'])

    assert str(condition)


def test_uri_path(bigip):
    name="0"
    condition = Condition(name, conditions['http_host'])

    with pytest.raises(NotImplementedError):
        condition._uri_path(bigip)


def test_create_tcp_address_match():
    name="0"
    condition = Condition(name, conditions['tcp_address'])
    data = condition.data

    assert condition.name == "0"
    assert not condition.partition

    assert data.get('tcp')
    assert data.get('values') == ["10.0.0.0/16", "10.10.10.10/32"]

    assert 'httpHost' not in data
    assert 'httpUri' not in data
    assert 'httpCookie' not in data

    assert not data.get('equals')
    assert not data.get('startsWith')
    assert not data.get('endsWith')
    assert data.get('matches')

    assert not data.get('missing')
    assert not data.get('not')
    assert not data.get('caseSensitive')

    assert not data.get('index')
    assert not data.get('path')
    assert not data.get('pathSegment')
