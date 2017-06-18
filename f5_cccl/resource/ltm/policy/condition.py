"""Provides a class for managing BIG-IP L7 Rule Action resources."""
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

from __future__ import print_function

from f5_cccl.resource import Resource


class Condition(Resource):
    """L7 Rule Action class."""
    # The property names class attribute defines the names of the
    # properties that we wish to compare.
    properties = {
        "name": None,
        "request": True,

        "equals": None,
        "endsWith": None,
        "startsWith": None,
        "contains": None,

        "not": None,
        "missing": None,
        "caseSensitive": None,

        "httpHost": False,
        "host": False,

        "httpUri": False,
        "pathSegment": False,
        "path": False,
        "extension": False,
        "index": None,

        "httpHeader": False,
        "httpCookie": False,

        "tmName": None,
        "values": list()
    }

    def __init__(self, name, data):
        super(Condition, self).__init__(name, partition=None)

        self._data['request'] = True

        values = sorted(data.get('values', list()))
        tm_name = data.get('tmName', None)
        condition_map = dict()

        # Does this rule match the HTTP hostname?
        if data.get('httpHost', False):
            condition_map = {'httpHost': True, 'host': True, 'values': values}

        # Does this rule match a part of the HTTP URI?
        elif data.get('httpUri', False):
            condition_map = {'httpUri': True, 'values': values}
            if data.get('path', False):
                condition_map['path'] = True
            elif data.get('pathSegment', False):
                condition_map['pathSegment'] = True
                condition_map['index'] = data.get('index', 1)
            elif data.get('extension', False):
                condition_map['extension'] = True
            else:
                raise ValueError("must specify one of path, pathSegment, or "
                                 "extension for HTTP URI matching condition")

        # Does this rule match an HTTP header?
        elif data.get('httpHeader', False):
            condition_map = {
                'httpHeader': True, 'tmName': tm_name, 'values': values}

        # Does this rule match an HTTP cookie?
        elif data.get('httpCookie', False):
            condition_map = {
                'httpCookie': True, 'tmName': tm_name, 'values': values}

        else:
            raise ValueError("Invalid match type must be one of: httpHost, "
                             "httpUri, httpHeader, or httpCookie")

        self._data.update(condition_map)

        # This condition attributes should not be set if they are not defined.
        # For example, having a comparison option set to 'None' will conflict
        # with the one that is set to 'True'
        match_options = ['not', 'missing', 'caseSensitive']
        comparisons = ['contains', 'equals', 'startsWith', 'endsWith']
        for key in match_options + comparisons:
            value = data.get(key, None)
            if value:
                self._data[key] = value

    def __eq__(self, other):
        """Check the equality of the two objects.

        Do a data to data comparison as implemented in Resource.
        """
        if not isinstance(other, Condition):
            return False

        return super(Condition, self).__eq__(other)

    def __str__(self):
        return str(self._data)

    def _uri_path(self, bigip):
        """Return the URI path of an rule object.

        Not implemented because the current implementation does
        not manage Rules individually."""
        raise NotImplementedError
