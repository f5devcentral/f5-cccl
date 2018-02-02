"""Provides a class for managing BIG-IP iRule resources."""
# coding=utf-8
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


class IRule(Resource):
    """iRule class."""
    # The property names class attribute defines the names of the
    # properties that we wish to compare.
    properties = dict(
        name=None,
        partition=None,
        apiAnonymous=None
    )

    def __init__(self, name, partition, **data):
        """Create the iRule"""
        super(IRule, self).__init__(name, partition, **data)

        self._data['metadata'] = data.get(
            'metadata',
            self.properties.get('metadata')
        )
        self._data['apiAnonymous'] = data.get(
            'apiAnonymous',
            self.properties.get('apiAnonymous')
        )
        # Strip any leading/trailing whitespace
        if self._data['apiAnonymous'] is not None:
            self._data['apiAnonymous'] = self._data['apiAnonymous'].strip()

    def __eq__(self, other):
        """Check the equality of the two objects.

        Only compare the properties as defined in the
        properties class dictionany.
        """
        if not isinstance(other, IRule):
            return False

        for key in self.properties:
            if self._data[key] != other.data.get(key, None):
                return False
        return True

    def __hash__(self):  # pylint: disable=useless-super-delegation
        return super(IRule, self).__hash__()

    def _uri_path(self, bigip):
        return bigip.tm.ltm.rules.rule

    def __str__(self):
        return str(self._data)


class IcrIRule(IRule):
    """iRule object created from the iControl REST object"""
    pass


class ApiIRule(IRule):
    """IRule object created from the API configuration object"""
    pass
