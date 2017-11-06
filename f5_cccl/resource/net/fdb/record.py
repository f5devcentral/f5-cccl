"""Provides a class for managing BIG-IP FDB tunnel record resources."""
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


LOGGER = logging.getLogger(__name__)


class Record(Resource):
    """Record class for managing network configuration on BIG-IP."""
    properties = dict(name=None, endpoint=None)

    def __init__(self, name, **data):
        """Create a record from CCCL recordType."""
        super(Record, self).__init__(name, partition=None)
        self._data['endpoint'] = data.get('endpoint', None)

    def __eq__(self, other):
        if not isinstance(other, Record):
            return False

        return super(Record, self).__eq__(other)

    def _uri_path(self, bigip):
        raise NotImplementedError
