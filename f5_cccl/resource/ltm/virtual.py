"""Provides a class for managing BIG-IP Virtual Server resources."""
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


class VirtualServer(Resource):
    """Virtual Server class for managing configuration on BIG-IP."""

    properties = dict(name=None,
                      partition=None,
                      description=None,
                      destination=None,
                      servicePort=None,
                      ipProtocol=None,
                      pool=None,
                      profilesReference={},
                      policiesReference={})

    def __init__(self, name, partition, **properties):
        """Create a Virtual server instance."""
        super(VirtualServer, self).__init__(name, partition)

        for key, value in self.properties.items():
            if key == "name" or key == "partition":
                continue
            self._data[key] = properties.get(key, value)

    def __eq__(self, other):
        if not isinstance(other, VirtualServer):
            raise ValueError(
                "Invalid comparison of Virtual object with object "
                "of type {}".format(type(other)))

        for key in self.properties:
            if self._data[key] != other.data.get(key, None):
                return False

        return True

    def __hash__(self):  # pylint: disable=useless-super-delegation
        return super(VirtualServer, self).__hash__()

    def _uri_path(self, bigip):
        return bigip.tm.ltm.virtuals.virtual
