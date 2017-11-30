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
import logging
from operator import itemgetter
import re

from f5_cccl.resource import Resource
from f5_cccl.resource.ltm.profile import Profile


LOGGER = logging.getLogger(__name__)


class VirtualServer(Resource):
    """Virtual Server class for managing configuration on BIG-IP."""

    ipv4_dest_pattern = re.compile(
        "\\/([a-zA-Z][\\w_\\.-]+)\\/" +
        "((?:[a-zA-Z0-9_\\-\\.]+)(?:%\\d+)?):(\\d+)$"
    )
    ipv6_dest_pattern = re.compile(
        "\\/([a-zA-Z][\\w_\\.-]+)\\/" +
        "((?:[a-fA-F0-9:]+)(?:%\\d+)?)\\.(\\d+)$"
    )

    properties = dict(description=None,
                      destination=None,
                      source=None,
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
                      profiles=list(),
                      rules=list())

    def __init__(self, name, partition, **properties):
        """Create a Virtual server instance."""
        super(VirtualServer, self).__init__(name, partition)

        for key, default in self.properties.items():
            if key in ["profiles", "policies"]:
                prop = properties.get(key, default)
                self._data[key] = sorted(prop, key=itemgetter('name'))
            elif key == "vlans":
                self._data['vlans'] = sorted(properties.get('vlans', default))
            elif key == "sourceAddressTranslation":
                self._data['sourceAddressTranslation'] = copy(
                    properties.get('sourceAddressTranslation', default))
            else:
                value = properties.get(key, default)
                if value is not None:
                    self._data[key] = value

    @property
    def destination(self):
        """Return the destination of the virtual server.

        Return:
        (destination, partition, name, port)
        """
        match = None
        for pattern in [self.ipv4_dest_pattern, self.ipv6_dest_pattern]:
            match = pattern.match(self._data['destination'])
            if match:
                destination = match.group(0, 1, 2, 3)
                break
        else:
            print("unexpected destination address format")
            destination = (self._data['destination'], None, None, None)

        return destination

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
    def __init__(self, name, partition, **properties):
        """Handle the mutually exclusive properties."""

        enabled = properties.pop('enabled', True)
        if not enabled:
            disabled = True
            enabled = None
        else:
            disabled = None

        vlansEnabled = properties.pop('vlansEnabled', False)
        if not vlansEnabled:
            vlansDisabled = True
            vlansEnabled = None
        else:
            vlansDisabled = None

        destination = properties.get('destination', None)
        rd = None
        if '%' in destination:
            try:
                rd = re.findall(r"%(\d+)(:|.)", destination)[0][0]
            except IndexError:
                LOGGER.error(
                    "Could not extract route domain from destination '%s'",
                    destination)

        source = properties.pop('source', '0.0.0.0/0')
        if rd and '%' not in source:
            idx = source.index('/')
            source = source[:idx] + '%{}'.format(rd) + source[idx:]

        super(ApiVirtualServer, self).__init__(name,
                                               partition,
                                               enabled=enabled,
                                               disabled=disabled,
                                               vlansEnabled=vlansEnabled,
                                               vlansDisabled=vlansDisabled,
                                               source=source,
                                               **properties)


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

    def _flatten_profiles(self, **properties):
        profiles = list()
        profiles_reference = properties.pop('profilesReference', dict())

        items = profiles_reference.get('items', list())
        for item in items:
            try:
                profiles.append(Profile(**item).data)
            except ValueError as error:
                LOGGER.error(
                    "Virtual Create Error: failed to create profile: %s",
                    error)

        return profiles

    def _flatten_policies(self, **properties):
        policies = list()
        policies_reference = properties.pop('policiesReference', dict())

        items = policies_reference.get('items', list())
        for item in items:
            policies.append(dict(name=item['name'],
                                 partition=item['partition']))

        return policies
