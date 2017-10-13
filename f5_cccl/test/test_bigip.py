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
from f5_cccl.resource.ltm.node import IcrNode
from f5_cccl.resource.ltm.app_service import IcrApplicationService


def test_bigip_refresh(bigip_proxy):
    """Test BIG-IP refresh function."""
    big_ip = bigip_proxy.mgmt_root()

    test_pools = [
        IcrPool(**p) for p in big_ip.bigip_data['pools']
        if p['partition'] == 'test'
    ]
    test_virtuals = [
        VirtualServer(**v) for v in big_ip.bigip_data['virtuals']
        if v['partition'] == 'test'
    ]
    test_iapps = [
        IcrApplicationService(**i) for i in big_ip.bigip_data['iapps']
        if i['partition'] == 'test'
    ]
    test_nodes = [
        IcrNode(default_route_domain=0, **n) for n in big_ip.bigip_data['nodes']
        if n['partition'] == 'test'
    ]

    # refresh the BIG-IP state
    bigip_proxy.refresh()

    # verify pools and pool members
    assert big_ip.tm.ltm.pools.get_collection.called
    assert len(bigip_proxy._pools) == 1

    assert len(bigip_proxy._pools) == len(test_pools)
    for pool in test_pools:
        assert bigip_proxy._pools[pool.name] == pool
        # Make a change, pools will not be equal
        pool._data['loadBalancingMode'] = 'Not a valid LB mode'
        assert bigip_proxy._pools[pool.name] != pool

    # verify virtual servers 
    assert big_ip.tm.ltm.virtuals.get_collection.called
    assert len(bigip_proxy._virtuals) == 1

    assert len(bigip_proxy._virtuals) == len(test_virtuals)
    for v in test_virtuals:
        assert bigip_proxy._virtuals[v.name] == v
        # Make a change, virtuals will not be equal
        v._data['partition'] = 'NoPartition'
        assert bigip_proxy._virtuals[v.name] != v

    # verify application services
    assert big_ip.tm.sys.application.services.get_collection.called
    assert len(bigip_proxy._iapps) == 2

    assert len(bigip_proxy._iapps) == len(test_iapps)
    for i in test_iapps:
        assert bigip_proxy._iapps[i.name] == i
        # Make a change, iapps will not be equal
        i._data['template'] = '/Common/NoTemplate'
        assert bigip_proxy._iapps[i.name] != i

    # verify nodes
    assert big_ip.tm.ltm.nodes.get_collection.called
    assert len(bigip_proxy._nodes) == 4

    assert len(bigip_proxy._nodes) == len(test_nodes)
    for n in test_nodes:
        assert bigip_proxy._nodes[n.name] == n


def test_bigip_properties(bigip_proxy):
    """Test BIG-IP properties function."""
    big_ip = bigip_proxy

    test_pools = [
        IcrPool(**p) for p in big_ip.mgmt_root().bigip_data['pools']
        if p['partition'] == 'test'
    ]
    test_virtuals = [
        VirtualServer(**v) for v in big_ip.mgmt_root().bigip_data['virtuals']
        if v['partition'] == 'test'
    ]

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
