#!/usr/bin/env python
"""Hosts an interface for the BIG-IP Monitor Resource.

This module references and holds items relevant to the orchestration of the F5
BIG-IP for purposes of abstracting the F5-SDK library.
"""
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

from collections import namedtuple

import f5
import f5_cccl.exceptions as exceptions

from f5_cccl.resource import Resource

logger = logging.getLogger(__name__)
default_schema = dict(interval=5, recv='', send="GET /\\r\\n", timeout=16)


class Monitor(Resource):
    """Creates a CCCL BIG-IP Monitor Object of sub-type of Resource

    This object hosts the ability to orchestrate basic CRUD actions against a
    BIG-IP Monitor via the F5-SDK.
    """
    monitor_schema_kvps = None
    _data = dict()

    def __cmp__(self, compare):
        return self.__eq__(compare)

    @property
    def __dict__(self):
        return self._data

    def __eq__(self, compare):
        myself = self.__dict__
        if isinstance(compare, Monitor):
            compare = compare.__dict__
        if isinstance(compare, f5.bigip.resource.Resource):
            compare = compare.raw
        elif not isinstance(compare, dict):
            raise TypeError("comparison is not against another Monitor"
                            " or dict ({})".format(type(compare)))
        for item in self.monitor_schema_kvps._asdict().keys():
            value = compare.get(item, None)
            my_value = myself.get(item, None)
            if not my_value == value and (my_value or value):
                # empty strings should be seen as "None" coming back from the
                # BIG-IP...
                return False
        return True

    def __hash__(self):
        return hash("{}{}{}".format(self.partition, self.name, self.__class__))

    def __init__(self, name, partition, **kwargs):
        if not self.monitor_schema_kvps:
            raise EnvironmentError("Could not derive pre-defined schema!")
        expected = self.monitor_schema_kvps._asdict()
        my_type = kwargs.get('type', None)
        if my_type and my_type.upper() not in str(type(self)):
            raise exceptions.F5CcclResourceCreateError(
                "Wrong child chosen for monitor type({}) I am({})".format(
                    my_type, type(self)))
        elif not my_type:  # follow by "best effort"
            print('my_type', my_type)
            msg = \
                "Assuming that monitor of type({}) is okay for '{}:{}'".format(
                    type(self), partition, name)
            logger.debug(msg)
        if not name or not partition:
            raise exceptions.F5CcclResourceCreateError(
                "must have at least name({}) and partition({})".format(
                    name, partition))
        super(Monitor, self).__init__(name, partition)

        expected.update(kwargs)
        expected.update(self._data)
        self._data = expected

    def __ne__(self, compare):
        return False if self.__eq__(compare) else True

    def __str__(self):
        return("Monitor(partition: {}, name: {}, type: {}".format(
            self._data['partition'], self._data['name'], type(self)))

    def _uri_path(self, bigip):
        """Returns the bigip object instance's reference to the monitor object

        This method takes in a bigip and returns the uri reference for managing
        the monitor object via the F5-SDK on the BIG-IP
        """
        raise NotImplementedError("No default monitor implemented")

    def create(self, bigip):
        msg = "Creating Monitor '{}'".format(self._data['name'])
        logger.debug(msg)
        super(Monitor, self).create(bigip)

    def delete(self, bigip):
        msg = "Deleting Monitor '{}'".format(self._data['name'])
        logger.debug(msg)
        super(Monitor, self).delete(bigip)

    def read(self, bigip):
        msg = "Reading Monitor '{}'".format(self._data['name'])
        logger.debug(msg)
        return super(Monitor, self).read(bigip)

    def update(self, bigip, data=None, modify=True):
        msg = "Updating Monitor '{}'".format(self._data['name'])
        logger.debug(msg)
        super(Monitor, self).update(bigip, data=data, modify=modify)


def get_dynamic_schema():
    """Extracts the input schema's definition of the Monitor and returns

    This function is a module-level and will eventually be replaced once we
    have a solid means by which to extract this data.  Thus, this is a
    glorified placeholder.

    :params: Any
    :return: False - always
    """
    return False


def _entry():
    """A preliminary entry assignment vector function

    This function determines how Monitor will derive its default schema.
    """
    input_schema = get_dynamic_schema()
    winning_dict = input_schema if input_schema else default_schema
    Monitor.monitor_schema_kvps = \
        namedtuple('Monitor', winning_dict.keys())(**winning_dict)


if __name__ != '__main__':
    # Don't want bad users directly executing this...
    _entry()
