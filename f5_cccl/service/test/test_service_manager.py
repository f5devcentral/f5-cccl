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

import json
import pickle
import pytest
from f5_cccl.test.conftest import bigip_proxy

from f5_cccl.resource.ltm.app_service import ApplicationService 
from f5_cccl.resource.ltm.virtual import VirtualServer 
from f5_cccl.resource.ltm.pool import Pool 
from f5_cccl.resource.ltm.monitor.http_monitor import HTTPMonitor 
from f5_cccl.resource.ltm.policy.policy import Policy 
from f5_cccl.resource.ltm.internal_data_group import InternalDataGroup
from f5_cccl.resource.ltm.irule import IRule
from f5_cccl.resource.net.arp import Arp
from f5_cccl.resource.net.fdb.tunnel import FDBTunnel

from f5_cccl.service.manager import ServiceConfigDeployer
from f5_cccl.service.manager import ServiceManager
from f5_cccl.service.config_reader import ServiceConfigReader

from mock import MagicMock
from mock import Mock
from mock import patch


@pytest.fixture
def ltm_service_manager():
    partition = "test"
    schema = 'f5_cccl/schemas/cccl-ltm-api-schema.yml'

    service_mgr = ServiceManager(
        bigip_proxy(),
        partition,
        schema)

    return service_mgr


@pytest.fixture
def net_service_manager():
    partition = "test"
    schema = 'f5_cccl/schemas/cccl-net-api-schema.yml'

    service_mgr = ServiceManager(
        bigip_proxy(),
        partition,
        schema)

    return service_mgr


def test_apply_ltm_config(ltm_service_manager):
    services = {}
    assert ltm_service_manager.apply_ltm_config(services) == 0


def test_apply_net_config(net_service_manager):
    services = {}
    assert net_service_manager.apply_net_config(services) == 0


class TestServiceConfigDeployer:

    def setup(self):
        self.bigip = bigip_proxy()
        self.partition = "test"

        ltm_svcfile = 'f5_cccl/schemas/tests/ltm_service.json'
        with open(ltm_svcfile, 'r') as fp:
            self.ltm_service = json.loads(fp.read())

        net_svcfile = 'f5_cccl/schemas/tests/net_service.json'
        with open(net_svcfile, 'r') as fp:
            self.net_service = json.loads(fp.read())

        config_reader = ServiceConfigReader(self.partition)
        self.default_route_domain = self.bigip.get_default_route_domain()
        self.desired_ltm_config = config_reader.read_ltm_config(
            self.ltm_service, self.default_route_domain)
        self.desired_net_config = config_reader.read_net_config(
            self.net_service, self.default_route_domain)

    def get_objects(self, objs, obj_type):
        """Extract objects of obj_type from the list."""
        objs = [obj for obj in objs if isinstance(obj, obj_type)]
        return objs

    def get_created_ltm_objects(self, ltm_service_manager, obj_type):
        """Return list of created objects."""
        deployer = ltm_service_manager._service_deployer
        deployer._create_resources = Mock(return_value=[])

        ltm_service_manager.apply_ltm_config(self.ltm_service)
        assert deployer._create_resources.called
        args, kwargs = deployer._create_resources.call_args_list[0]
        return self.get_objects(args[0], obj_type)

    def get_updated_ltm_objects(self, ltm_service_manager, obj_type):
        """Return list of updated objects."""
        deployer = ltm_service_manager._service_deployer
        deployer._update_resources = Mock(return_value=[])

        ltm_service_manager.apply_ltm_config(self.ltm_service)
        assert deployer._update_resources.called
        args, kwargs = deployer._update_resources.call_args_list[0]
        return self.get_objects(args[0], obj_type)

    def get_deleted_ltm_objects(self, ltm_service_manager, obj_type):
        """Return list of deleted objects."""
        deployer = ltm_service_manager._service_deployer
        deployer._delete_resources = Mock(return_value=[])

        ltm_service_manager.apply_ltm_config(self.ltm_service)
        assert deployer._delete_resources.called
        args, kwargs = deployer._delete_resources.call_args_list[0]
        return self.get_objects(args[0], obj_type)

    def get_created_net_objects(self, net_service_manager, obj_type):
        """Return list of created objects."""
        deployer = net_service_manager._service_deployer
        deployer._create_resources = Mock(return_value=[])

        net_service_manager.apply_net_config(self.net_service)
        assert deployer._create_resources.called
        args, kwargs = deployer._create_resources.call_args_list[0]
        return self.get_objects(args[0], obj_type)

    def get_updated_net_objects(self, net_service_manager, obj_type):
        """Return list of updated objects."""
        deployer = net_service_manager._service_deployer
        deployer._update_resources = Mock(return_value=[])

        net_service_manager.apply_net_config(self.net_service)
        assert deployer._update_resources.called
        args, kwargs = deployer._update_resources.call_args_list[0]
        return self.get_objects(args[0], obj_type)

    def get_deleted_net_objects(self, net_service_manager, obj_type):
        """Return list of deleted objects."""
        deployer = net_service_manager._service_deployer
        deployer._delete_resources = Mock(return_value=[])

        net_service_manager.apply_net_config(self.net_service)
        assert deployer._delete_resources.called
        args, kwargs = deployer._delete_resources.call_args_list[0]
        return self.get_objects(args[0], obj_type)

    def test_create_deployer(self):
        deployer = ServiceConfigDeployer(self.bigip)
        assert deployer

    def test_deploy_ltm(self):
        deployer = ServiceConfigDeployer(self.bigip)
        tasks_remaining = deployer.deploy_ltm(self.desired_ltm_config,
            self.default_route_domain)
        assert 0 == tasks_remaining

    def test_deploy_net(self):
        deployer = ServiceConfigDeployer(self.bigip)
        tasks_remaining = deployer.deploy_net(self.desired_net_config)
        assert 0 == tasks_remaining

    def test_app_services(self, ltm_service_manager):
        """Test create/update/delete of app services."""
        # Should create one app service
        objs = self.get_created_ltm_objects(ltm_service_manager, ApplicationService)
        assert 1 == len(objs)
        assert objs[0].name == 'MyAppService0'

        # Should update one app service
        self.ltm_service['iapps'][0]['name'] = 'MyAppService'
        objs = self.get_updated_ltm_objects(ltm_service_manager, ApplicationService)
        assert 1 == len(objs)
        assert objs[0].name == 'MyAppService'

        # Should delete two app services
        self.ltm_service['iapps'] = []
        objs = self.get_deleted_ltm_objects(ltm_service_manager, ApplicationService)
        assert 2 == len(objs)
        expected_set = set(['appsvc', 'MyAppService'])
        result_set = set([objs[0].name, objs[1].name])
        assert expected_set == result_set

    def test_virtual_servers(self, ltm_service_manager):
        """Test create/update/delete of Virtual Servers."""
        # Should create one Virtual Server 
        objs = self.get_created_ltm_objects(ltm_service_manager, VirtualServer)
        assert 1 == len(objs)
        assert objs[0].name == 'vs1'

        # Should update one Virtual Server
        self.ltm_service['virtualServers'][0]['name'] = 'virtual2'
        objs = self.get_updated_ltm_objects(ltm_service_manager, VirtualServer)
        assert 1 == len(objs)
        assert objs[0].name == 'virtual2'

        # Should delete one Virtual Server
        self.ltm_service['virtualServers'] = []
        objs = self.get_deleted_ltm_objects(ltm_service_manager, VirtualServer)
        assert 1 == len(objs)
        assert 'virtual2' == objs[0].name

    def test_pools(self, ltm_service_manager):
        """Test create/update/delete of Pools."""
        # Should create one Pool 
        objs = self.get_created_ltm_objects(ltm_service_manager, Pool)
        assert 1 == len(objs)
        assert objs[0].name == 'pool2'

        # Should update one Pool
        self.ltm_service['pools'][0]['name'] = 'pool1'
        objs = self.get_updated_ltm_objects(ltm_service_manager, Pool)
        assert 1 == len(objs)
        assert objs[0].name == 'pool1'

        # Should delete one Pool
        self.ltm_service['pools'] = []
        objs = self.get_deleted_ltm_objects(ltm_service_manager, Pool)
        assert 1 == len(objs)
        assert 'pool1' == objs[0].name

    def test_monitors(self, ltm_service_manager):
        """Test create/update/delete of Health Monitors."""
        # Should create one Monitor 
        objs = self.get_created_ltm_objects(ltm_service_manager, HTTPMonitor)
        assert 1 == len(objs)
        assert objs[0].name == 'myhttp'

        # Should update one Monitor
        self.ltm_service['monitors'][0]['name'] = 'mon_http'
        objs = self.get_updated_ltm_objects(ltm_service_manager, HTTPMonitor)
        assert 1 == len(objs)
        assert objs[0].name == 'mon_http'

        # Should delete one Monitor
        self.ltm_service['monitors'] = [] 
        objs = self.get_deleted_ltm_objects(ltm_service_manager, HTTPMonitor)
        assert 1 == len(objs)
        assert 'mon_http' == objs[0].name

    def test_policies(self, ltm_service_manager):
        """Test create/update/delete of L7 Policies."""
        # Should create one Policy 
        objs = self.get_created_ltm_objects(ltm_service_manager, Policy)
        assert 1 == len(objs)
        assert objs[0].name == 'test_wrapper_policy'

        # Should update one Policy
        self.ltm_service['l7Policies'][0]['name'] = 'wrapper_policy'
        objs = self.get_updated_ltm_objects(ltm_service_manager, Policy)
        assert 1 == len(objs)
        assert objs[0].name == 'wrapper_policy'

        # Should delete one Policy
        self.ltm_service['l7Policies'] = [] 
        objs = self.get_deleted_ltm_objects(ltm_service_manager, Policy)
        assert 1 == len(objs)
        assert 'wrapper_policy' == objs[0].name

    def test_internal_data_groups(self, ltm_service_manager):
        """Test create/update/delete of Internal Data Groups."""
        # Should create one Data Group 
        objs = self.get_created_ltm_objects(ltm_service_manager, InternalDataGroup)
        assert 1 == len(objs)
        assert objs[0].name == 'test-dgs'

        # Should update one Data Group
        self.ltm_service['internalDataGroups'][0]['name'] = 'test-dg'
        objs = self.get_updated_ltm_objects(ltm_service_manager, InternalDataGroup)
        assert 1 == len(objs)
        assert objs[0].name == 'test-dg'

        # Should delete one Data Group
        self.ltm_service['internalDataGroups'] = []
        objs = self.get_deleted_ltm_objects(ltm_service_manager, InternalDataGroup)
        assert 1 == len(objs)
        assert 'test-dg' == objs[0].name

    def test_irules(self, ltm_service_manager):
        """Test create/update/delete of iRules."""
        # Should create one iRule 
        objs = self.get_created_ltm_objects(ltm_service_manager, IRule)
        assert 1 == len(objs)
        assert objs[0].name == 'https_redirect'

        # Should update one iRule
        self.ltm_service['iRules'][0]['name'] = 'https_redirector'
        objs = self.get_updated_ltm_objects(ltm_service_manager, IRule)
        assert 1 == len(objs)
        assert objs[0].name == 'https_redirector'

        # Should delete one iRule
        self.ltm_service['iRules'] = [] 
        objs = self.get_deleted_ltm_objects(ltm_service_manager, IRule)
        assert 1 == len(objs)
        assert 'https_redirector' == objs[0].name

    def test_arps(self, net_service_manager):
        """Test create/update/delete of arps."""
        # Should create one Arp
        objs = self.get_created_net_objects(net_service_manager, Arp)
        assert 1 == len(objs)
        assert objs[0].name == 'test-arp1'

        # Should update one Arp
        self.net_service['arps'][0]['name'] = 'arp1'
        objs = self.get_updated_net_objects(net_service_manager, Arp)
        assert 1 == len(objs)
        assert objs[0].name == 'arp1'

        # Should delete one Arp
        self.net_service['arps'] = []
        objs = self.get_deleted_net_objects(net_service_manager, Arp)
        assert 1 == len(objs)
        assert 'arp1' == objs[0].name

    def test_fdb_tunnels(self, net_service_manager):
        """Test create/update/delete of fdbTunnels."""
        # Should create one tunnel
        objs = self.get_created_net_objects(net_service_manager, FDBTunnel)
        assert 1 == len(objs)
        assert objs[0].name == 'test-tunnel1'

        # Should update one tunnel
        self.net_service['fdbTunnels'][0]['name'] = 'tunnel1'
        objs = self.get_updated_net_objects(net_service_manager, FDBTunnel)
        assert 1 == len(objs)
        assert objs[0].name == 'tunnel1'

        # Should delete one tunnel
        self.net_service['fdbTunnels'] = []
        objs = self.get_deleted_net_objects(net_service_manager, FDBTunnel)
        assert 1 == len(objs)
        assert 'tunnel1' == objs[0].name
