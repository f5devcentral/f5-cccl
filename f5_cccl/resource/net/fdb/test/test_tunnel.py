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
from f5_cccl.resource.net.fdb.tunnel import FDBTunnel
from mock import Mock
import pytest


cfg_test = {
    'name': 'test_tunnel',
    'partition': 'test_partition',
    'records': [
        {
            'name': '12:ab:34:cd:56:ef',
            'endpoint': '1.2.3.4'
        },
        {
            'name': '98:ab:76:cd:54:ef',
            'endpoint': '4.3.2.1'
        }
    ]
}


@pytest.fixture
def bigip():
    bigip = Mock()
    return bigip


def test_create_tunnel():
    """Test FDBTunnel creation."""
    tunnel = FDBTunnel(**cfg_test)
    data = tunnel.data
    assert tunnel.name == 'test_tunnel'
    assert tunnel.partition == 'test_partition'
    assert data['records'][0]['name'] == '12:ab:34:cd:56:ef'
    assert data['records'][0]['endpoint'] == '1.2.3.4'
    assert data['records'][1]['name'] == '98:ab:76:cd:54:ef'
    assert data['records'][1]['endpoint'] == '4.3.2.1'


def test_eq():
    """Test FDBTunnel equality."""
    tunnel1 = FDBTunnel(**cfg_test)
    tunnel2 = FDBTunnel(**cfg_test)
    assert tunnel1
    assert tunnel2
    assert tunnel1 == tunnel2

    # name not equal
    cfg_changed = copy(cfg_test)
    cfg_changed['name'] = '4.3.2.1'
    tunnel2 = FDBTunnel(**cfg_changed)
    assert tunnel1 != tunnel2

    # partition not equal
    cfg_changed = copy(cfg_test)
    cfg_changed['partition'] = 'other'
    tunnel2 = FDBTunnel(**cfg_changed)
    assert tunnel1 != tunnel2

    # records name not equal
    cfg_changed = copy(cfg_test)
    cfg_changed['records'][0]['name'] = '12:wx:34:yz:56:ab'
    tunnel2 = FDBTunnel(**cfg_changed)
    assert tunnel1 != tunnel2

    # records endpoint not equal
    cfg_changed = copy(cfg_test)
    cfg_changed['records'][0]['endpoint'] = '5.6.7.8'
    tunnel2 = FDBTunnel(**cfg_changed)
    assert tunnel1 != tunnel2


def test_hash():
    """Test FDBTunnel hash."""
    tunnel1 = FDBTunnel(**cfg_test)
    tunnel2 = FDBTunnel(**cfg_test)
 
    cfg_changed = copy(cfg_test)
    cfg_changed['name'] = 'new_tunnel'
    tunnel3 = FDBTunnel(**cfg_changed)
 
    cfg_changed = copy(cfg_test)
    cfg_changed['partition'] = 'other'
    tunnel4 = FDBTunnel(**cfg_changed)
 
    assert tunnel1
    assert tunnel2
    assert tunnel3
    assert tunnel4
 
    assert hash(tunnel1) == hash(tunnel2)
    assert hash(tunnel1) != hash(tunnel3)
    assert hash(tunnel1) != hash(tunnel4)
 
 
def test_uri_path(bigip):
    """Test FDBTunnel URI."""
    tunnel = FDBTunnel(**cfg_test)
    assert tunnel._uri_path(bigip) == bigip.tm.net.fdb.tunnels.tunnel
