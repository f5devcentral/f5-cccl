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

from f5_cccl.resource.ltm.monitor.http_monitor import HTTPMonitor
from f5_cccl.resource.ltm.monitor.https_monitor import HTTPSMonitor
from f5_cccl.resource.ltm.monitor.icmp_monitor import ICMPMonitor
from f5_cccl.resource.ltm.monitor.tcp_monitor import TCPMonitor
from f5_cccl.resource.ltm.pool import BigIPPool
from f5_cccl.resource.ltm.virtual import VirtualServer
from f5_cccl.resource.ltm.app_service import ApplicationService

from f5.bigip import ManagementRoot
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning


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
        self._polices = dict()
        self._iapps = dict()
        self._monitors = dict()

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

        #  Retrieve the list of pools in managed partition
        query = "{}&expandSubcollections=true".format(partition_filter)
        virtuals = self.tm.ltm.virtuals.get_collection(
            requests_params={"params": query})

        pools = self.tm.ltm.pools.get_collection(
            requests_params={"params": query})

        #  Retrieve the list of policies in the managed partition
        # FIXME: Refresh policies
        # policies = self.tm.ltm.policys.get_collection(
        #    requests_params={"params": query})
        self._virtuals = {
            v.name: VirtualServer(**v.raw) for v in virtuals
            if v.name.startswith(self._prefix)
        }

        #  Refresh the pool cache
        self._pools = {
            p.name: BigIPPool(**p.raw) for p in pools
            if p.name.startswith(self._prefix)
        }

        #  Refresh the iapp cache
        self._iapps = {
            i.name: ApplicationService(**i.raw) for i in iapps
            if i.name.startswith(self._prefix)
        }

        #  Refresh the health monitor cache
        self._monitors['http'] = {
            m.name: HTTPMonitor(**m.raw) for m in http_monitors
            if m.name.startswith(self._prefix)
        }
        self._monitors['https'] = {
            m.name: HTTPSMonitor(**m.raw) for m in https_monitors
            if m.name.startswith(self._prefix)
        }
        self._monitors['tcp'] = {
            m.name: TCPMonitor(**m.raw) for m in tcp_monitors
            if m.name.startswith(self._prefix)
        }
        self._monitors['icmp'] = {
            m.name: ICMPMonitor(**m.raw) for m in icmp_monitors
            if m.name.startswith(self._prefix)
        }

    @property
    def virtuals(self):
        """Return the index of virtual servers."""
        return self._virtuals

    @property
    def pools(self):
        """Return the index of pools."""
        return self._pools

    @property
    def app_svcs(self):
        """Return the index of app services."""
        return self._iapps

    @property
    def http_monitors(self):
        """Return the index of HTTP monitors."""
        return self._monitors.get('http', dict())

    @property
    def tcp_monitors(self):
        """Return the index of TCP monitors."""
        return self._monitors.get('tcp', dict())

    @property
    def https_monitors(self):
        """Return the index of HTTPS monitors."""
        return self._monitors.get('https', dict())

    @property
    def icmp_monitors(self):
        """Return the index of gateway ICMP monitors."""
        return self._monitors.get('icmp', dict())
