"""Provides a class for managing BIG-IP Virtual Server resources."""
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

from copy import copy
from operator import itemgetter

from f5_cccl.resource import Resource
from f5_cccl.resource.ltm.profile import Profile


class VirtualServer(Resource):
    """Virtual Server class for managing configuration on BIG-IP."""

    properties = dict(description=None,
                      destination=None,
                      ipProtocol=None,
                      enabled=None,
                      disabled=None,
                      vlansEnabled=None,
                      vlansDisabled=None,
                      vlans=list(),
                      sourceAddressTranslation=dict(),
                      connectionLimit=0,
                      pool=None,
                      policies=list(),
                      profiles=list())

    def __init__(self, name, partition, **properties):
        """Create a Virtual server instance."""
        super(VirtualServer, self).__init__(name, partition)

        for key, value in self.properties.items():
            if key in ["profiles", "policies"]:
                prop = properties.get(key, value)
                self._data[key] = sorted(prop, key=itemgetter('name'))
            elif key == "vlans":
                self._data['vlans'] = sorted(properties.get('vlans', list()))
            elif key == "sourceAddressTranslation":
                self._data['sourceAddressTranslation'] = copy(
                    properties.get('sourceAddressTranslation', dict()))
            else:
                self._data[key] = properties.get(key, value)

        # Ensure the vlansEnabled options, enabled and disabled are mutually
        # exclusive.
        if self._data.get('vlansEnabled'):
            self._data.pop('vlansDisabled', None)
        elif self._data.get('vlansDisabled'):
            self._data.pop('vlansEnabled', None)

    def __eq__(self, other):
        if not isinstance(other, VirtualServer):
            return False

        return super(VirtualServer, self).__eq__(other)

    def __hash__(self):  # pylint: disable=useless-super-delegation
        return super(VirtualServer, self).__hash__()

    def _uri_path(self, bigip):
        return bigip.tm.ltm.virtuals.virtual


class ApiVirtualServer(VirtualServer):
    """Parse the CCCL input to create the canonical Virtual Server."""
    pass


class IcrVirtualServer(VirtualServer):
    """Parse the iControl REST input to create the canonical Virtual Server."""
    def __init__(self, name, partition, **properties):
        """Remove some of the properties that are not required."""
        self._filter_virtual_properties(**properties)

        profiles = self._flatten_profiles(**properties)
        policies = self._flatten_policies(**properties)

        super(IcrVirtualServer, self).__init__(name,
                                               partition,
                                               profiles=profiles,
                                               policies=policies,
                                               **properties)

    def _filter_virtual_properties(self, **properties):
        """Remove any unneeded properties from the ICR response."""

        # Remove the pool reference property in sourceAddressTranslation
        snat_translation = properties.get('sourceAddressTranslation', dict())
        snat_translation.pop('poolReference', None)

        # Flatten the profiles reference.

    def _flatten_profiles(self, **properties):
        profiles = list()
        profiles_reference = properties.pop('profilesReference', dict())

        items = profiles_reference.get('items', list())
        for item in items:
            profiles.append(Profile(**item).data)

        return profiles

    def _flatten_policies(self, **properties):
        policies = list()
        policies_reference = properties.pop('policiesReference', dict())

        items = policies_reference.get('items', list())
        for item in items:
            policies.append(dict(name=item['name'],
                                 partition=item['partition']))

        return policies
