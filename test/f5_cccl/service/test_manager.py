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

from f5_cccl.bigip import BigIPProxy
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

from icontrol.exceptions import iControlUnexpectedHTTPError

from mock import MagicMock
from mock import Mock
from mock import patch

import logging

LOGGER = logging.getLogger(__name__)
LOGGER.setLevel(logging.DEBUG)

TEST_USER_AGENT='k8s-bigip-ctlr-v1.4.0'


req_symbols = ['bigip_mgmt_ip', 'bigip_username', 'bigip_password', 'bigip_port']


def missing_bigip_symbols():
    for sym in req_symbols:
        if not hasattr(pytest.symbols, sym):
            return True
    return False


pytestmark = pytest.mark.skipif(missing_bigip_symbols(),
                                reason="Need symbols pointing at a real bigip.")


@pytest.fixture
def bigip_proxy(bigip, partition):
    yield BigIPProxy(bigip, partition)


@pytest.fixture
def ltm_service_manager(bigip_proxy, partition):
    schema = 'f5_cccl/schemas/cccl-ltm-api-schema.yml'
    service_mgr = ServiceManager(
        bigip_proxy,
        partition,
        schema
    )
    return service_mgr


class TestServiceConfigDeployer:

    def _get_policy_from_bigip(self, name, bigip, partition):
        try:
            icr_policy = bigip.tm.ltm.policys.policy.load(
                name=name, partition=partition,
                requests_params={'params': "expandSubcollections=true"})
            code = 200
        except iControlUnexpectedHTTPError as err:
            icr_policy = None
            code = err.response.status_code

        return icr_policy, code

    def test_deploy_ltm(self, bigip, partition, ltm_service_manager):
        ltm_svcfile = 'f5_cccl/schemas/tests/test_policy_schema_01.json'
        with open(ltm_svcfile, 'r') as fp:
            test_service1 = json.loads(fp.read())

        policy1 = test_service1['l7Policies'][0]['name']
        tasks_remaining = ltm_service_manager.apply_ltm_config(
            test_service1, TEST_USER_AGENT
        )
        assert 0 == tasks_remaining

        # Get the policy from the bigip.
        (icr_policy, code) = self._get_policy_from_bigip(
            policy1, bigip, partition
        )

        # Assert object exists and test attributes.
        assert icr_policy
        assert icr_policy.raw['name'] == policy1

        tasks_remaining = ltm_service_manager.apply_ltm_config(
            {}, TEST_USER_AGENT
        )
        assert 0 == tasks_remaining
