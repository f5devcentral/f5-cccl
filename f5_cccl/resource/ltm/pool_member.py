"""This module provides class for managing member configuration."""
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
import re

from netaddr import IPAddress
from requests.utils import quote as urlquote
from f5_cccl.resource import Resource
from f5_cccl.utils.route_domain import normalize_address_with_route_domain


LOGGER = logging.getLogger(__name__)


class PoolMember(Resource):
    """PoolMember class for deploying configuration on BIG-IP?

    Encapsulate an PoolMember configuration object as defined by BIG-IP
    into a dictionary
    """
    # The property names class attribute defines the names of the
    # properties that we wish to compare.
    properties = dict(name=None,
                      partition=None,
                      ratio=1,
                      connectionLimit=0,
                      priorityGroup=0,
                      session="user-enabled",
                      description=None)
    member_name_re = re.compile("^(.*:?)%(\\d+)[\\.|\\:](\\d+)$")

    def __init__(self, name, partition, pool=None, **properties):
        """Initialize the PoolMember object."""
        super(PoolMember, self).__init__(name, partition)

        self._pool = pool
        for key, value in list(self.properties.items()):
            if key in ['name', 'partition']:
                continue
            self._data[key] = properties.get(key, value)

    def __hash__(self):  # pylint: disable=useless-super-delegation
        return super(PoolMember, self).__hash__()

    def __eq__(self, other):
        """Check the equality of the two objects.

        Only compare the properties as defined in the
        properties class dictionary.
        """
        if not isinstance(other, PoolMember):
            return False

        for key in self.properties:
            if self._data[key] != other.data.get(key, None):

                if key == "session":
                    if self._check_states(other):
                        continue

                return False

        return True

    def _check_states(self, other):
        """Compare desired admin state to operational state."""
        other_session = other.data['session']

        return ("monitor" in self.data['session'] or
                "monitor" in other_session)

    def _uri_path(self, bigip):
        if not self._pool:
            LOGGER.error(
                "Performing REST operation on pool member not supported.")
            raise NotImplementedError

        with self._pool.read(bigip) as pool:
            return pool.members_s.members

    @property
    def name(self):
        """Override the name property to get quoted format.

        This handles the '%' route domain marker.
        """
        return urlquote(self._data['name'])


class IcrPoolMember(PoolMember):
    """PoolMember instantiated from iControl REST pool member object."""
    pass


class ApiPoolMember(PoolMember):
    """PoolMember instantiated from F5 CCCL schema input."""

    def __init__(self, partition, default_route_domain, pool, **properties):
        """Create a PoolMember instance from CCCL PoolMemberType.

        Args:
            If this is defined as None, the name will be computed
            from the address and port.
            partition (string): Pool member partition
            default_route_domain (string): For managed partition
            pool (Pool): Parent pool object

        Properties:
            address (string): Member IP address
            port (int): Member service port
            ratio (int): Member weight for ratio-member lb algorithm
            connectionLimit (int): Max number of connections
            priorityGroup (int): Member priority group
            state (string): Member admin state, user-up or user-down
            description (string): User specified description
        """
        address = properties.get('address', None)
        port = properties.get('port', None)
        name = self._init_member(address, port, default_route_domain)

        super(ApiPoolMember, self).__init__(name=name,
                                            partition=partition,
                                            pool=pool,
                                            **properties)

    @staticmethod
    def _init_member(address, port, default_route_domain):
        """Initialize the pool member name and address.

        An address is of the form:
        <ip_address>[%<route_domain_id>]
        """
        if not address or not port:
            LOGGER.error(
                "pool member definition must contain address and port")
            raise TypeError(
                "F5CCCL poolMember definition must contain address and port")

        # force address to include route domain
        address, ip, _ = normalize_address_with_route_domain(
            address, default_route_domain)

        ip_address = IPAddress(ip)

        # force name to be defined as <ip>%<rd>:<port>
        if ip_address.version == 4:
            name_format = "{}:{}"
        else:
            name_format = "{}.{}"
        name = name_format.format(address, port)

        return name
