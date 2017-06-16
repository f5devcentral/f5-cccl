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


from f5_cccl.resource import Resource


class Node(Resource):
    """Node class for managing configuration on BIG-IP."""

    properties = dict(name=None,
                      partition=None,
                      address=None,
                      state=None,
                      session=None)

    def __init__(self, name, partition, **properties):
        """Create a Node instance."""
        super(Node, self).__init__(name, partition)

        for key, value in self.properties.items():
            if key == "name" or key == "partition":
                continue

            self._data[key] = properties.get(key, value)

    def __eq__(self, other):
        if not isinstance(other, Node):
            raise ValueError(
                "Invalid comparison of Node object with object "
                "of type {}".format(type(other)))

        if self.name != other.name:
            return False
        if self.partition != other.partition:
            return False
        if self._data['address'] != other.data['address']:
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
