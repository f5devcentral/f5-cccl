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

import json
import os
from pprint import pprint as pp

from f5_cccl.resource.ltm.pool_member import IcrPoolMember
from f5_cccl.resource.ltm.pool_member import PoolMember


from mock import MagicMock
# import pdb
import pytest


ccclMemberA = {
    "address": "172.16.0.100", "port": 8080, "routeDomain": {"id": 0}}
ccclMemberB = {
    "address": "172.16.0.101", "port": 8080, "routeDomain": {"id": 0}}


@pytest.fixture
def pool_member_ipv6():
    pass


@pytest.fixture
def pool_member_with_rd():
    member = {"name": "192.168.100.101%0:80"}
    return member


@pytest.fixture
def pool_member_with_rd_ipv6():
    member = {"name": "2001:0db8:3c4d:0015:0000:0000:abcd:ef12%0.80"}
    return member


@pytest.fixture
def bigip():
    bigip = MagicMock()
    return bigip


@pytest.fixture
def pool():
    return MagicMock()


@pytest.fixture
def bigip_members():
    members_filename = (
        os.path.join(os.path.dirname(os.path.abspath(__file__)),
                     './bigip-members.json'))
    with open(members_filename) as fp:
        json_data = fp.read()
        json_data = json.loads(json_data)
        members = [m for m in json_data['members']]
        pp(json_data)

    return members


def test_create_bigip_member(pool, bigip_members):
    """Test the creation of PoolMember from BIG-IP data."""
    member_cfg = bigip_members[0]

    pp(bigip_members)
    pp(member_cfg)
    # pdb.set_trace()
    member = IcrPoolMember(
        pool=pool,
        **member_cfg
    )

    assert member

    # Test data
    assert member.data
    assert member.data['name'] == "192.168.200.2:80"
    assert member.data['ratio'] == 1
    assert member.data['connectionLimit'] == 0
    assert member.data['priorityGroup'] == 0
    assert member.data['session'] == "user-enabled"
    assert not member.data['description']


def test_create_pool_member(pool, bigip_members):
    """Test the creation of PoolMember from BIG-IP data."""
    member_cfg = bigip_members[0]

    member = PoolMember(
        pool=pool,
        **member_cfg
    )

    assert member
    assert member._pool

    # Test data
    assert member.data
    assert member.data['name'] == "192.168.200.2:80"
    assert member.data['ratio'] == 1
    assert member.data['connectionLimit'] == 0
    assert member.data['priorityGroup'] == 0
    assert member.data['session'] == "user-enabled"
    assert not member.data['description']


def test_create_pool_member_with_rd(pool, pool_member_with_rd):
    """Test the creation of PoolMember from BIG-IP data."""
    member = PoolMember(
        partition="Common",
        pool=pool,
        **pool_member_with_rd
    )

    assert member
    assert member._pool

    # Test data
    assert member.data
    assert member.data['name'] == "192.168.100.101:80"


def test_create_pool_member_with_rd_ipv6(pool, pool_member_with_rd_ipv6):
    """Test the creation of PoolMember from BIG-IP data."""
    member = PoolMember(
        partition="Common",
        pool=pool,
        **pool_member_with_rd_ipv6
    )

    assert member
    assert member._pool

    # Test data
    assert member.data
    assert member.data['name'] == "2001:0db8:3c4d:0015:0000:0000:abcd:ef12.80"
