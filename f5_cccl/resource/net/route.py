"""Provides a class for managing BIG-IP Route resources."""
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

from f5_cccl.resource import Resource


LOGGER = logging.getLogger(__name__)


class Route(Resource):
    """Route class for managing network configuration on BIG-IP."""
    properties = dict(name=None,
                      partition=None,
                      network=None,
                      gw=None)

    def __init__(self, name, partition, **data):
        """Create an Route entry from CCCL routeType."""
        super(Route, self).__init__(name, partition)

        for key, value in list(self.properties.items()):
            if key in ["name", "partition"]:
                continue
            self._data[key] = data.get(key, value)

    def __eq__(self, other):
        if not isinstance(other, Route):
            LOGGER.warning(
                "Invalid comparison of Route object with object "
                "of type %s", type(other))
            return False

        for key in self.properties:
            if self._data[key] != other.data.get(key, None):
                return False

        return True

    def __hash__(self):  # pylint: disable=useless-super-delegation
        return super(Route, self).__hash__()

    def _uri_path(self, bigip):
        return bigip.tm.net.routes.route


class IcrRoute(Route):
    """Route object created from the iControl REST object."""
    pass


class ApiRoute(Route):
    """Route object created from the API configuration object."""
    pass
