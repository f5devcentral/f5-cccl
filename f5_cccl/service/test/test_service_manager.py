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
from f5_cccl.service.manager import ServiceConfigDeployer
from f5_cccl.service.manager import ServiceManager
from f5_cccl.service.config_reader import ServiceConfigReader

from mock import MagicMock
from mock import Mock
from mock import patch

@pytest.fixture
def service_manager():
    partition = "test"
    schema = 'f5_cccl/schemas/cccl-api-schema.yml'

    service_mgr = ServiceManager(
        bigip_proxy(),
        partition,
        schema)

    return service_mgr


def test_apply_config(service_manager):
    services = {}

    assert service_manager.apply_config(services) == 0


class TestServiceConfigDeployer:

    def setup(self):
        self.bigip = bigip_proxy()
        self.partition = "test"

        svcfile = 'f5_cccl/schemas/tests/service.json'
        with open(svcfile, 'r') as fp:
            self.service = json.loads(fp.read())

        config_reader = ServiceConfigReader(self.partition)
        self.default_route_domain = self.bigip.get_default_route_domain()
        self.desired_config = config_reader.read_config(
            self.service, self.default_route_domain)

    def get_objects(self, objs, obj_type):
        """Extract objects of obj_type from the list."""
        objs = [obj for obj in objs if isinstance(obj, obj_type)]
        return objs

    def get_created_objects(self, service_manager, obj_type):
        """Return list of created objects."""
        deployer = service_manager._service_deployer
        deployer._create_resources = Mock(return_value=[])

        service_manager.apply_config(self.service)
        assert deployer._create_resources.called
        args, kwargs = deployer._create_resources.call_args_list[0]
        return self.get_objects(args[0], obj_type) 

    def get_updated_objects(self, service_manager, obj_type):
        """Return list of updated objects."""
        deployer = service_manager._service_deployer
        deployer._update_resources = Mock(return_value=[])

        service_manager.apply_config(self.service)
        assert deployer._update_resources.called
        args, kwargs = deployer._update_resources.call_args_list[0]
        return self.get_objects(args[0], obj_type) 

    def get_deleted_objects(self, service_manager, obj_type):
        """Return list of deleted objects."""
        deployer = service_manager._service_deployer
        deployer._delete_resources = Mock(return_value=[])

        service_manager.apply_config(self.service)
        assert deployer._delete_resources.called
        args, kwargs = deployer._delete_resources.call_args_list[0]
        return self.get_objects(args[0], obj_type) 

    def test_create_deployer(self):
        deployer = ServiceConfigDeployer(
            self.bigip)

        assert deployer

    def test_deploy(self):
        deployer = ServiceConfigDeployer(
            self.bigip)
        tasks_remaining = deployer.deploy(
            self.desired_config, self.default_route_domain)
        assert 0 == tasks_remaining

    def test_app_services(self, service_manager):
        """Test create/update/delete of app services."""
        # Should create one app service
        objs = self.get_created_objects(service_manager, ApplicationService)
        assert 1 == len(objs)
        assert objs[0].name == 'MyAppService0'

        # Should update one app service
        self.service['iapps'][0]['name'] = 'MyAppService'
        objs = self.get_updated_objects(service_manager, ApplicationService)
        assert 1 == len(objs)
        assert objs[0].name == 'MyAppService'

        # Should delete two app services
        self.service['iapps'] = []
        objs = self.get_deleted_objects(service_manager, ApplicationService)
        assert 2 == len(objs)
        expected_set = set(['appsvc', 'MyAppService'])
        result_set = set([objs[0].name, objs[1].name])
        assert expected_set == result_set

    def test_virtual_servers(self, service_manager):
        """Test create/update/delete of Virtual Servers."""
        # Should create one Virtual Server 
        objs = self.get_created_objects(service_manager, VirtualServer)
        assert 1 == len(objs)
        assert objs[0].name == 'vs1'

        # Should update one Virtual Server
        self.service['virtualServers'][0]['name'] = 'virtual2'
        objs = self.get_updated_objects(service_manager, VirtualServer)
        assert 1 == len(objs)
        assert objs[0].name == 'virtual2'

        # Should delete one Virtual Server
        self.service['virtualServers'] = [] 
        objs = self.get_deleted_objects(service_manager, VirtualServer)
        assert 1 == len(objs)
        assert 'virtual2' == objs[0].name

    def test_pools(self, service_manager):
        """Test create/update/delete of Pools."""
        # Should create one Pool 
        objs = self.get_created_objects(service_manager, Pool)
        assert 1 == len(objs)
        assert objs[0].name == 'pool2'

        # Should update one Pool
        self.service['pools'][0]['name'] = 'pool1'
        objs = self.get_updated_objects(service_manager, Pool)
        assert 1 == len(objs)
        assert objs[0].name == 'pool1'

        # Should delete one Pool
        self.service['pools'] = [] 
        objs = self.get_deleted_objects(service_manager, Pool)
        assert 1 == len(objs)
        assert 'pool1' == objs[0].name

    def test_monitors(self, service_manager):
        """Test create/update/delete of Health Monitors."""
        # Should create one Monitor 
        objs = self.get_created_objects(service_manager, HTTPMonitor)
        assert 1 == len(objs)
        assert objs[0].name == 'myhttp'

        # Should update one Monitor
        self.service['monitors'][0]['name'] = 'mon_http'
        objs = self.get_updated_objects(service_manager, HTTPMonitor)
        assert 1 == len(objs)
        assert objs[0].name == 'mon_http'

        # Should delete one Monitor
        self.service['monitors'] = [] 
        objs = self.get_deleted_objects(service_manager, HTTPMonitor)
        assert 1 == len(objs)
        assert 'mon_http' == objs[0].name

    def test_policies(self, service_manager):
        """Test create/update/delete of L7 Policies."""
        # Should create one Policy 
        objs = self.get_created_objects(service_manager, Policy)
        assert 1 == len(objs)
        assert objs[0].name == 'test_wrapper_policy'

        # Should update one Policy
        self.service['l7Policies'][0]['name'] = 'wrapper_policy'
        objs = self.get_updated_objects(service_manager, Policy)
        assert 1 == len(objs)
        assert objs[0].name == 'wrapper_policy'

        # Should delete one Policy
        self.service['l7Policies'] = [] 
        objs = self.get_deleted_objects(service_manager, Policy)
        assert 1 == len(objs)
        assert 'wrapper_policy' == objs[0].name

    def test_internal_data_groups(self, service_manager):
        """Test create/update/delete of Internal Data Groups."""
        # Should create one Data Group 
        objs = self.get_created_objects(service_manager, InternalDataGroup)
        assert 1 == len(objs)
        assert objs[0].name == 'test-dgs'

        # Should update one Data Group
        self.service['internalDataGroups'][0]['name'] = 'test-dg'
        objs = self.get_updated_objects(service_manager, InternalDataGroup)
        assert 1 == len(objs)
        assert objs[0].name == 'test-dg'

        # Should delete one Data Group
        self.service['internalDataGroups'] = [] 
        objs = self.get_deleted_objects(service_manager, InternalDataGroup)
        assert 1 == len(objs)
        assert 'test-dg' == objs[0].name

    def test_irules(self, service_manager):
        """Test create/update/delete of iRules."""
        # Should create one iRule 
        objs = self.get_created_objects(service_manager, IRule)
        assert 1 == len(objs)
        assert objs[0].name == 'https_redirect'

        # Should update one iRule
        self.service['iRules'][0]['name'] = 'https_redirector'
        objs = self.get_updated_objects(service_manager, IRule)
        assert 1 == len(objs)
        assert objs[0].name == 'https_redirector'

        # Should delete one iRule
        self.service['iRules'] = [] 
        objs = self.get_deleted_objects(service_manager, IRule)
        assert 1 == len(objs)
        assert 'https_redirector' == objs[0].name
