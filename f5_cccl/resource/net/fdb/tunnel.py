"""Provides a class for managing BIG-IP FDB tunnel resources."""
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

import logging

from f5_cccl.resource import Resource
from f5_cccl.resource.net.fdb.record import Record


LOGGER = logging.getLogger(__name__)


class FDBTunnel(Resource):
    """FDBTunnel class for managing network configuration on BIG-IP."""
    properties = dict(name=None,
                      partition=None,
                      records=list())

    def __init__(self, name, partition, default_route_domain, **data):
        """Create a tunnel from CCCL fdbTunnelType."""
        super(FDBTunnel, self).__init__(name, partition)

        records = data.get('records', list())
        self._data['records'] = self._create_records(
            default_route_domain, records)

    def __eq__(self, other):
        if not isinstance(other, FDBTunnel):
            LOGGER.warning(
                "Invalid comparison of FDBTunnel object with object "
                "of type %s", type(other))
            return False

        for key in self.properties:
            if key == 'records':
                if len(self._data[key]) != len(other.data[key]):
                    return False
                for record in self._data[key]:
                    if record not in other.data[key]:
                        return False
                    else:
                        idx = other.data[key].index(record)
                        if record != other.data[key][idx]:
                            return False
                continue
            if self._data[key] != other.data.get(key):
                return False

        return True

    def _create_records(self, default_route_domain, records):
        """Create a list of records for the tunnel."""
        new_records = list()
        for record in records:
            record['default_route_domain'] = default_route_domain
            new_records.append(Record(**record).data)
        return new_records

    def __hash__(self):  # pylint: disable=useless-super-delegation
        return super(FDBTunnel, self).__hash__()

    def _uri_path(self, bigip):
        return bigip.tm.net.fdb.tunnels.tunnel


class IcrFDBTunnel(FDBTunnel):
    """FDBTunnel object created from the iControl REST object."""
    pass


class ApiFDBTunnel(FDBTunnel):
    """FDBTunnel object created from the API configuration object."""
    pass
