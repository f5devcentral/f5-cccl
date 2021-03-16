#!/usr/bin/env python
# Copyright (c) 2017-2021 F5 Networks, Inc.
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

from mock import MagicMock
import pytest

import f5_cccl.resource.ltm.monitor.icmp_monitor as target


@pytest.fixture
def icmp_config():
    return {"name": "test_monitor",
            "partition": "Test",
            "interval": 1,
            "timeout": 10}


@pytest.fixture
def bigip():
    bigip = MagicMock()
    return bigip


def test_create_w_defaults(icmp_config):
    monitor = target.ICMPMonitor(
        name=icmp_config['name'],
        partition=icmp_config['partition'])

    assert monitor
    assert monitor.name == "test_monitor"
    assert monitor.partition == "Test"
    data = monitor.data
    assert data.get('interval') == 5
    assert data.get('timeout') == 16


def test_create_w_config(icmp_config):
    monitor = target.ICMPMonitor(
        **icmp_config
    )

    assert monitor
    assert monitor.name == "test_monitor"
    assert monitor.partition == "Test"
    data = monitor.data
    assert data.get('interval') == 1
    assert data.get('timeout') == 10


def test_get_uri_path(bigip, icmp_config):
    monitor = target.ICMPMonitor(**icmp_config)

    assert (monitor._uri_path(bigip) ==
            bigip.tm.ltm.monitor.gateway_icmps.gateway_icmp)


def test_create_icr_monitor(icmp_config):
    monitor = target.IcrICMPMonitor(**icmp_config)

    assert isinstance(monitor, target.ICMPMonitor)


def test_create_api_monitor(icmp_config):
    monitor = target.ApiICMPMonitor(**icmp_config)

    assert isinstance(monitor, target.ICMPMonitor)


def test_create_monitors_invalid(icmp_config):
    # Set interval to be larger than timeout,
    # ICR Monitor will be created, API Monitor will not
    icmp_config['interval'] = 30
    monitor = target.IcrICMPMonitor(**icmp_config)

    assert isinstance(monitor, target.IcrICMPMonitor)

    with pytest.raises(ValueError):
        monitor = target.ApiICMPMonitor(**icmp_config)
