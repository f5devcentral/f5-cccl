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
from f5_cccl.resource.ltm.virtual import VirtualServer
from f5_cccl.resource.ltm.pool import Pool
from mock import Mock
import pytest


cfg_test = {
    'name': 'Virtual-1',
    'partition': 'my_partition',
    'destination': '1.2.3.4',
    'servicePort': 80,
    'pool': '/my_partition/pool1',
    'ipProtocol': 'tcp'
}


@pytest.fixture
def bigip():
    bigip = Mock()
    return bigip


def test_create_virtual():
    """Test Virtual Server creation."""
    virtual = VirtualServer(
        **cfg_test
    )
    assert virtual

    # verify all cfg items
    for k,v in cfg_test.items():
        assert virtual.data[k] == v


def test_hash():
    """Test Virtual Server hash."""
    virtual = VirtualServer(
        **cfg_test
    )
    virtual1 = VirtualServer(
        **cfg_test
    )
    cfg_changed = copy(cfg_test)
    cfg_changed['name'] = 'test'
    virtual2 = VirtualServer(
        **cfg_changed
    )
    cfg_changed = copy(cfg_test)
    cfg_changed['partition'] = 'other'
    virtual3 = VirtualServer(
        **cfg_changed
    )
    assert virtual
    assert virtual1
    assert virtual2
    assert virtual3

    assert hash(virtual) == hash(virtual1)
    assert hash(virtual) != hash(virtual2)
    assert hash(virtual) != hash(virtual3)


def test_eq():
    """Test Virtual Server equality."""
    partition = 'Common'
    name = 'virtual_1'

    virtual = VirtualServer(
        **cfg_test
    )
    virtual2 = VirtualServer(
        **cfg_test
    )
    pool = Pool(
        name=name,
        partition=partition
    )
    assert virtual
    assert virtual2
    assert virtual == virtual2

    # not equal
    virtual2.data['servicePort'] = 8080
    assert virtual != virtual2

    # different objects
    with pytest.raises(ValueError):
        assert virtual != pool 


def test_uri_path(bigip):
    """Test Virtual Server URI."""
    virtual = VirtualServer(
        **cfg_test
    )
    assert virtual

    assert virtual._uri_path(bigip) == bigip.tm.ltm.virtuals.virtual
