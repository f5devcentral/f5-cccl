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

import copy

from f5_cccl.resource.ltm.pool_member import ApiPoolMember
from f5_cccl.resource.ltm.pool_member import PoolMember

from mock import MagicMock
# import pdb
import pytest


@pytest.fixture
def members():
    members = {
        'member_min_config': {
            'address': "172.16.200.100",
            'port': 80
        },
        'member_w_route_domain': {
            'address': "172.16.200.101",
            'port': 80,
            'routeDomain': {'id': 0}
        },
        'member_no_port': {
            'address': "172.16.200.102",
            'routeDomain': {'id': 0}
        },
        'member_no_address': {
            'port': 80,
            'routeDomain': {'id': 0}
        },
        'member_w_nonzero_route_domain': {
            'address': "172.16.200.103",
            'port': 80,
            'routeDomain': {'id': 2}
        },
        'member_min_ipv6_config': {
            'address': "2001:0db8:3c4d:0015:0000:0000:abcd:ef12",
            'port': 80
        },
        'member_min_ipv6_rd_config': {
            'address': "2001:0db8:3c4d:0015:0000:0000:abcd:ef12",
            'port': 80,
            'routeDomain': {'id': 2}
        },
        'member_min_config_w_name': {
            'address': "172.16.200.100",
            'port': 80,
            'name': "192.168.200.100:80"
        }
    }
    return members


@pytest.fixture
def bigip():
    """Fixture that returns BIG-IP."""
    bigip = MagicMock()
    return bigip


@pytest.fixture
def pool():
    """Fixture that returns a Pool object."""
    return MagicMock()


POOL_PROPERTIES = PoolMember.properties


def test_create_cccl_member_min_config(pool, members):
    """Test creation of ApiPoolMember from bare config."""
    cfg_name = "member_min_config"
    partition = "Common"

    # pdb.set_trace()
    member = ApiPoolMember(
        name=None,
        partition=partition,
        pool=pool,
        **members[cfg_name]
    )

    assert member

    # Test data
    assert member.data
    pool_data = copy.copy(member.data)
    for k, _ in POOL_PROPERTIES.items():
        if k == 'name':
            assert pool_data['name'] == "172.16.200.100:80"
        elif k == 'partition':
            assert pool_data['partition'] == "Common"
        elif k == 'ratio':
            assert pool_data['ratio'] == 1
        elif k == 'connectionLimit':
            assert pool_data['connectionLimit'] == 0
        elif k == 'priorityGroup':
            assert pool_data['priorityGroup'] == 0
        elif k == 'session':
            assert pool_data['session'] == "user-enabled"
        elif k == 'description':
            assert not pool_data['description']
        pool_data.pop(k)

    assert not pool_data, "unexpected keys found in data"


def test_create_cccl_member_w_route_domain(pool, members):
    """Test creation of ApiPoolMember from bare config w route domain."""
    cfg_name = "member_w_route_domain"
    partition = "Common"

    member = ApiPoolMember(
        name=None,
        partition=partition,
        pool=pool,
        **members[cfg_name]
    )

    assert member

    # Test data
    assert member.data
    pool_data = copy.copy(member.data)
    for k, _ in POOL_PROPERTIES.items():
        if k == 'name':
            assert pool_data['name'] == "172.16.200.101:80"
        elif k == 'partition':
            assert pool_data['partition'] == "Common"
        elif k == 'ratio':
            assert pool_data['ratio'] == 1
        elif k == 'connectionLimit':
            assert pool_data['connectionLimit'] == 0
        elif k == 'priorityGroup':
            assert pool_data['priorityGroup'] == 0
        elif k == 'session':
            assert pool_data['session'] == "user-enabled"
        elif k == 'description':
            assert not pool_data['description']
        pool_data.pop(k)

    assert not pool_data, "unexpected keys found in data"


def test_create_cccl_member_no_port(pool, members):
    """Test of ApiPoolMember create without name or port."""
    cfg_name = "member_no_port"
    partition = "Common"

    with pytest.raises(TypeError):
        member = ApiPoolMember(
            name=None,
            partition=partition,
            pool=pool,
            **members[cfg_name]
        )
        assert not member


def test_create_cccl_member_no_address(pool, members):
    """Test of ApiPoolMember create without name or address."""
    cfg_name = "member_no_address"
    partition = "Common"

    with pytest.raises(TypeError):
        member = ApiPoolMember(
            name=None,
            partition=partition,
            pool=pool,
            **members[cfg_name]
        )
        assert not member


def test_create_cccl_member_w_nonzero_route_domain(pool, members):
    """Test of ApiPoolMember create with non-zero route-domain."""
    cfg_name = "member_w_nonzero_route_domain"
    partition = "Common"

    member = ApiPoolMember(
        name=None,
        partition=partition,
        pool=pool,
        **members[cfg_name]
    )

    assert member

    # Test data
    assert member.data
    pool_data = copy.copy(member.data)
    for k, _ in POOL_PROPERTIES.items():
        if k == 'name':
            assert pool_data['name'] == "172.16.200.103%2:80"
        elif k == 'partition':
            assert pool_data['partition'] == "Common"
        elif k == 'ratio':
            assert pool_data['ratio'] == 1
        elif k == 'connectionLimit':
            assert pool_data['connectionLimit'] == 0
        elif k == 'priorityGroup':
            assert pool_data['priorityGroup'] == 0
        elif k == 'session':
            assert pool_data['session'] == "user-enabled"
        elif k == 'description':
            assert not pool_data['description']
        pool_data.pop(k)

    assert not pool_data, "unexpected keys found in data"


def test_create_cccl_member_min_ipv6_config(pool, members):
    """Test of ApiPoolMember create with IPv6 address."""
    cfg_name = "member_min_ipv6_config"
    partition = "Common"

    # pdb.set_trace()
    member = ApiPoolMember(
        name=None,
        partition=partition,
        pool=pool,
        **members[cfg_name]
    )

    assert member

    # Test data
    assert member.data
    pool_data = copy.copy(member.data)
    for k, _ in POOL_PROPERTIES.items():
        if k == 'name':
            assert (pool_data['name'] ==
                    "2001:0db8:3c4d:0015:0000:0000:abcd:ef12.80")
        elif k == 'partition':
            assert pool_data['partition'] == "Common"
        elif k == 'ratio':
            assert pool_data['ratio'] == 1
        elif k == 'connectionLimit':
            assert pool_data['connectionLimit'] == 0
        elif k == 'priorityGroup':
            assert pool_data['priorityGroup'] == 0
        elif k == 'session':
            assert pool_data['session'] == "user-enabled"
        elif k == 'description':
            assert not pool_data['description']
        pool_data.pop(k)

    assert not pool_data, "unexpected keys found in data"


def test_create_cccl_member_min_ipv6_rd_config(pool, members):
    """Test of ApiPoolMember create with IPv6 address and route domain."""
    cfg_name = "member_min_ipv6_rd_config"
    partition = "Common"

    # pdb.set_trace()
    member = ApiPoolMember(
        name=None,
        partition=partition,
        pool=pool,
        **members[cfg_name]
    )

    assert member

    # Test data
    assert member.data
    pool_data = copy.copy(member.data)
    for k, _ in POOL_PROPERTIES.items():
        if k == 'name':
            assert (pool_data['name'] ==
                    "2001:0db8:3c4d:0015:0000:0000:abcd:ef12%2.80")
        elif k == 'partition':
            assert pool_data['partition'] == "Common"
        elif k == 'ratio':
            assert pool_data['ratio'] == 1
        elif k == 'connectionLimit':
            assert pool_data['connectionLimit'] == 0
        elif k == 'priorityGroup':
            assert pool_data['priorityGroup'] == 0
        elif k == 'session':
            assert pool_data['session'] == "user-enabled"
        elif k == 'description':
            assert not pool_data['description']
        pool_data.pop(k)

    assert not pool_data, "unexpected keys found in data"


def test_create_cccl_member_min_config_w_name(pool, members):
    """Test of ApiPoolMember create with a name."""
    cfg_name = "member_min_config_w_name"
    partition = "Common"

    # pdb.set_trace()
    member = ApiPoolMember(
        partition=partition,
        pool=pool,
        **members[cfg_name]
    )

    assert member

    # Test data
    assert member.data
    pool_data = copy.copy(member.data)
    for k, _ in POOL_PROPERTIES.items():
        if k == 'name':
            assert pool_data['name'] == "192.168.200.100:80"
        elif k == 'partition':
            assert pool_data['partition'] == "Common"
        elif k == 'ratio':
            assert pool_data['ratio'] == 1
        elif k == 'connectionLimit':
            assert pool_data['connectionLimit'] == 0
        elif k == 'priorityGroup':
            assert pool_data['priorityGroup'] == 0
        elif k == 'session':
            assert pool_data['session'] == "user-enabled"
        elif k == 'description':
            assert not pool_data['description']
        pool_data.pop(k)

    assert not pool_data, "unexpected keys found in data"
