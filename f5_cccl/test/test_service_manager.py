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

from f5_cccl.service_manager import F5CloudServiceManager
from mock import MagicMock
import pytest


@pytest.fixture
def service_manager():
    bigip = MagicMock()
    partition = "Test"

    service_mgr = F5CloudServiceManager(
        bigip,
        partition)

    return service_mgr


def test_apply_config(service_manager):
    services = {}

    assert service_manager.apply_config(services)
