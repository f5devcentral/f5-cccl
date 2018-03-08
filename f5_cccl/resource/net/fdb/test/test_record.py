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
from f5_cccl.resource.net.fdb.record import Record
from mock import Mock
import pytest


cfg_test = {
    'name':'12:ab:34:cd:56:ef', 
    'default_route_domain': 2,
    'endpoint':'1.2.3.4'
}

@pytest.fixture
def bigip():
    bigip = Mock()
    return bigip


def test_create_record():
    """Test Record creation."""
    record = Record(**cfg_test)
    assert Record
    assert record.name == '12:ab:34:cd:56:ef'
    assert record.data['endpoint'] == '1.2.3.4%2' 


def test_eq():
    """Test Record equality."""
    record1 = Record(**cfg_test)
    record2 = Record(**cfg_test)
    assert record1 == record2

    # name not equal
    cfg_changed = copy(cfg_test)
    cfg_changed['name'] = '98:ab:76:cd:54:ef'
    record2 = Record(**cfg_changed)
    assert record1 != record2

    # endpoint not equal
    cfg_changed = copy(cfg_test)
    cfg_changed['endpoint'] = '4.3.2.1'
    record2 = Record(**cfg_changed)
    assert record1 != record2


def test_uri_path(bigip):
    """Test Record URI."""
    record = Record(**cfg_test)

    with pytest.raises(NotImplementedError):
        record._uri_path(bigip)
