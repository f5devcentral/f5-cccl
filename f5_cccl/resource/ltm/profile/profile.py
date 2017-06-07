"""Provides a class for managing BIG-IP Profile resources."""
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


class Profile(Resource):
    """Virtual Server class for managing configuration on BIG-IP."""

    properties = dict(name=None,
                      partition=None,
                      context="all")

    def __init__(self, name, partition, **properties):
        """Create a Virtual server instance."""
        super(Profile, self).__init__(name, partition)
        self._data['context'] = properties.get('context', "all")

    def __eq__(self, other):
        if not isinstance(other, Profile):
            return False

        return super(Profile, self).__eq__(other)

    def _uri_path(self, bigip):
        """"""
        raise NotImplementedError

    def __repr__(self):
        return 'Profile(%r, %r, context=%r)' % (self._data['name'],
                                                self._data['partition'],
                                                self._data['context'])
