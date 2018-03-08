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

from copy import deepcopy
import os

import json
from mock import Mock
from pprint import pprint as pp
import pytest

from f5_cccl.resource.ltm.policy import IcrPolicy
from f5_cccl.resource.ltm.policy import Policy


@pytest.fixture
def bigip():
    bigip = Mock()
    return bigip


@pytest.fixture
def icr_policy_dict():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    policy_file = os.path.join(current_dir, "bigip_policy.json")
    with open(policy_file, "r") as fp:
        json_data = fp.read()

    return json.loads(json_data)


@pytest.fixture
def api_policy():
    test_policy = {
        'name': "wrapper_policy",
        'strategy': "/Common/first-match",
        'rules': [{
            'name': "my_rule1",
            'actions': [{
                'pool': "/Test/pool1",
                'forward': True,
                'request': True
            }],
            'conditions': [{
                "httpHeader": True,
                "contains": True,
                "tmName": "X-Header",
                "values": ["openstack", "velcro"]
            }]
        },
        {
            'name': "my_rule2",
            'actions': [{'reset': True, 'forward': True}],
            'conditions': []
        }]
    }

    return Policy(partition="Test", **test_policy)


@pytest.fixture
def policy_0():
    data = {
        'name': "my_policy",
        'partition': "Test",
        'strategy': "/Common/first-match",
        'rules': []
    }
    return Policy(**data)


def test_create_policy():
    data = {
        'name': "my_policy",
        'partition': "Test",
        'strategy': "/Common/first-match",
        'rules': []
    }
    policy = Policy(**data)

    assert policy.name == "my_policy"
    assert policy.partition == "Test"

    assert policy.data.get('strategy') == "/Common/first-match"
    assert len(policy.data.get('rules')) == 0
    assert policy.data.get('legacy')
    assert policy.data.get('controls') == ["forwarding"]
    assert policy.data.get('requires') == ["http"]

    rules = {'name': "test_rule",
             'actions': [],
             'conditions': []}
    data['rules'].append(rules)

    policy = Policy(**data)
    assert policy.name == "my_policy"
    assert policy.partition == "Test"

    assert policy.data.get('strategy') == "/Common/first-match"
    assert len(policy.data.get('rules')) == 1
    assert policy.data.get('legacy')
    assert policy.data.get('controls') == ["forwarding"]
    assert policy.data.get('requires') == ["http"]


def test_uri_path(bigip, policy_0):
    assert (policy_0._uri_path(bigip) ==
            bigip.tm.ltm.policys.policy)


def test_compare_policy(policy_0):

    policy_1 = deepcopy(policy_0)

    assert policy_0 == policy_1

    rules = {'name': "test_rule",
             'actions': [],
             'conditions': []}
    policy_0.data['rules'].append(rules)

    assert policy_0 != policy_1

    rules = {'name': "prod_rule",
             'actions': [],
             'conditions': []}
    policy_1.data['rules'].append(rules)

    assert policy_0 != policy_1

    policy_2 = deepcopy(policy_0)
    assert policy_0 == policy_2

    policy_2.data['name'] = "your_policy"
    assert not policy_0 == policy_2

def test_compare_policy_w_dict(policy_0):
    data = {
        'name': "my_policy",
        'partition': "Test",
        'strategy': "/Common/first-match",
        'rules': []
    }
    assert policy_0 != data


def test_tostring(policy_0):
    assert str(policy_0) != ""


def test_create_policy_from_bigip(icr_policy_dict):
    policy = IcrPolicy(**icr_policy_dict)

    assert policy.name == "wrapper_policy"
    assert policy.partition == "Test"

    data = policy.data
    assert data.get('strategy') == "/Common/first-match"
    assert len(data.get('rules')) == 2
    assert data.get('legacy')
    assert data.get('controls') == ["forwarding"]
    assert data.get('requires') == ["http"]


def test_compare_icr_to_api_policy(icr_policy_dict, api_policy):
    icr_policy = IcrPolicy(**icr_policy_dict)
    assert icr_policy == api_policy
