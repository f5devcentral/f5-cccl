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
from f5_cccl.resource.ltm.pool import IcrPool
from f5_cccl.resource.ltm.virtual import VirtualServer
from f5_cccl.resource.ltm.node import Node
from f5_cccl.resource.ltm.app_service import ApplicationService


def test_bigip_refresh(big_ip):
    """Test BIG-IP refresh function."""
    test_pools = []
    for p in big_ip.bigip_data['pools']:
        pool = IcrPool(**p)
        test_pools.append(pool)
    test_virtuals = []
    for v in big_ip.bigip_data['virtuals']:
        test_virtuals.append(VirtualServer(**v))
    test_iapps = []
    for i in big_ip.bigip_data['iapps']:
        test_iapps.append(ApplicationService(**i))
    test_nodes = []
    for n in big_ip.bigip_data['nodes']:
        test_nodes.append(Node(**n))

    # refresh the BIG-IP state
    big_ip.refresh()

    # verify pools and pool members
    assert big_ip.tm.ltm.pools.get_collection.called
    assert len(big_ip._pools) == 2

    assert len(big_ip._pools) == len(test_pools)
    for pool in test_pools:
        assert big_ip._pools[pool.name] == pool
        # Make a change, pools will not be equal
        pool._data['loadBalancingMode'] = 'Not a valid LB mode'
        assert big_ip._pools[pool.name] != pool

    # verify virtual servers 
    assert big_ip.tm.ltm.virtuals.get_collection.called
    assert len(big_ip._virtuals) == 2

    assert len(big_ip._virtuals) == len(test_virtuals)
    for v in test_virtuals:
        assert big_ip._virtuals[v.name] == v
        # Make a change, virtuals will not be equal
        v._data['partition'] = 'NoPartition'
        assert big_ip._virtuals[v.name] != v

    # verify application services
    assert big_ip.tm.sys.application.services.get_collection.called
    assert len(big_ip._iapps) == 2

    assert len(big_ip._iapps) == len(test_iapps)
    for i in test_iapps:
        assert big_ip._iapps[i.name] == i
        # Make a change, iapps will not be equal
        i._data['template'] = '/Common/NoTemplate'
        assert big_ip._iapps[i.name] != i

    # verify nodes
    assert big_ip.tm.ltm.nodes.get_collection.called
    assert len(big_ip._nodes) == 4

    assert len(big_ip._nodes) == len(test_nodes)
    for n in test_nodes:
        assert big_ip._nodes[n.name] == n


def test_bigip_properties(big_ip):
    """Test BIG-IP properties function."""
    test_pools = []
    for p in big_ip.bigip_data['pools']:
        pool = IcrPool(**p)
        test_pools.append(pool)
    test_virtuals = []
    for v in big_ip.bigip_data['virtuals']:
        test_virtuals.append(VirtualServer(**v))

    # refresh the BIG-IP state
    big_ip.refresh()

    assert len(big_ip.get_pools()) == len(test_pools)
    for p in test_pools:
        assert big_ip._pools[p.name] == p

    assert len(big_ip.get_virtuals()) == len(test_virtuals)
    for v in test_virtuals:
        assert big_ip._virtuals[v.name] == v

    http_hc = big_ip.get_http_monitors()
    https_hc = big_ip.get_https_monitors()
    tcp_hc = big_ip.get_tcp_monitors()
    icmp_hc = big_ip.get_icmp_monitors()
