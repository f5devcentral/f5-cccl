"""Manages the creation and deployment of desired services configuration."""
# coding=utf-8
#
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




import logging

import f5_cccl.exceptions as cccl_error
# LTM resources
from f5_cccl.resource.ltm.monitor.http_monitor import ApiHTTPMonitor
from f5_cccl.resource.ltm.monitor.https_monitor import ApiHTTPSMonitor
from f5_cccl.resource.ltm.monitor.icmp_monitor import ApiICMPMonitor
from f5_cccl.resource.ltm.monitor.tcp_monitor import ApiTCPMonitor
from f5_cccl.resource.ltm.monitor.udp_monitor import ApiUDPMonitor
from f5_cccl.resource.ltm.irule import ApiIRule
from f5_cccl.resource.ltm.policy import ApiPolicy
from f5_cccl.resource.ltm.pool import ApiPool
from f5_cccl.resource.ltm.virtual import ApiVirtualServer
from f5_cccl.resource.ltm.virtual_address import ApiVirtualAddress
from f5_cccl.resource.ltm.app_service import ApiApplicationService
from f5_cccl.resource.ltm.internal_data_group import ApiInternalDataGroup

# NET resources
from f5_cccl.resource.net.arp import ApiArp
from f5_cccl.resource.net.fdb.tunnel import ApiFDBTunnel
from f5_cccl.resource.net.route import ApiRoute


LOGGER = logging.getLogger(__name__)


class ServiceConfigReader(object):
    """Class that loads a service defined by cccl-api-schema."""

    def __init__(self, partition):
        """Initializer."""
        self._partition = partition

    def _create_config_item(self, resource_type, obj,
                            default_route_domain=None, user_agent=None):
        """Create an API resource object and handle exceptions.

        This is a factory method to create resource objects in
        such a way that any exceptions that are raised might
        be handled and the appropriate F5CcclConfigurationReadError.

        :param resource_type: The type of resource to create.
        :param obj: The configuration object.
        :returns: A resource object.
        :rtype: f5_cccl.resource.Resource
        :raises:  f5_cccl.exceptions.F5CcclConfigurationReadError
        """
        config_resource = None

        # Update the object with metadata
        if user_agent is not None:

            metadata = {
                'metadata': [{
                    'name': 'user_agent',
                    'persist': 'true',
                    'value': user_agent
                }]
            }
            obj.update(metadata)

        try:
            if default_route_domain is not None:
                config_resource = resource_type(
                    partition=self._partition,
                    default_route_domain=default_route_domain,
                    **obj)
            else:
                config_resource = resource_type(
                    partition=self._partition,
                    **obj)
        except (ValueError, TypeError) as error:
            msg_format = \
                "Failed to create resource {}, {} from config: error({})"
            msg = msg_format.format(
                obj.get('name'), resource_type.__name__, str(error))
            LOGGER.error(msg)
            raise cccl_error.F5CcclConfigurationReadError(msg)

        return config_resource

    # pylint: disable=too-many-locals
    def read_ltm_config(self, service_config, default_route_domain,
                        user_agent):
        """Read the LTM service configuration and save as resource object."""
        config_dict = dict()
        config_dict['http_monitors'] = dict()
        config_dict['https_monitors'] = dict()
        config_dict['icmp_monitors'] = dict()
        config_dict['tcp_monitors'] = dict()
        config_dict['udp_monitors'] = dict()

        LOGGER.debug("Loading desired service configuration...")

        virtuals = service_config.get('virtualServers', list())
        config_dict['virtuals'] = {
            v['name']: self._create_config_item(ApiVirtualServer, v,
                                                default_route_domain,
                                                user_agent=user_agent)
            for v in virtuals
        }

        # Get the list of explicitly defined virtual addresses.
        virtual_addresses = service_config.get('virtualAddresses', list())
        config_dict['virtual_addresses'] = {
            va['name']: self._create_config_item(ApiVirtualAddress, va,
                                                 default_route_domain,
                                                 user_agent=user_agent)
            for va in virtual_addresses
        }

        pools = service_config.get('pools', list())
        config_dict['pools'] = {
            p['name']: self._create_config_item(ApiPool, p,
                                                default_route_domain,
                                                user_agent=user_agent)
            for p in pools
        }

        irules = service_config.get('iRules', list())
        config_dict['irules'] = {
            p['name']: self._create_config_item(ApiIRule, p,
                                                user_agent=user_agent)
            for p in irules
        }

        policies = service_config.get('l7Policies', list())
        config_dict['l7policies'] = {
            p['name']: self._create_config_item(ApiPolicy, p)
            for p in policies
        }

        internal_dgs = service_config.get('internalDataGroups', list())
        config_dict['internaldatagroups'] = {
            p['name']: self._create_config_item(ApiInternalDataGroup, p)
            for p in internal_dgs
        }

        monitors = service_config.get('monitors', list())
        for monitor in monitors:
            monitor_type = monitor.get('type', None)
            monitor_name = monitor.get('name', None)
            if monitor_type == "http":
                config_dict['http_monitors'].update(
                    {monitor_name: self._create_config_item(
                        ApiHTTPMonitor, monitor)})
            if monitor_type == "https":
                config_dict['https_monitors'].update(
                    {monitor_name: self._create_config_item(
                        ApiHTTPSMonitor, monitor)})
            if monitor_type == "icmp":
                config_dict['icmp_monitors'].update(
                    {monitor_name: self._create_config_item(
                        ApiICMPMonitor, monitor)})
            if monitor_type == "tcp":
                config_dict['tcp_monitors'].update(
                    {monitor_name: self._create_config_item(
                        ApiTCPMonitor, monitor)})
            if monitor_type == "udp":
                config_dict['udp_monitors'].update(
                    {monitor_name: self._create_config_item(
                        ApiUDPMonitor, monitor)})

        iapps = service_config.get('iapps', list())
        config_dict['iapps'] = {
            i['name']: self._create_config_item(ApiApplicationService, i,
                                                default_route_domain)
            for i in iapps
        }

        return config_dict

    def read_net_config(self, service_config, default_route_domain):
        """Read the NET service configuration and save as resource object."""
        config_dict = dict()

        arps = service_config.get('arps', list())
        config_dict['arps'] = {
            a['name']: self._create_config_item(ApiArp, a)
            for a in arps
        }

        tunnels = service_config.get('fdbTunnels', list())
        config_dict['fdbTunnels'] = {
            t['name']: self._create_config_item(ApiFDBTunnel, t,
                                                default_route_domain)
            for t in tunnels
        }

        user_tunnels = service_config.get('userFdbTunnels', list())
        config_dict['userFdbTunnels'] = {
            t['name']: self._create_config_item(ApiFDBTunnel, t,
                                                default_route_domain)
            for t in user_tunnels
        }

        routes = service_config.get('routes', list())
        config_dict['routes'] = {
            a['name']: self._create_config_item(ApiRoute, a)
            for a in routes
        }
        config_dict['cis-identifier'] = service_config.get('cis-identifier',str())

        return config_dict
