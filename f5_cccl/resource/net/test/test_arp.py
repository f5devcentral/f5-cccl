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

from copy import copy
from f5_cccl.resource.net.arp import Arp
from mock import Mock
import pytest


cfg_test = {
    'name': '1.2.3.4',
    'partition': 'test_partition',
    'ipAddress': '1.2.3.4',
    'macAddress': '12:ab:34:cd:56:ef'
}


@pytest.fixture
def bigip():
    bigip = Mock()
    return bigip


def test_create_arp():
    """Test Arp creation."""
    arp = Arp(**cfg_test)
    assert Arp

    # verify cfg items
    for k, v in cfg_test.items():
        assert arp.data[k] == v


def test_eq():
    """Test Arp equality."""
    arp1 = Arp(**cfg_test)
    arp2 = Arp(**cfg_test)
    assert arp1
    assert arp2
    assert arp1 == arp2

    # name not equal
    cfg_changed = copy(cfg_test)
    cfg_changed['name'] = '4.3.2.1'
    arp2 = Arp(**cfg_changed)
    assert arp1 != arp2

    # partition not equal
    cfg_changed = copy(cfg_test)
    cfg_changed['partition'] = 'other'
    arp2 = Arp(**cfg_changed)
    assert arp1 != arp2

    # ipAddress not equal
    cfg_changed = copy(cfg_test)
    cfg_changed['ipAddress'] = '4.3.2.1'
    arp2 = Arp(**cfg_changed)
    assert arp1 != arp2

    # macAddress not equal
    cfg_changed = copy(cfg_test)
    cfg_changed['macAddress'] = '98:ab:76:cd:54:ef'
    arp2 = Arp(**cfg_changed)
    assert arp1 != arp2


def test_hash():
    """Test Arp hash."""
    arp1 = Arp(**cfg_test)
    arp2 = Arp(**cfg_test)

    cfg_changed = copy(cfg_test)
    cfg_changed['name'] = '4.3.2.1'
    arp3 = Arp(**cfg_changed)

    cfg_changed = copy(cfg_test)
    cfg_changed['partition'] = 'other'
    arp4 = Arp(**cfg_changed)

    assert arp1
    assert arp2
    assert arp3
    assert arp4

    assert hash(arp1) == hash(arp2)
    assert hash(arp1) != hash(arp3)
    assert hash(arp1) != hash(arp4)


def test_uri_path(bigip):
    """Test Arp URI."""
    arp = Arp(**cfg_test)
    assert arp._uri_path(bigip) == bigip.tm.net.arps.arp
