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
from f5_cccl.test.conftest import big_ip
import pdb
from f5_cccl.bigip import CommonBigIP
from f5_cccl.resource import ltm

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
        big_ip(),
        partition,
        schema)

    return service_mgr


def test_apply_config(service_manager):
    services = {}

    assert service_manager.apply_config(services) == 0


class TestServiceConfigDeployer:

    def setup(self):
        self.bigip = big_ip()
        self.partition = "test"

        svcfile = 'f5_cccl/schemas/tests/service.json'
        with open(svcfile, 'r') as fp:
            self.service = json.loads(fp.read())

        config_reader = ServiceConfigReader(self.partition)
        self.desired_config = config_reader.read_config(self.service)

    def test_create_deployer(self):
        deployer = ServiceConfigDeployer(
            self.bigip)

        assert deployer

    def test_deploy(self):

        deployer = ServiceConfigDeployer(
            self.bigip)
        tasks_remaining = deployer.deploy(self.desired_config)
        assert 0 == tasks_remaining


    def test_app_services(self, service_manager):
        """Test create/update/delete of app services."""
        deployer = service_manager._service_deployer

        # Should create one app service
        deployer._create_resources = Mock(return_value=[])
        service_manager.apply_config(self.service)
        assert deployer._create_resources.called
        args, kwargs = deployer._create_resources.call_args_list[0]
        print(args)
        assert 7 == len(args[0])
        assert args[0][6].name == 'MyAppService0'

        # Should update one app service
        self.service['iapps'][0]['name'] = 'MyAppService'
        deployer._update_resources = Mock(return_value=[])
        service_manager.apply_config(self.service)
        assert deployer._update_resources.called
        args, kwargs = deployer._update_resources.call_args_list[0]
        assert 3 == len(args[0])
        assert args[0][2].name == 'MyAppService'

        # Should delete two app services
        self.service = {}
        deployer._delete_resources = Mock(return_value=[])
        service_manager.apply_config(self.service)

        assert deployer._delete_resources.called
        args, kwargs = deployer._delete_resources.call_args_list[0]
        assert 8 == len(args[0])
        expected_set = set(['appsvc', 'MyAppService'])
        result_set = set([args[0][0].name, args[0][1].name])
        assert expected_set == result_set

        # Should not delete resources owned by iApps
        for rsc in args[0][2:]:
            assert not rsc.name.startswith('appsvc')
            assert not rsc.name.startswith('MyAppService')
