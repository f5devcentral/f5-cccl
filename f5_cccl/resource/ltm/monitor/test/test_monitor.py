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

import pytest

from mock import MagicMock

import f5_cccl.exceptions as exceptions
import f5_cccl.resource.ltm.monitor.monitor as target


api_monitors_cfg = [
    { "name": "myhttp",
      "type": "http",
      "send": "GET /\r\n",
      "recv": "SERVER" },
    { "name": "my_ping",
      "type": "icmp" },
    { "name": "my_tcp",
      "type": "tcp" },
    { "name": "myhttp",
      "type": "https",
      "send": "GET /\r\n",
      "recv": "HTTPS-SERVER" }
]


name = "test_monitor"
partition = "Test"


@pytest.fixture
def http_monitor():
    return api_monitors_cfg[0]


@pytest.fixture
def icmp_monitor():
    return api_monitors_cfg[1]


@pytest.fixture
def tcp_monitor():
    return api_monitors_cfg[2]


@pytest.fixture
def https_monitor():
    return api_monitors_cfg[3]


def test__eq__():
    monitor1 = target.Monitor(name=name, partition=partition)
    monitor2 = target.Monitor(name=name, partition=partition)

    assert monitor1 == monitor2


def test__init__():

    monitor = target.Monitor(name=name, partition=partition)
    assert monitor

    monitor_data = monitor.data
    assert monitor_data
    assert monitor_data['interval'] == 5
    assert monitor_data['timeout'] == 16
    assert not monitor_data.get('send', None)
    assert not monitor_data.get('recv', None)


def test__init__xtra_params():
    properties = {'foo': 'xtra1', 'send': "GET /\r\n"}

    monitor = target.Monitor(name=name,
                             partition=partition,
                             **properties)
    assert monitor

    monitor_data = monitor.data
    assert monitor_data
    assert monitor_data['interval'] == 5
    assert monitor_data['timeout'] == 16
    assert monitor_data.get('send',"GET /\r\n")
    assert not monitor_data.get('foo', None)


def test__str__():
    monitor = target.Monitor(name=name,
                             partition=partition)
    class_str = "<class \'f5_cccl.resource.ltm.monitor.monitor.Monitor\'>"
    assert str(monitor) == (
        "Monitor(partition: Test, name: test_monitor, type: {})".format(
            class_str))


def test_uri_path():
    monitor = target.Monitor(name=name,
                             partition=partition)
    with pytest.raises(NotImplementedError):
        monitor._uri_path(MagicMock())


def test_invalid_interval_and_timeout():
    monitors = list(api_monitors_cfg)
    for mon in monitors:
        mon['interval'] = 10
        mon['timeout'] = 5
        with pytest.raises(ValueError):
            monitor = target.Monitor(partition=partition, **mon)
