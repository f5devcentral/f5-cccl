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

from f5_cccl.resource.ltm.pool import BigIPPool
from f5.bigip import BigIP
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


class CommonBigIP(BigIP):
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

    def __init__(self, hostname, port, username, password, partitions,
                 token=None, manage_types=None):
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
        self._partitions = partitions

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
        self._virtuals = []
        self._pools = []
        self._polices = []
        self._iapps = []
        self._monitors = []

    def refresh(self):
        """Refresh the internal cache with the BIG-IP state."""
        new_pools = []
        pools = self.ltm.pools.get_collection(
            requests_params={"params": "expandSubcollections=true"})

        for p in pools:
            pool = BigIPPool(**p.__dict__)
            new_pools.append(pool)

        self._pools = new_pools

        # TODO: Refresh iapps, virtuals, monitors, and policies
