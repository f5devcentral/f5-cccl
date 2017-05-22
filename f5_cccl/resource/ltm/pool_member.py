u"""This module provides class for managing member configuration."""
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

import re

from f5_cccl.resource import Resource
from netaddr import IPAddress
from requests.utils import quote as urlquote


class PoolMember(Resource):
    u"""PoolMember class for deploying configuration on BIG-IP?

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
        name = self._strip_route_domain_zero(name)
        super(PoolMember, self).__init__(name, partition)

        self._pool = pool
        for key, value in self.properties.items():
            if key == 'name' or key == 'partition':
                continue
            self._data[key] = properties.get(key, value)

    def __hash__(self):
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

    def _strip_route_domain_zero(self, name):
        """Remove the route domain from the address, if 0."""
        match = self.member_name_re.match(name)
        if match and match.group(2) == "0":
            ip_address = IPAddress(match.group(1))
            if ip_address.version == 4:
                name = "{}:{}".format(
                    match.group(1), match.group(3))
            else:
                name = "{}.{}".format(
                    match.group(1), match.group(3))
        return name

    def _uri_path(self, bigip):
        if not self._pool:
            raise NotImplementedError

        with self._pool.read(bigip) as pool:
            return pool.members_s.members

    @property
    def name(self):
        u"""Override the name property to get quoted format.

        This handles the '%' route domain marker.
        """
        return urlquote(self._data['name'])


class BigIPPoolMember(PoolMember):
    """PoolMember instantiated from F5 SDK pool member object."""
    pass


class F5CcclPoolMember(PoolMember):
    """PoolMember instantiated from F5 CCCL schema input."""
    def __init__(self, name, partition, pool=None, **properties):
        u"""Create a PoolMember instance from CCCL PoolMemberType.

        Args:
            name (string): The name of the member <address>:<port>
            If this is defined as None, the name will be computed
            from the address and port.
            partition (string): Pool member partition
            pool (Pool): Parent pool object

        Properties:
            address (string): Member IP address
            port (int): Member service port
            routeDomain (dict): Route domain id and name
            ratio (int): Member weight for ratio-member lb algorithm
            connectionLimit (int): Max number of connections
            priorityGroup (int): Member priority group
            state (string): Member admin state, user-up or user-down
            description (string): User specified description
        """
        if not name:
            address = properties.get('address', None)
            port = properties.get('port', None)
            route_domain = properties.get('routeDomain', {})

            name = self._init_member_name(
                address,
                port,
                route_domain)

        super(F5CcclPoolMember, self).__init__(name=name,
                                               partition=partition,
                                               pool=pool,
                                               **properties)

    @staticmethod
    def _init_member_name(address, port, route_domain):
        u"""Initialize the pool member address.

        An address is of the form:
        <ip_address>%<route_domain_id>
        """
        if not address or not port:
            raise TypeError(
                "F5CCCL poolMember definition must contain address and port")

        ip_address = IPAddress(address)
        rd_id = route_domain.get('id', 0)
        if rd_id:
            if ip_address.version == 4:
                name_format = "{}%{}:{}"
            else:
                name_format = "{}%{}.{}"
            name = name_format.format(address, rd_id, port)
        else:
            if ip_address.version == 4:
                name_format = "{}:{}"
            else:
                name_format = "{}.{}"
            name = name_format.format(address, port)

        return name
