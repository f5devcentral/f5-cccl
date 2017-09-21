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
import pytest
import requests
import pdb

from mock import MagicMock

from f5.bigip import ManagementRoot

from f5.sdk_exception import F5SDKError
from icontrol.exceptions import iControlUnexpectedHTTPError

import f5_cccl.exceptions as exceptions
from f5_cccl.resource.ltm.virtual import VirtualServer

from pprint import pprint

requests.packages.urllib3.disable_warnings()

req_symbols = ['bigip_mgmt_ip', 'bigip_username', 'bigip_password']
def missing_bigip_symbols():
    for sym in req_symbols:
        if not hasattr(pytest.symbols, sym):
            return True
    return False

pytestmark = pytest.mark.skipif(missing_bigip_symbols(),
                                reason="Need symbols pointing at a real bigip.")

def _make_svc_config(partition, num_virtuals=0, num_members=0):
    base_virtual = {
        'name': 'Virtual-1',
        'destination': '/Test/1.2.3.4:80',
        'ipProtocol': 'tcp',
        'profiles': [
            {'name': "tcp",
            'partition': "Common",
            'context': "all"}
        ],
        "enabled": True,
        "vlansEnabled": True,
        "sourceAddressTranslation": {
        "type": "automap",
        }
    }
    base_pool = {
        "name": "pool1",
        "monitors": ["/Common/http"]
    },
    base_member ={
        "address": "172.16.0.100", "port": 8080, "routeDomain": {"id": 0}
    }


    cfg={
        'virtualServers': [],
        'pools': [],
    }
    for i in range(num_virtuals):
        v = {}
        v.update(base_virtual)
        v['name'] = "virtual-{}".format(i)
        v['pool'] = "/{}/pool-{}".format(partition,i)
        cfg['virtualServers'].append(v)

        p = {}
        p.update(base_pool)
        p['name'] = "pool-{}".format(i)

        members = []
        for i in range(num_members):
            m = {}
            m.update(base_member)
            m['address'] = '172.16.0.{}'.format(i)
            members.append(m)
        p['members'] = members
        cfg['pools'].append(p)

    return cfg

testdata = [
    (1, 1),
    (10, 10),
    (100, 10),
    (10, 100),
]



@pytest.mark.parametrize("nv,nm", testdata)
@pytest.mark.benchmark(group="apply-new")
def test_apply_new(partition, cccl, bigip_rest_counters, benchmark, nv, nm):
    cfg = _make_svc_config(partition, num_virtuals=nv, num_members=nm)
    def setup():
        cccl.apply_config({})
    def apply():
        cccl.apply_config(cfg)
    benchmark.pedantic(apply, setup=setup, rounds=2, iterations=1)

    pprint(bigip_rest_counters)

@pytest.mark.parametrize("nv,nm", testdata)
@pytest.mark.benchmark(group="apply-no-change")
def test_apply_no_change(partition, cccl, bigip_rest_counters, benchmark, nv, nm):
    cfg = _make_svc_config(partition, num_virtuals=nv, num_members=nm)
    def apply():
        cccl.apply_config(cfg)
    apply()
    benchmark.pedantic(apply, rounds=2, iterations=1)
    pprint(bigip_rest_counters)
