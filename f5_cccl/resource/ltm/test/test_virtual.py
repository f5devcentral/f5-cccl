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

from copy import copy, deepcopy
from f5_cccl.resource.ltm.pool import Pool

from f5_cccl.resource.ltm.virtual import ApiVirtualServer
from f5_cccl.resource.ltm.virtual import IcrVirtualServer
from f5_cccl.resource.ltm.virtual import VirtualServer

from mock import Mock
import pytest


cfg_test = {
    'name': 'Virtual-1',
    'partition': 'my_partition',
    'destination': '/Test/1.2.3.4%2:80',
    'source': '10.0.0.1%2/32',
    'pool': '/my_partition/pool1',
    'ipProtocol': 'tcp',
    'profiles': [
        {'name': "tcp",
         'partition': "Common",
         'context': "all"}
    ],
    'policies': [
        {'name': "test_policy",
         'partition': "my_partition"}
    ],
    "enabled": True,
    "vlansEnabled": True,
    "vlans": ["/Test/vlan-100", "/Common/http-tunnel"],
    "sourceAddressTranslation": {
	"type": "snat",
	"pool": "/Test/snatpool1"
    }
}


@pytest.fixture
def bigip():
    bigip = Mock()
    return bigip


def test_create_virtual():
    """Test Virtual Server creation."""
    virtual = VirtualServer(
        default_route_domain=2,
        **cfg_test
    )
    assert virtual

    # verify all cfg items
    for k,v in cfg_test.items():
        if k == "vlans":
            assert virtual.data[k] == sorted(v)
        else:
            assert virtual.data[k] == v


def test_hash():
    """Test Virtual Server hash."""
    virtual = VirtualServer(
        default_route_domain=2,
        **cfg_test
    )
    virtual1 = VirtualServer(
        default_route_domain=2,
        **cfg_test
    )
    cfg_changed = copy(cfg_test)
    cfg_changed['name'] = 'test'
    virtual2 = VirtualServer(
        default_route_domain=2,
        **cfg_changed
    )
    cfg_changed = copy(cfg_test)
    cfg_changed['partition'] = 'other'
    virtual3 = VirtualServer(
        default_route_domain=2,
        **cfg_changed
    )
    assert virtual
    assert virtual1
    assert virtual2
    assert virtual3

    assert hash(virtual) == hash(virtual1)
    assert hash(virtual) != hash(virtual2)
    assert hash(virtual) != hash(virtual3)


def test_eq():
    """Test Virtual Server equality."""
    partition = 'Common'
    name = 'virtual_1'

    virtual = VirtualServer(
        default_route_domain=2,
        **cfg_test
    )
    virtual2 = VirtualServer(
        default_route_domain=2,
        **cfg_test
    )
    pool = Pool(
        name=name,
        partition=partition
    )
    assert virtual
    assert virtual2
    assert virtual == virtual2

    # not equal
    virtual2.data['destination'] = '/Test/1.2.3.4:8080'
    assert virtual != virtual2

    # different objects
    assert virtual != pool


def test_uri_path(bigip):
    """Test Virtual Server URI."""
    virtual = VirtualServer(
        default_route_domain=2,
        **cfg_test
    )
    assert virtual

    assert virtual._uri_path(bigip) == bigip.tm.ltm.virtuals.virtual


def test_ipv4_destination():
    """Test Virtual Server destination."""
    virtual = VirtualServer(
        default_route_domain=2,
        **cfg_test
    )
    assert virtual

    destination = virtual.destination
    assert destination

    assert destination[0] == "/Test/1.2.3.4%2:80"
    assert destination[1] == "Test"
    assert destination[2] == "1.2.3.4%2"
    assert destination[3] == "80"

    cfg = copy(cfg_test)
    cfg['destination'] = "/Test/1.2.3.4%2:80"
    virtual = VirtualServer(
        default_route_domain=2,
        **cfg
    )

    destination = virtual.destination
    assert destination[0] == "/Test/1.2.3.4%2:80"
    assert destination[1] == "Test"
    assert destination[2] == "1.2.3.4%2"
    assert destination[3] == "80"

    cfg = copy(cfg_test)
    cfg['destination'] = "/Test/my_virtual_addr%2:80"
    virtual = VirtualServer(
        default_route_domain=2,
        **cfg
    )

    destination = virtual.destination
    assert destination[0] == "/Test/my_virtual_addr%2:80"
    assert destination[1] == "Test"
    assert destination[2] == "my_virtual_addr%2"
    assert destination[3] == "80"

    cfg = copy(cfg_test)
    cfg['destination'] = "/Test_1/my_virtual_addr%2:80"
    virtual = VirtualServer(
        default_route_domain=2,
        **cfg
    )

    destination = virtual.destination
    assert destination[0] == "/Test_1/my_virtual_addr%2:80"
    assert destination[1] == "Test_1"
    assert destination[2] == "my_virtual_addr%2"
    assert destination[3] == "80"

    cfg = copy(cfg_test)
    cfg['destination'] = "/Test-1/my_virtual_addr%2:80"
    virtual = VirtualServer(
        default_route_domain=2,
        **cfg
    )

    destination = virtual.destination
    assert destination[0] == "/Test-1/my_virtual_addr%2:80"
    assert destination[1] == "Test-1"
    assert destination[2] == "my_virtual_addr%2"
    assert destination[3] == "80"

    cfg = copy(cfg_test)
    cfg['destination'] = "/Test.1/my_virtual_addr%2:80"
    virtual = VirtualServer(
        default_route_domain=2,
        **cfg
    )

    destination = virtual.destination
    assert destination[0] == "/Test.1/my_virtual_addr%2:80"
    assert destination[1] == "Test.1"
    assert destination[2] == "my_virtual_addr%2"
    assert destination[3] == "80"


def test_ipv6_destination():
    cfg = copy(cfg_test)
    cfg['destination'] = "/Test_1/2001::1%2.80"
    virtual = VirtualServer(
        default_route_domain=2,
        **cfg
    )

    destination = virtual.destination
    assert destination[0] == "/Test_1/2001::1%2.80"
    assert destination[1] == "Test_1"
    assert destination[2] == "2001::1%2"
    assert destination[3] == "80"

    cfg = copy(cfg_test)
    cfg['destination'] = "/Test/2001:0db8:85a3:0000:0000:8a2e:0370:7334.80"
    virtual = VirtualServer(
        default_route_domain=2,
        **cfg
    )

    destination = virtual.destination
    assert destination[0] == "/Test/2001:0db8:85a3:0000:0000:8a2e:0370:7334%2.80"
    assert destination[1] == "Test"
    assert destination[2] == "2001:0db8:85a3:0000:0000:8a2e:0370:7334%2"
    assert destination[3] == "80"

    cfg = copy(cfg_test)
    cfg['destination'] = "/Test/2001:0db8:85a3::8a2e:0370:7334.80"
    virtual = VirtualServer(
        default_route_domain=2,
        **cfg
    )

    destination = virtual.destination
    assert destination[0] == "/Test/2001:0db8:85a3::8a2e:0370:7334%2.80"
    assert destination[1] == "Test"
    assert destination[2] == "2001:0db8:85a3::8a2e:0370:7334%2"
    assert destination[3] == "80"

    # Negative matches
    cfg = copy(cfg_test)
    cfg['destination'] = "Test/2001:0db8:85a3::8a2e:0370:7334.80"
    virtual = VirtualServer(
        default_route_domain=2,
        **cfg
    )

    destination = virtual.destination
    assert destination[0] == "Test/2001:0db8:85a3::8a2e:0370:7334.80"
    assert not destination[1]
    assert not destination[2]
    assert not destination[3]


    # Negative matches
    cfg = copy(cfg_test)
    cfg['destination'] = "/Test/2001:0db8:85a3::8a2e:0370:7334%3:80"
    virtual = VirtualServer(
        default_route_domain=2,
        **cfg
    )

    destination = virtual.destination
    assert destination[0] == "/Test/2001:0db8:85a3::8a2e:0370:7334%3:80"
    assert not destination[1]
    assert not destination[2]
    assert not destination[3]


cfg_test_api_virtual = {
    'name': 'Virtual-1',
    'partition': 'my_partition',
    'destination': '/Test/1.2.3.4:80',
    'source': '10.0.0.1/32',
    'pool': '/my_partition/pool1',
    'ipProtocol': 'tcp',
    'profiles': [
        {'name': "tcp",
         'partition': "Common",
         'context': "all"}
    ],
    'policies': [
        {'name': "test_policy",
         'partition': "my_partition"}
    ],
    "vlansEnabled": True,
    "vlans": ["/Test/vlan-100", "/Common/http-tunnel"],
    "sourceAddressTranslation": {
	"type": "snat",
	"pool": "/Test/snatpool1"
    }
}


def test_create_api_virtual():
    """Test Virtual Server creation."""
    virtual = ApiVirtualServer(
        default_route_domain=2,
        **cfg_test_api_virtual
    )
    assert virtual

    # verify all cfg items
    for k,v in cfg_test.items():
        if k == "vlans":
            assert virtual.data[k] == sorted(v)
        else:
            assert virtual.data[k] == v

    assert virtual.data['enabled']
    assert 'disabled' not in virtual.data

    cfg_test_api_virtual['enabled'] = False
    virtual = ApiVirtualServer(
        default_route_domain=2,
        **cfg_test_api_virtual
    )
    assert virtual
    assert 'enabled' not in virtual.data
    assert virtual.data['disabled']

    cfg_test_api_virtual['enabled'] = True
    cfg_test_api_virtual.pop('vlansEnabled', None)
    virtual = ApiVirtualServer(
        default_route_domain=2,
        **cfg_test_api_virtual
    )
    assert virtual
    assert 'vlansEnabled' not in virtual.data
    assert virtual.data['vlansDisabled']


cfg_test_icr_virtual = {
    "addressStatus": "yes",
    "autoLasthop": "default",
    "cmpEnabled": "yes",
    "connectionLimit": 0,
    "destination": "/Common/10.190.1.2:443",
    "enabled": True,
    "fullPath": "/Common/virtual1",
    "generation": 15839,
    "gtmScore": 0,
    "ipProtocol": "tcp",
    "kind": "tm:ltm:virtual:virtualstate",
    "mask": "255.255.255.255",
    "mirror": "disabled",
    "mobileAppTunnel": "disabled",
    "name": "virtual1",
    "nat64": "disabled",
    "partition": "Common",
    "policiesReference": {
        "isSubcollection": True,
        "link": "https://localhost/mgmt/tm/ltm/virtual/~Common~virtual1/policies?ver=12.1.0",
        "items": [
            {
                "kind": "tm:ltm:virtual:policies:policiesstate",
                "name": "wrapper_policy",
                "partition": "Test",
                "fullPath": "/Test/wrapper_policy",
                "generation": 7538,
                "selfLink": "https://localhost/mgmt/tm/ltm/virtual/~Test~vs1/policies/~Test~wrapper_policy?ver=12.1.1",
                "nameReference": {
                    "link": "https://localhost/mgmt/tm/ltm/policy/~Test~wrapper_policy?ver=12.1.1"
                }
            }
        ]
    },
    "pool": "/Common/test_pool",
    "poolReference": {
        "link": "https://localhost/mgmt/tm/ltm/pool/~Common~test_pool?ver=12.1.0"
    },
    "profilesReference": {
        "isSubcollection": True,
        "link": "https://localhost/mgmt/tm/ltm/virtual/~Common~virtual1/profiles?ver=12.1.0",
        "items": [
            {
                "kind": "tm:ltm:virtual:profiles:profilesstate",
                "name": "clientssl",
                "partition": "Common",
                "fullPath": "/Common/clientssl",
                "generation": 7538,
                "selfLink": "https://localhost/mgmt/tm/ltm/virtual/~Test~vs1/profiles/~Common~clientssl?ver=12.1.1",
                "context": "clientside",
                "nameReference": {
                    "link": "https://localhost/mgmt/tm/ltm/profile/client-ssl/~Common~clientssl?ver=12.1.1"
                }
            }
        ]
    },
    "rateLimit": "disabled",
    "rateLimitDstMask": 0,
    "rateLimitMode": "object",
    "rateLimitSrcMask": 0,
    "selfLink": "https://localhost/mgmt/tm/ltm/virtual/~Common~virtual1?ver=12.1.0",
    "serviceDownImmediateAction": "none",
    "source": "0.0.0.0/0",
    "sourceAddressTranslation": {
        "type": "none"
    },
    "sourcePort": "preserve",
    "synCookieStatus": "not-activated",
    "translateAddress": "enabled",
    "translatePort": "enabled",
    "vlansDisabled": True,
    "vsIndex": 111
}


def test_create_icr_virtual():
    """Test Virtual Server creation."""
    virtual = IcrVirtualServer(
        default_route_domain=2,
        **cfg_test_icr_virtual
    )
    assert virtual
