u"""This module provides a class for managing a BIG-IP."""
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

from copy import copy

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from f5.bigip import ManagementRoot

from f5_cccl.resource.ltm.app_service import ApplicationService
from f5_cccl.resource.ltm.monitor.http_monitor import IcrHTTPMonitor
from f5_cccl.resource.ltm.monitor.https_monitor import IcrHTTPSMonitor
from f5_cccl.resource.ltm.monitor.icmp_monitor import IcrICMPMonitor
from f5_cccl.resource.ltm.monitor.tcp_monitor import IcrTCPMonitor
from f5_cccl.resource.ltm.policy import IcrPolicy
from f5_cccl.resource.ltm.pool import IcrPool
from f5_cccl.resource.ltm.virtual_address import IcrVirtualAddress
from f5_cccl.resource.ltm.virtual import IcrVirtualServer
from f5_cccl.resource.ltm.node import Node

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class CommonBigIP(ManagementRoot):
    """CommonBigIP class.

    Manages the resources for the partition(s) of the specified BIG-IP

    - Token-based authentication is used by specifying a token named 'tmos'.
      This will allow non-admin users to use the API (BIG-IP must configure
      the accounts with proper permissions, for either local or remote auth).

    Args:
        hostname: IP address of BIG-IP
        port: Port of BIG-IP
        username: BIG-IP username
        password: BIG-IP password
        partitions: List of BIG-IP partitions to manage
        token: The optional auth token to use with BIG-IP (e.g. "tmos")
    """

    def __init__(self, hostname, username, password, partition, prefix=None,
                 port=443, token=None, manage_types=None):
        """Initialize the CommonBigIP object."""
        super_kwargs = {"port": port}
        if token:
            super_kwargs["token"] = token
        super(CommonBigIP, self).__init__(hostname, username, password,
                                          **super_kwargs)
        self._hostname = hostname
        self._port = port
        self._username = username
        self._password = password
        self._partition = partition
        self._prefix = ""

        if prefix:
            self._prefix = prefix

        # This currently hard codes what resources we care about until we
        # enable policy management.
        if manage_types is None:
            manage_types = ['/tm/ltm/virtual', '/tm/ltm/pool',
                            '/tm/ltm/monitor', '/tm/sys/application/service']

        self._manage_virtual = '/tm/ltm/virtual' in manage_types
        self._manage_pool = '/tm/ltm/pool' in manage_types
        self._manage_monitor = '/tm/ltm/monitor' in manage_types
        self._manage_policy = '/tm/ltm/policy' in manage_types
        self._manage_iapp = '/tm/sys/application/service' in manage_types

        # BIG-IP resources
        self._virtuals = dict()
        self._pools = dict()
        self._all_pools = dict()
        self._policies = dict()
        self._iapps = dict()
        self._monitors = dict()
        self._nodes = dict()

    def _manageable_resource(self, rsc):
        """Determine if the resource will be managed.

        Resource will be managed if it matches prefix and does not belong
        to an appService (iApp)

        Args:
            rsc: A BIG-IP resource
        """
        return rsc.name.startswith(self._prefix) and \
            getattr(rsc, 'appService', None) is None

    def find_unreferenced_virtual_addrs(self):
        """The list of virtual addresses to remove from existing config."""
        virtual_addrs = copy(self._virtual_addresses)
        all_virtuals = self._all_virtuals

        for virtual in all_virtuals:
            (virtual_addr) = all_virtuals[virtual].destination[2]
            virtual_addrs.pop(virtual_addr, None)

        return virtual_addrs

    def refresh(self):
        """Refresh the internal cache with the BIG-IP state."""
        partition_filter = "$filter=partition+eq+{}".format(self._partition)

        #  Retrieve the list of virtual servers in managed partition.
        query = partition_filter

        #  Retrieve the lists of health monitors
        http_monitors = self.tm.ltm.monitor.https.get_collection(
            requests_params={"params": query})
        https_monitors = self.tm.ltm.monitor.https_s.get_collection(
            requests_params={"params": query})
        tcp_monitors = self.tm.ltm.monitor.tcps.get_collection(
            requests_params={"params": query})
        icmp_monitors = (
            self.tm.ltm.monitor.gateway_icmps.get_collection(
                requests_params={"params": query})
        )
        iapps = self.tm.sys.application.services.get_collection(
            requests_params={"params": query})
        nodes = self.tm.ltm.nodes.get_collection(
            requests_params={"params": query})
        virtual_addresses = self.tm.ltm.virtual_address_s.get_collection(
            requests_params={"params": query})

        #  Retrieve the list of virtuals, pools, and policies in the
        #  managed partition getting all subCollections.
        query = "{}&expandSubcollections=true".format(partition_filter)
        virtuals = self.tm.ltm.virtuals.get_collection(
            requests_params={"params": query})

        pools = self.tm.ltm.pools.get_collection(
            requests_params={"params": query})

        policies = self.tm.ltm.policys.get_collection(
            requests_params={"params": query})

        #  Refresh the virtuals cache.
        self._virtuals = {
            v.name: IcrVirtualServer(**v.raw) for v in virtuals
            if self._manageable_resource(v)
        }

        #  Refresh the virtuals cache.
        self._all_virtuals = {
            v.name: IcrVirtualServer(**v.raw) for v in virtuals
        }

        #  Refresh the virtual address cache.
        self._virtual_addresses = {
            v.name: IcrVirtualAddress(**v.raw) for v in virtual_addresses
            if self._manageable_resource(v)
        }

        #  Refresh the pool cache
        self._pools = {
            p.name: IcrPool(**p.raw) for p in pools
            if self._manageable_resource(p)
        }

        #  Refresh the all-pool cache
        self._all_pools = {
            p.name: IcrPool(**p.raw) for p in pools
        }

        #  Refresh the policy cache
        self._policies = {
            p.name: IcrPolicy(**p.raw) for p in policies
            if self._manageable_resource(p)
        }

        #  Refresh the iapp cache
        self._iapps = {
            i.name: ApplicationService(**i.raw) for i in iapps
            if i.name.startswith(self._prefix)
        }

        #  Refresh the node cache
        self._nodes = {
            n.name: Node(**n.raw) for n in nodes
        }

        #  Refresh the health monitor cache
        self._monitors['http'] = {
            m.name: IcrHTTPMonitor(**m.raw) for m in http_monitors
            if self._manageable_resource(m)
        }
        self._monitors['https'] = {
            m.name: IcrHTTPSMonitor(**m.raw) for m in https_monitors
            if self._manageable_resource(m)
        }
        self._monitors['tcp'] = {
            m.name: IcrTCPMonitor(**m.raw) for m in tcp_monitors
            if self._manageable_resource(m)
        }
        self._monitors['icmp'] = {
            m.name: IcrICMPMonitor(**m.raw) for m in icmp_monitors
            if self._manageable_resource(m)
        }

    def get_virtuals(self, all_virtuals=False):
        """Return the index of virtual servers."""
        if all_virtuals:
            return self._all_virtuals

        return self._virtuals

    def get_pools(self, all_pools=False):
        """Return the index of pools."""
        if all_pools:
            return self._all_pools
        return self._pools

    def get_app_svcs(self):
        """Return the index of app services."""
        return self._iapps

    def get_monitors(self, hm_type=None):
        """Get all monitors or those of type, hm_type."""
        if hm_type:
            monitors = self._monitors.get(hm_type, dict())
        else:
            monitors = self._monitors

        return monitors

    def get_http_monitors(self):
        """Return the index of HTTP monitors."""
        return self.get_monitors('http')

    def get_tcp_monitors(self):
        """Return the index of TCP monitors."""
        return self.get_monitors('tcp')

    def get_https_monitors(self):
        """Return the index of HTTPS monitors."""
        return self.get_monitors('https')

    def get_icmp_monitors(self):
        """Return the index of gateway ICMP monitors."""
        return self.get_monitors('icmp')

    def get_l7policies(self):
        """Return the index of L7 policies."""
        return self._policies

    def get_iapps(self):
        """Return the index of iApps."""
        return self._iapps

    def get_nodes(self):
        """Return the index of nodes."""
        return self._nodes

    def get_virtual_addresses(self):
        """Return the index of virtual_addresses."""
        return self._virtual_addresses
