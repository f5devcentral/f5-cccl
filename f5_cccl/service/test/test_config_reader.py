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

from f5_cccl import F5CloudServiceManager
from f5_cccl.bigip import CommonBigIP
from f5_cccl.resource import ltm

from f5_cccl.service.manager import ServiceConfigDeployer
from f5_cccl.service.config_reader import ServiceConfigReader

from mock import MagicMock
from mock import Mock
from mock import patch

class TestServiceConfigReader:

    def setup(self):
        self.partition = "Test"

        svcfile = 'f5_cccl/schemas/tests/service.json'
        with open(svcfile, 'r') as fp:
            self.service = json.loads(fp.read())

    def test_create_reader(self):
        reader = ServiceConfigReader(
            self.partition)

        assert reader
        assert reader._partition == self.partition

    def test_get_config(self):
        reader = ServiceConfigReader(self.partition)
        config = reader.read_config(self.service)

        assert len(config.get('virtuals')) == 1
        assert len(config.get('pools')) == 1
        assert len(config.get('http_monitors')) == 1
        assert len(config.get('https_monitors')) == 1
        assert len(config.get('icmp_monitors')) == 1
        assert len(config.get('tcp_monitors')) == 1
        assert not len(config.get('policies'))
        assert not len(config.get('iapps'))
