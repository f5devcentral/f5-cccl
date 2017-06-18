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

from f5_cccl.resource.ltm.policy import Action
from mock import Mock
import pytest


@pytest.fixture
def bigip():
    bigip = Mock()
    return bigip


actions = {
    'redirect': {
	"request": True,
	"redirect": True,
	"location": "http://boulder-dev.f5.com",
	"httpReply": True
    },
    'pool_forward': {
	"request": True,
	"forward": True,
	"pool": "/Test/my_pool"
    },
    'reset': {
	"request": True,
	"forward": True,
	"reset": True
    },
    'invalid_action': {
        "request": False,
        "forward": False,
        "pool": None,
        "location": None,
        "reset": False,
        "redirect": False
    }
}


def test_create_redirect_action():
    name="0"
    action = Action(name, actions['redirect'])
    data = action.data

    assert action.name == "0"
    assert not action.partition
    assert data.get('request')
    assert not data.get('forward')
    assert not data.get('pool')
    assert data.get('redirect')
    assert data.get('location') == "http://boulder-dev.f5.com"
    assert not data.get('reset')


def test_create_pool_forwarding_action():
    name="0"
    action = Action(name, actions['pool_forward'])
    data = action.data

    assert action.name == "0"
    assert not action.partition
    assert data.get('request')
    assert data.get('forward')
    assert data.get('pool') == "/Test/my_pool"
    assert not data.get('redirect')
    assert not data.get('location')
    assert not data.get('reset')


def test_create_reset_action():
    name="0"
    action = Action(name, actions['reset'])
    data = action.data

    assert action.name == "0"
    assert not action.partition
    assert data.get('request')
    assert data.get('forward')
    assert not data.get('pool')
    assert not data.get('redirect')
    assert not data.get('location')
    assert data.get('reset')


def test_create_invalid_action():
    name="0"
    action = Action(name, actions['invalid_action'])
    data = action.data

    assert action.name == "0"
    assert not action.partition
    assert data.get('request')
    assert not data.get('forward', True)
    assert not data.get('pool', "test_pool")
    assert not data.get('redirect', True)
    assert not data.get('location', "test_uri")
    assert not data.get('reset', True)


def test_equal_actions():
    name="0"
    action_redirect_1 = Action(name, actions['redirect'])
    action_redirect_2 = Action(name, actions['redirect'])

    assert id(action_redirect_1) != id(action_redirect_2)
    assert action_redirect_1 == action_redirect_2

    action_redirect_1.data['location'] = "http://sea-dev.f5.com"
    assert not action_redirect_1 == action_redirect_2
    assert action_redirect_1 != action_redirect_2

    fake_action = {
        "request": False,
        "forward": False,
        "pool": None,
        "location": None,
        "reset": False,
        "redirect": False
    }

    assert action_redirect_1 != fake_action
    assert action_redirect_1 != actions['redirect']


def test_str_action():
    name="0"
    action = Action(name, actions['redirect'])

    assert str(action)


def test_uri_path(bigip):
    name="0"
    action = Action(name, actions['redirect'])

    with pytest.raises(NotImplementedError):
        action._uri_path(bigip)
