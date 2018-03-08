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
from f5_cccl.resource import Resource
from f5_cccl.resource.ltm.node import Node
from f5_cccl.resource.ltm.pool import Pool
from mock import Mock, patch
import pytest


cfg_test = {
    'name': '1.2.3.4%2',
    'partition': 'my_partition',
    'address': '1.2.3.4%2'
}


@pytest.fixture
def bigip():
    bigip = Mock()
    return bigip


def test_create_node():
    """Test Node creation."""
    node = Node(
        default_route_domain=2,
        **cfg_test
    )
    assert node

    # verify all cfg items
    for k,v in cfg_test.items():
        assert node._data[k] == v


def test_update_node():
    node = Node(
        default_route_domain=2,
        **cfg_test
    )

    assert 'address' in node.data

    # Verify that immutable 'address' is not passed to parent method
    with patch.object(Resource, 'update') as mock_method:
        node.update(bigip)
        assert 1 == mock_method.call_count
        assert 'address' not in mock_method.call_args[1]['data']


def test_hash():
    """Test Node Server hash."""
    node = Node(
        default_route_domain=2,
        **cfg_test
    )
    node1 = Node(
        default_route_domain=2,
        **cfg_test
    )
    cfg_changed = copy(cfg_test)
    cfg_changed['name'] = 'test'
    node2 = Node(
        default_route_domain=2,
        **cfg_changed
    )
    cfg_changed = copy(cfg_test)
    cfg_changed['partition'] = 'other'
    node3 = Node(
        default_route_domain=2,
        **cfg_changed
    )
    assert node
    assert node1
    assert node2
    assert node3

    assert hash(node) == hash(node1)
    assert hash(node) != hash(node2)
    assert hash(node) != hash(node3)


def test_eq():
    """Test Node equality."""
    partition = 'Common'
    name = 'node_1'

    node = Node(
        default_route_domain=2,
        **cfg_test
    )
    node2 = Node(
        default_route_domain=2,
        **cfg_test
    )
    pool = Pool(
        name=name,
        partition=partition
    )
    assert node
    assert node2
    assert node != node2

    node2.data['state'] = 'up'
    node2.data['session'] = 'user-enabled'
    assert node == node2

    node2.data['state'] = 'unchecked'
    node2.data['session'] = 'monitor-enabled'
    assert node == node2

    # not equal
    node2.data['state'] = 'user-down'
    node2.data['session'] = 'user-enabled'
    assert node != node2

    node2.data['state'] = 'up'
    node2.data['session'] = 'user-disabled'
    assert node != node2

    node2.data['state'] = 'up'
    node2.data['session'] = 'user-enabled'
    node2.data['address'] = '10.10.0.10'
    assert node != node2

    # different objects
    assert node != pool


def test_uri_path(bigip):
    """Test Node URI."""
    node = Node(
        default_route_domain=2,
        **cfg_test
    )
    assert node

    assert node._uri_path(bigip) == bigip.tm.ltm.nodes.node
