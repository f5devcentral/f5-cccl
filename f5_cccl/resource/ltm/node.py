"""Provides a class for managing BIG-IP Node resources."""
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

from copy import deepcopy
import logging

from f5_cccl.resource import Resource
from f5_cccl.utils.route_domain import normalize_address_with_route_domain


LOGGER = logging.getLogger(__name__)


class Node(Resource):
    """Node class for managing configuration on BIG-IP."""

    properties = dict(name=None,
                      partition=None,
                      address=None,
                      state=None,
                      session=None)

    def __init__(self, name, partition, default_route_domain, **properties):
        """Create a Node instance."""
        super(Node, self).__init__(name, partition)
        self._default_route_domain = default_route_domain

        for key, value in self.properties.items():
            if key == "name" or key == "partition":
                continue

            self._data[key] = properties.get(key, value)

    def __eq__(self, other):
        if not isinstance(other, Node):
            LOGGER.warning(
                "Invalid comparison of Node object with object "
                "of type %s", type(other))
            return False

        if self.name != other.name:
            return False
        if self.partition != other.partition:
            return False
        self_ip_rd = normalize_address_with_route_domain(
            self._data['address'], self._default_route_domain)[0]
        other_ip_rd = normalize_address_with_route_domain(
            other.data['address'], self._default_route_domain)[0]
        if self_ip_rd != other_ip_rd:
            return False

        # Check equivalence of states
        if other.data['state'] == 'up' or other.data['state'] == 'unchecked':
            if 'enabled' in other.data['session']:
                return True
        return False

    def __hash__(self):  # pylint: disable=useless-super-delegation
        return super(Node, self).__hash__()

    def _uri_path(self, bigip):
        return bigip.tm.ltm.nodes.node

    def update(self, bigip, data=None, modify=False):
        # 'address' is immutable, don't pass it in an update operation
        tmp_data = deepcopy(data) if data is not None else deepcopy(self.data)
        tmp_data.pop('address', None)
        super(Node, self).update(bigip, data=tmp_data, modify=modify)


class IcrNode(Node):
    """Node instantiated from iControl REST pool member object."""
    pass
