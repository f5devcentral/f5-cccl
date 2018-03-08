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

from copy import copy
from f5_cccl.resource.ltm.irule import IRule
from mock import Mock
import pytest


ssl_redirect_irule_1 = """
    when HTTP_REQUEST {
        HTTP::redirect https://[getfield [HTTP::host] \":\" 1][HTTP::uri]
    }
    """

cfg_test = {
    'name': 'ssl_redirect',
    'partition': 'my_partition',
    'apiAnonymous': ssl_redirect_irule_1
}

class FakeObj: pass


@pytest.fixture
def bigip():
    bigip = Mock()
    return bigip


def test_create_irule():
    """Test iRule creation."""
    irule = IRule(
        **cfg_test
    )
    assert irule

    # verify all cfg items
    for k,v in cfg_test.items():
        assert irule.data[k] == v.strip()


def test_hash():
    """Test Node Server hash."""
    irule1 = IRule(
        **cfg_test
    )
    irule2 = IRule(
        **cfg_test
    )
    cfg_changed = copy(cfg_test)
    cfg_changed['name'] = 'test'
    irule3 = IRule(
        **cfg_changed
    )
    cfg_changed = copy(cfg_test)
    cfg_changed['partition'] = 'other'
    irule4 = IRule(
        **cfg_changed
    )
    assert irule1
    assert irule2
    assert irule3
    assert irule4

    assert hash(irule1) == hash(irule2)
    assert hash(irule1) != hash(irule3)
    assert hash(irule1) != hash(irule4)


def test_eq():
    """Test iRule equality."""
    partition = 'Common'
    name = 'irule_1'

    irule1 = IRule(
        **cfg_test
    )
    irule2 = IRule(
        **cfg_test
    )
    assert irule1
    assert irule2
    assert irule1 == irule2

    # name not equal
    cfg_changed = copy(cfg_test)
    cfg_changed['name'] = 'ssl_redirect_2'
    irule2 = IRule(**cfg_changed)
    assert irule1 != irule2

    # partition not equal
    cfg_changed = copy(cfg_test)
    cfg_changed['partition'] = 'test'
    irule2 = IRule(**cfg_changed)
    assert irule1 != irule2

    # the actual rule code not equal
    cfg_changed = copy(cfg_test)
    cfg_changed['apiAnonymous'] = None
    irule2 = IRule(**cfg_changed)
    assert irule1 != irule2

    # different objects
    fake = FakeObj
    assert irule1 != fake 

    # should be equal after assignment
    irule2 = irule1
    assert irule1 == irule2


def test_uri_path(bigip):
    """Test iRule URI."""
    irule = IRule(
        **cfg_test
    )
    assert irule

    assert irule._uri_path(bigip) == bigip.tm.ltm.rules.rule


def test_whitespace():
    """Verify that leading/trailing whitespace is removed from iRule."""
    whitespace = '\n\t   '
    ssl_redirect_irule_ws = whitespace + ssl_redirect_irule_1 + whitespace

    cfg_ws = {
        'name': 'ssl_redirect',
        'partition': 'my_partition',
        'apiAnonymous': ssl_redirect_irule_ws
    }

    irule = IRule(
        **cfg_ws
    )

    assert irule
    assert irule.data['apiAnonymous'] == ssl_redirect_irule_1.strip()
