"""Provides a class for managing BIG-IP Application Service resources."""
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


class ApplicationService(Resource):
    """Application Service class for managing configuration on BIG-IP."""

    properties = dict(template=None,
                      options={},
                      variables=[],
                      tables=[])

    def __init__(self, name, partition, **properties):
        """Create an Application Service instance."""
        super(ApplicationService, self).__init__(name, partition)

        for key, value in self.properties.items():
            if key == "options":
                self._data.update(properties.get(key, value))
            else:
                self._data[key] = properties.get(key, value)

    def __eq__(self, other):
        if not isinstance(other, ApplicationService):
            raise ValueError(
                "Invalid comparison of Application Service object with object "
                "of type {}".format(type(other)))

        for key in self._data:
            if self._data[key] != other.data.get(key, None):
                return False
        return True

    def __hash__(self):  # pylint: disable=useless-super-delegation
        return super(ApplicationService, self).__hash__()

    def _uri_path(self, bigip):
        return bigip.tm.sys.application.services.service

    def create(self, bigip):
        """Create an iApp Application Service.

        Args:
            bigip (f5.bigip.ManagementRoot): F5 SDK session object
        """
        super(ApplicationService, self).create(bigip)

    def update(self, bigip):
        """Update an iApp Application Service.

        Args:
            bigip (f5.bigip.ManagementRoot): F5 SDK session object
        """
        self._data['executeAction'] = 'definition'
        super(ApplicationService, self).update(bigip)
