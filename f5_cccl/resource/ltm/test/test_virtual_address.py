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

from copy import deepcopy
from mock import Mock
import pytest

from f5_cccl.resource.ltm.virtual_address import VirtualAddress

va_cfg = {
    "name": "192.168.100.100",
    "partition": "Test",
    "address": "192.168.100.100",
    "autoDelete": "true",
    "enabled": "yes",
    "description": "Test virutal address resource",
    "trafficGroup": "/Common/traffic-group-local-only"
}

@pytest.fixture
def bigip():
    bigip = Mock()
    return bigip


def test_create_virtual_address():
    va = VirtualAddress(**va_cfg)

    assert va

    assert va.name == "192.168.100.100"
    assert va.partition == "Test"

    data = va.data
    assert data['address'] == "192.168.100.100"
    assert data['autoDelete'] == "true"
    assert data['enabled'] == "yes"
    assert data['description'] == "Test virutal address resource"
    assert data['trafficGroup'] ==  "/Common/traffic-group-local-only"


def test_create_virtual_address_defaults():
    va = VirtualAddress(name="test_va", partition="Test")

    assert va

    assert va.name == "test_va"
    assert va.partition == "Test"

    data = va.data
    assert not data['address']
    assert data['autoDelete'] == "false"
    assert not data['enabled']
    assert not data['description']
    assert data['trafficGroup'] ==  "/Common/traffic-group-1"


def test_equals_virtual_address():
    va1 = VirtualAddress(**va_cfg)
    va2 = VirtualAddress(**va_cfg)
    va3 = deepcopy(va1)

    assert id(va1) != id(va2)
    assert va1 == va2

    assert id(va1) != id(va3)
    assert va1 == va3

    va3._data['address'] = "192.168.200.100"
    assert va1 != va3

    assert va1 != va_cfg


def test_get_uri_path(bigip):
    va = VirtualAddress(**va_cfg)

    assert (va._uri_path(bigip) ==
            bigip.tm.ltm.virtual_address_s.virtual_address)
