"""Provides a class for managing BIG-IP iRule resources."""
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


LOGGER = logging.getLogger(__name__)


def get_record_key(record):
    """Allows data groups to be sorted by the 'name' member."""
    return record.get('name', '')


class InternalDataGroup(Resource):
    """InternalDataGroup class."""
    # The property names class attribute defines the names of the
    # properties that we wish to compare.
    properties = dict(
        name=None,
        partition=None,
        type=None,
        records=list()
    )

    def __init__(self, name, partition, **data):
        """Create the InternalDataGroup"""
        super(InternalDataGroup, self).__init__(name, partition)

        self._data['type'] = data.get('type', '')
        records = data.get('records', list())
        self._data['records'] = sorted(records, key=get_record_key)

    def __eq__(self, other_dg):
        """Check the equality of the two objects.

        Only compare the properties as defined in the
        properties class dictionany.
        """
        if not isinstance(other_dg, InternalDataGroup):
            return False
        for key in self.properties:
            if self._data[key] != other_dg.data.get(key, None):
                return False
        return True

    def __hash__(self):  # pylint: disable=useless-super-delegation
        return super(InternalDataGroup, self).__hash__()

    def _uri_path(self, bigip):
        return bigip.tm.ltm.data_group.internals.internal

    def __str__(self):
        return str(self._data)

    def update(self, bigip, data=None, modify=False):
        """Override of base class implemntation, required because data-groups
           are picky about what data can exist in the object when modifying.
        """
        tmp_copy = deepcopy(self)
        tmp_copy.do_update(bigip, data, modify)

    def do_update(self, bigip, data, modify):
        """Remove 'type' before doing the update."""
        del self._data['type']
        super(InternalDataGroup, self).update(
            bigip, data=data, modify=modify)


class IcrInternalDataGroup(InternalDataGroup):
    """InternalDataGroup object created from the iControl REST object"""
    pass


class ApiInternalDataGroup(InternalDataGroup):
    """InternalDataGroup object created from the API configuration object"""
    pass
