#!/usr/bin/env python
# Copyright (c) 2017-2021 F5 Networks, Inc.
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
from f5_cccl.resource.ltm.internal_data_group import InternalDataGroup
from mock import Mock
import pytest


cfg_test = {
    'name': 'test_dg',
    'partition': 'my_partition',
    'type': 'string',
    'records': [
        {
            "name": "test_record_name",
            "data": "test record data"
        }
    ]
}

class FakeObj: pass


@pytest.fixture
def bigip():
    bigip = Mock()
    return bigip


def test_create_internal_data_group():
    """Test InternalDataGroup creation."""
    idg = InternalDataGroup(
        **cfg_test
    )
    assert idg

    # verify all cfg items
    for k,v in list(cfg_test.items()):
        assert idg.data[k] == v


def test_hash():
    """Test InternalDataGroup hash."""
    idg1 = InternalDataGroup(
        **cfg_test
    )
    idg2 = InternalDataGroup(
        **cfg_test
    )
    cfg_changed = deepcopy(cfg_test)
    cfg_changed['name'] = 'test'
    idg3 = InternalDataGroup(
        **cfg_changed
    )
    cfg_changed = deepcopy(cfg_test)
    cfg_changed['partition'] = 'other'
    idg4 = InternalDataGroup(
        **cfg_changed
    )

    assert idg1
    assert idg2
    assert idg3
    assert idg4

    assert hash(idg1) == hash(idg2)
    assert hash(idg1) != hash(idg3)
    assert hash(idg1) != hash(idg4)


def test_eq():
    """Test InternalDataGroup equality."""
    partition = 'Common'
    name = 'idg_1'

    idg1 = InternalDataGroup(
        **cfg_test
    )
    idg2 = InternalDataGroup(
        **cfg_test
    )
    assert idg1
    assert idg2
    assert idg1 == idg2

    # name not equal
    cfg_changed = deepcopy(cfg_test)
    cfg_changed['name'] = 'idg_2'
    idg2 = InternalDataGroup(**cfg_changed)
    assert idg1 != idg2

    # partition not equal
    cfg_changed = deepcopy(cfg_test)
    cfg_changed['partition'] = 'test'
    idg2 = InternalDataGroup(**cfg_changed)
    assert idg1 != idg2

    # the records in the group not equal
    cfg_changed = deepcopy(cfg_test)
    cfg_changed['records'][0]['data'] = 'changed data'
    idg2 = InternalDataGroup(**cfg_changed)
    assert idg1 != idg2

    # different objects
    fake = FakeObj
    assert idg1 != fake

    # should be equal after assignment
    idg2 = idg1
    assert idg1 == idg2


def test_uri_path(bigip):
    """Test InternalDataGroup URI."""
    idg = InternalDataGroup(
        **cfg_test
    )
    assert idg
    assert idg._uri_path(bigip) == bigip.tm.ltm.data_group.internals.internal
