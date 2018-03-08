"""Hosts an interface for the BIG-IP Monitor Resource.

This module references and holds items relevant to the orchestration of the F5
BIG-IP for purposes of abstracting the F5-SDK library.
"""
#
# Copyright (c) 2017,2018, F5 Networks, Inc.
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


class Monitor(Resource):
    """Creates a CCCL BIG-IP Monitor Object of sub-type of Resource

    This object hosts the ability to orchestrate basic CRUD actions against a
    BIG-IP Monitor via the F5-SDK.
    """
    properties = dict(timeout=16, interval=5)

    def __eq__(self, compare):
        myself = self._data

        if isinstance(compare, Monitor):
            compare = compare.data

        return myself == compare

    def __init__(self, name, partition, **kwargs):
        super(Monitor, self).__init__(name, partition)

        for key, value in self.properties.items():
            self._data[key] = kwargs.get(key, value)

        # Check for invalid interval/timeout values
        if self._data['interval'] >= self._data['timeout']:
            raise ValueError(
                "Health Monitor interval ({}) must be less than "
                "timeout ({})".format(self._data['interval'],
                                      self._data['timeout']))

    def __str__(self):
        return("Monitor(partition: {}, name: {}, type: {})".format(
            self._data['partition'], self._data['name'], type(self)))

    def _uri_path(self, bigip):
        """Returns the bigip object instance's reference to the monitor object

        This method takes in a bigip and returns the uri reference for managing
        the monitor object via the F5-SDK on the BIG-IP
        """
        raise NotImplementedError("No default monitor implemented")
