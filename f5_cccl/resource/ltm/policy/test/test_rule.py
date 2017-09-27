#!/usr/bin/env python
# Copyright 2017 F5 Networks Inc.
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

from f5_cccl.resource.ltm.policy import Rule
from mock import Mock
import pytest


@pytest.fixture
def bigip():
    bigip = Mock()
    return bigip


action_0 = {
    "request": True,
    "redirect": True,
    "location": "http://boulder-dev.f5.com",
    "httpReply": True
}

action_1 = {
    "request": True,
    "redirect": True,
    "location": "http://seattle-dev.f5.com",
    "httpReply": True
}

action_2 = {
    "request": True,
    "forward": True,
    "virtual": "/Test/my_virtual"
}

condition_0 = {
    'httpUri': True,
    'pathSegment': True,
    'contains': True,
    'values': ["colorado"],
}

condition_1 = {
    'httpUri': True,
    'pathSegment': True,
    'contains': True,
    'values': ["washington"],
}

condition_2 = {
    'httpUri': True,
    'queryString': True,
    'contains': True,
    'values': ["washington"],
}

@pytest.fixture
def rule_0():
    data = {'ordinal': "0",
            'actions': [],
            'conditions': []}
    data['conditions'].append(condition_0)
    data['actions'].append(action_0)
    return Rule(name="rule_0", **data)


@pytest.fixture
def rule_0_clone():
    data = {'ordinal': "0",
            'actions': [],
            'conditions': []}
    data['conditions'].append(condition_0)
    data['actions'].append(action_0)
    return Rule(name="rule_0", **data)


@pytest.fixture
def rule_1():
    data = {'ordinal': "1",
            'actions': [],
            'conditions': []}
    data['conditions'].append(condition_1)
    data['actions'].append(action_1)
    return Rule(name="rule_1",  **data)


@pytest.fixture
def rule_no_actions():
    data = {'ordinal': "0",
            'actions': [],
            'conditions': []}
    data['conditions'].append(condition_0)
    return Rule(name="rule_0",  **data)


@pytest.fixture
def rule_no_conditions():
    data = {'ordinal': "0",
            'actions': [],
            'conditions': []}
    data['actions'].append(action_1)
    return Rule(name="rule_1",  **data)


def test_create_rule():
    data = {'ordinal': "0",
            'actions': [],
            'conditions': [],
            'description': 'This is a rule description'}

    rule = Rule(name="rule_0", **data)

    assert rule.name == "rule_0"
    assert len(rule.data['conditions']) == 0
    assert len(rule.data['actions']) == 0
    assert rule.data['description'] == 'This is a rule description'

    data['conditions'].append(condition_0)
    data['actions'].append(action_0)

    rule = Rule(name="rule_1", **data)
    assert len(rule.data['conditions']) == 1
    assert len(rule.data['actions']) == 1

    data['conditions'] = [condition_2]
    data['actions'] = [action_0]

    rule = Rule(name="rule_1", **data)
    assert len(rule.data['conditions']) == 0
    assert len(rule.data['actions']) == 1

    data['conditions'].append(condition_0)
    rule = Rule(name="rule_1", **data)
    assert len(rule.data['conditions']) == 1
    assert len(rule.data['actions']) == 1

    data['conditions'] = [condition_0]
    data['actions'] = [action_2]

    rule = Rule(name="rule_1", **data)
    assert len(rule.data['conditions']) == 1
    assert len(rule.data['actions']) == 0


def test_uri_path(bigip, rule_0):
    with pytest.raises(NotImplementedError):
        rule_0._uri_path(bigip)


def test_less_than(rule_0, rule_1):
    assert rule_0 < rule_1


def test_tostring(rule_0):
    assert str(rule_0) != ""


def test_compare_rules(rule_0, rule_0_clone, rule_1,
                       rule_no_actions, rule_no_conditions):

    assert rule_0 == rule_0_clone
    assert rule_0 != rule_1

    assert rule_0 != rule_no_actions
    assert rule_0 != rule_no_conditions

    fake_rule = {'ordinal': "0",
                 'actions': [],
                 'conditions': []}

    assert rule_0 != fake_rule

    rule_0_clone.data['actions'][0]['location'] = \
        "http://seattle-dev.f5.com"

    assert rule_0 != rule_0_clone
