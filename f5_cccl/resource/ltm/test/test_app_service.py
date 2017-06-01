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
from f5_cccl.resource.ltm.app_service import ApplicationService
from f5_cccl.resource.ltm.pool import Pool
from f5_cccl.resource import Resource
from f5_cccl.bigip import CommonBigIP
from mock import Mock
import pytest


cfg_test = {
  "name": "MyAppService",
  "template": "/Common/f5.http",
  "partition": "test",
  "options": {"description": "This is a test iApp"},
  "tables": [{
    "name": "pool__members",
    "columnNames": ["addr", "port", "connection_limit"],
    "rows": [{"row": ["10.2.3.4", "30001", "0"]},
             {"row": ["10.2.3.4", "30002", "0"]},
             {"row": ["10.2.3.4", "30003", "0"]},
             {"row": ["10.2.3.4", "30004", "0"]},
             {"row": ["10.2.3.4", "30005", "0"]}]
    }
  ],        
  "variables": [
    {"name": "net__client_mode", "value": "wan"},
    {"name": "net__server_mode", "value": "lan"},
    {"name": "pool__addr", "value": "10.10.1.100"},
    {"name": "pool__port", "value": "80"},
    {"name": "pool__pool_to_use", "value": "/#create_new#"},
    {"name": "pool__lb_method", "value": "round-robin"},
    {"name": "pool__http", "value": "/#create_new#"},
    {"name": "pool__mask", "value": "255.255.255.255"},
    {"name": "pool__persist", "value": "/#do_not_use#"},
    {"name": "monitor__monitor", "value": "/#create_new#"},
    {"name": "monitor__uri", "value": "/"},
    {"name": "monitor__frequency", "value": "30"},
    {"name": "monitor__response", "value": "none"},
    {"name": "ssl_encryption_questions__advanced", "value": "yes"},
    {"name": "net__vlan_mode", "value": "all"},
    {"name": "net__snat_type", "value": "automap"},
    {"name": "client__tcp_wan_opt", "value": "/#create_new#"},
    {"name": "client__standard_caching_with_wa", "value": "/#create_new#"},
    {"name": "client__standard_caching_without_wa", "value": "/#do_not_use#"},
    {"name": "server__tcp_lan_opt", "value": "/#create_new#"},
    {"name": "server__oneconnect", "value": "/#create_new#"},
    {"name": "server__ntlm", "value": "/#do_not_use#"}
  ]
}

cfg_test2 = {
  "name": "appsvc",
  "template": "/Common/appsvcs_integration_v2.0.002",
  "partition": "test",
  "options": {"description": "This is a test iApp"},
  "tables": [{
    "name": "pool__Members",
    "columnNames": ["Index", "IPAddress", "Port", "ConnectionLimit", "Ratio",
                    "PriorityGroup", "State"],
    "rows": [{"row": ["0", "10.2.3.5", "30001", "1000", "1", "0", "enabled"]},
             {"row": ["0", "10.2.3.5", "30002", "1000", "1", "0", "enabled"]},
             {"row": ["0", "10.2.3.5", "30003", "1000", "1", "0", "enabled"]},
             {"row": ["0", "10.2.3.5", "30004", "1000", "1", "0", "enabled"]},
             {"row": ["0", "10.2.3.5", "30005", "1000", "1", "0", "enabled"]}]
  },
  {
    "name": "l7policy__rulesMatch",
    "columnNames": ["Group", "Operand", "Negate", "Condition", "Value",
                    "CaseSensitive", "Missing"],
    "rows": [{"row": ["0", "http-uri/request/path", "no", "starts-with",
                      "/env", "no", "no"]},
             {"row": ["default", "", "no", "", "", "no", "no"]}]
  },
  {
    "name": "l7policy__rulesAction",
    "columnNames": ["Group", "Target", "Parameter"],
    "rows": [{"row": ["0", "forward/request/reset", "none"]},
             {"row": ["default", "forward/request/select/pool", "pool:0"]}]
  },
  {
    "name": "pool__Pools",
    "columnNames": ["Index", "Name", "Description", "LbMethod",
                "Monitor", "AdvOptions"],
    "rows": [{"row": ["0", "", "", "round-robin", "0", "none"]}]
  },
  {
    "name": "monitor__Monitors",
    "columnNames": ["Index", "Name", "Type", "Options"],
    "rows": [{"row": ["0", "/Common/tcp", "none", "none"]}]
  }],        
  "variables": [
    {"name": "pool__addr", "value": "10.10.2.100"},
    {"name": "pool__port", "value": "80"},
    {"name": "pool__mask", "value": "255.255.255.255"},
    {"name": "vs__Name", "value": "appsvc_iapp_vs"},
    {"name": "vs__ProfileClientProtocol", "value": "/Common/tcp-wan-optimized"},
    {"name": "vs__ProfileServerProtocol", "value": "/Common/tcp-lan-optimized"},
    {"name": "vs__ProfileHTTP", "value": "/Common/http"},
    {"name": "vs__SNATConfig", "value": "automap"},
    {"name": "iapp__logLevel", "value": "7"},
    {"name": "iapp__routeDomain", "value": "auto"},
    {"name": "iapp__mode", "value": "auto"},
    {"name": "pool__DefaultPoolIndex", "value": "0"},
    {"name": "l7policy__strategy", "value": "/Common/first-match"}
  ]
}

resource_create_save = Resource.create
resource_update_save = Resource.update

@pytest.fixture
def bigip():
    bigip = Mock()
    return bigip


@pytest.fixture(autouse=True)
def mock_resource(request):
    """Mock the resource object"""
    request.addfinalizer(restore_resource)
    Resource.create = Mock()
    Resource.update = Mock()


def restore_resource():
    Resource.create = resource_create_save
    Resource.update = resource_update_save


def test_create_app_service(bigip, mock_resource):
    """Test Application Service creation."""
    appsvc = ApplicationService(
        **cfg_test
    )
    assert appsvc

    # verify all cfg items
    expected = cfg_test
    expected.update(cfg_test['options'])
    del expected['options']
    for k,v in expected.items():
        assert appsvc.data[k] == v

    appsvc.create(bigip)

    # verify that 'create' was called with expected dict
    assert Resource.create.called

def test_update_app_service(bigip, mock_resource):
    """Test Application Service update."""
    appsvc = ApplicationService(
        **cfg_test2
    )
    assert appsvc

    # verify all cfg items
    expected = cfg_test2
    expected.update(cfg_test2['options'])
    del expected['options']

    for k,v in expected.items():
        assert appsvc.data[k] == v

    appsvc.update(bigip)

    # verify that 'update' was called with expected dict
    assert Resource.update.called


def test_hash():
    """Test Application Service hash."""
    appsvc = ApplicationService(
        **cfg_test
    )
    appsvc1 = ApplicationService(
        **cfg_test
    )
    cfg_changed = copy(cfg_test)
    cfg_changed['name'] = 'test'
    appsvc2 = ApplicationService(
        **cfg_changed
    )
    cfg_changed = copy(cfg_test)
    cfg_changed['partition'] = 'other'
    appsvc3 = ApplicationService(
        **cfg_changed
    )
    assert appsvc
    assert appsvc1
    assert appsvc2
    assert appsvc3

    assert hash(appsvc) == hash(appsvc1)
    assert hash(appsvc) != hash(appsvc2)
    assert hash(appsvc) != hash(appsvc3)


def test_eq():
    """Test Application Service equality."""
    partition = 'Common'
    name = 'app_svc'

    appsvc1 = ApplicationService(
        **cfg_test
    )
    appsvc2 = ApplicationService(
        **cfg_test
    )
    cfg_test3 = deepcopy(cfg_test)
    cfg_test3['variables'][0]['value'] = 'changed'
    appsvc3 = ApplicationService(
        **cfg_test3
    )
    pool = Pool(
        name=name,
        partition=partition
    )
    assert appsvc1
    assert appsvc2
    assert appsvc3
    assert appsvc1 == appsvc2

    # not equal
    assert appsvc1 != appsvc3

    # different objects
    with pytest.raises(ValueError):
        assert appsvc1 != pool 


def test_uri_path(bigip):
    """Test Application Service URI."""
    appsvc = ApplicationService(
        **cfg_test
    )
    assert appsvc

    assert appsvc._uri_path(bigip) == bigip.tm.sys.application.services.service
