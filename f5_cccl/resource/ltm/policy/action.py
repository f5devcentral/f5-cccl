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

import logging

from f5_cccl.resource import Resource


LOGGER = logging.getLogger(__name__)


class Action(Resource):
    """L7 Rule Action class."""
    # The property names class attribute defines the names of the
    # properties that we wish to compare.
    properties = dict(
        expression=None,
        forward=False,
        location=None,
        pool=None,
        redirect=False,
        request=True,
        reset=False,
        setVariable=False,
        tcl=False,
        tmName=None,
    )

    def __init__(self, name, data):
        """Initialize the Action object.

        Actions do not have explicit partition attributes, the are
        implied by the partition of the rule to which they belong.
        """
        super(Action, self).__init__(name, partition=None)

        # Actions are Only supported on requests.
        self._data['request'] = True

        # Is this a forwarding action?
        if data.get('forward', False):

            self._data['forward'] = True

            # Yes, there are two supported forwarding actions:
            # forward to pool and reset, these are mutually
            # exclusive options.
            pool = data.get('pool', None)
            reset = data.get('reset', False)
            if pool:
                self._data['pool'] = pool
            elif reset:
                self._data['reset'] = reset
            else:
                raise ValueError(
                    "Unsupported forward action, must be one of reset or "
                    "forward to pool.")
        # Is this a redirect action?
        elif data.get('redirect', False):
            self._data['redirect'] = True

            # Yes, set the location and httpReply attribute
            self._data['location'] = data.get('location', None)
            self._data['httpReply'] = data.get('httpReply', True)
        # Is this a setVariable action?
        elif data.get('setVariable', False):
            self._data['setVariable'] = True

            # Set the variable name and the value
            self._data['tmName'] = data.get('tmName', None)
            self._data['expression'] = data.get('expression', None)
            self._data['tcl'] = True
        else:
            # Only forward, redirect and setVariable are supported.
            raise ValueError("Unsupported action, must be one of forward, "
                             "redirect, setVariable or reset.")

    def __eq__(self, other):
        """Check the equality of the two objects.

        Do a straight data to data comparison.
        """
        if not isinstance(other, Action):
            return False

        return super(Action, self).__eq__(other)

    def __str__(self):
        return str(self._data)

    def _uri_path(self, bigip):
        """Return the URI path of an action object.

        Not implemented because the current implementation does
        not manage Actions individually."""
        raise NotImplementedError
