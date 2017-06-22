"""Manages the creation and deployment of desired services configuration."""
# coding=utf-8
#
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

from __future__ import print_function

from f5_cccl.resource.ltm.monitor.http_monitor import ApiHTTPMonitor
from f5_cccl.resource.ltm.monitor.https_monitor import ApiHTTPSMonitor
from f5_cccl.resource.ltm.monitor.icmp_monitor import ApiICMPMonitor
from f5_cccl.resource.ltm.monitor.tcp_monitor import ApiTCPMonitor
from f5_cccl.resource.ltm.policy import ApiPolicy
from f5_cccl.resource.ltm.pool import ApiPool
from f5_cccl.resource.ltm.virtual import ApiVirtualServer
from f5_cccl.resource.ltm.app_service import ApplicationService


class ServiceConfigReader(object):
    """Class that loads a service defined by cccl-api-schema."""
    def __init__(self, partition):
        """Initializer."""
        self._partition = partition

    def read_config(self, service_config):
        """Read the service configuration and save as resource object."""
        config_dict = dict()
        config_dict['http_monitors'] = dict()
        config_dict['https_monitors'] = dict()
        config_dict['icmp_monitors'] = dict()
        config_dict['tcp_monitors'] = dict()

        virtuals = service_config.get('virtualServers', list())
        config_dict['virtuals'] = {
            v['name']: ApiVirtualServer(partition=self._partition, **v)
            for v in virtuals
        }

        pools = service_config.get('pools', list())
        config_dict['pools'] = {
            p['name']: ApiPool(partition=self._partition, **p)
            for p in pools
        }

        policies = service_config.get('l7Policies', list())
        config_dict['l7policies'] = {
            p['name']: ApiPolicy(partition=self._partition, **p)
            for p in policies
        }

        monitors = service_config.get('monitors', list())
        for monitor in monitors:
            monitor_type = monitor.get('type', None)
            monitor_name = monitor.get('name', None)
            if monitor_type == "http":
                config_dict['http_monitors'].update(
                    {monitor_name: ApiHTTPMonitor(
                        partition=self._partition,
                        **monitor)})
            if monitor_type == "https":
                config_dict['https_monitors'].update(
                    {monitor_name: ApiHTTPSMonitor(
                        partition=self._partition,
                        **monitor)})
            if monitor_type == "icmp":
                config_dict['icmp_monitors'].update(
                    {monitor_name: ApiICMPMonitor(
                        partition=self._partition,
                        **monitor)})
            if monitor_type == "tcp":
                config_dict['tcp_monitors'].update(
                    {monitor_name: ApiTCPMonitor(
                        partition=self._partition,
                        **monitor)})

        iapps = service_config.get('iapps', list())
        config_dict['iapps'] = {
            i['name']: ApplicationService(partition=self._partition, **i)
            for i in iapps
        }

        return config_dict
