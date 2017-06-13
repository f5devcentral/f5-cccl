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
                      options=[
                          'description',
                          'inheritedTrafficGroup',
                          'inheritedDevicegroup',
                          'trafficGroup',
                          'deviceGroup'],
                      variables=[],
                      tables=[])

    def __init__(self, name, partition, **properties):
        """Create an Application Service instance."""
        super(ApplicationService, self).__init__(name, partition)

        for key, value in self.properties.items():
            if key == "options":
                if key in properties:
                    self._data.update(properties.get(key, value))
                for opt in value:
                    if opt in properties:
                        self._data[opt] = properties.get(opt, value)
            else:
                self._data[key] = properties.get(key, value)

                if key == "variables":
                    # Remove 'encrypted' key and its value from ICR data
                    for v in self._data[key]:
                        v.pop('encrypted', None)

    def __eq__(self, other):
        if not isinstance(other, ApplicationService):
            raise ValueError(
                "Invalid comparison of Application Service object with object "
                "of type {}".format(type(other)))

        if not all(v in self._data['variables']
                   for v in other.data['variables']):
            return False
        if not all(t in self._data['tables'] for t in other.data['tables']):
            return False

        for key in self._data:
            if key == "variables" or key == "tables":
                # already compared
                continue
            if self._data[key] != other.data.get(key, None):
                # FIXME (rtalley): description is overwritten in appsvcs
                # integration iApps this is a workaround until F5Networks/
                # f5-application-services-integration-iApp #43 is resolved
                if (key != 'description' or
                        'appsvcs_integration' not in self._data['template']):
                    return False
        return True

    def __hash__(self):  # pylint: disable=useless-super-delegation
        return super(ApplicationService, self).__hash__()

    def _uri_path(self, bigip):
        return bigip.tm.sys.application.services.service

    def update(self, bigip, data=None, modify=False):
        """Update an iApp Application Service.

        Args:
            bigip (f5.bigip.ManagementRoot): F5 SDK session object
        """
        self._data['executeAction'] = 'definition'
        super(ApplicationService, self).update(bigip, data=data, modify=modify)
