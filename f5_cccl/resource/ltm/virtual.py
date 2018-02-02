"""Provides a class for managing BIG-IP Virtual Server resources."""
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

from __future__ import print_function

from copy import copy
import logging
import re
from operator import itemgetter
from netaddr import IPAddress

from f5_cccl.resource import Resource
from f5_cccl.resource.ltm.profile import Profile
from f5_cccl.utils.route_domain import normalize_address_with_route_domain


LOGGER = logging.getLogger(__name__)


class VirtualServer(Resource):
    """Virtual Server class for managing configuration on BIG-IP."""

    # FIXME(kenr): This assumes API will include a one-level
    #              path (i.e. the partition)
    ipv4_dest_pattern = re.compile(
        "\\/([a-zA-Z][\\w_\\.-]+)\\/" +
        "((?:[a-zA-Z0-9_\\-\\.]+)(?:%\\d+)?):(\\d+)$"
    )
    ipv6_dest_pattern = re.compile(
        "\\/([a-zA-Z][\\w_\\.-]+)\\/" +
        "((?:[a-fA-F0-9:]+)(?:%\\d+)?)\\.(\\d+)$"
    )
    source_pattern = re.compile(
        r'([\w.:]+)/(\d+)'
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

    def __init__(self, name, partition, default_route_domain, **properties):
        """Create a Virtual server instance."""
        super(VirtualServer, self).__init__(name, partition, **properties)

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

        # Need to normalize destination and source fields with route domain ID
        try:
            self.normalizeAddresses(default_route_domain)
        # pylint: disable=broad-except
        except Exception as error:
            LOGGER.error(
                "Virtual Server address normalization error: %s", error)

    def normalizeAddresses(self, default_rd):
        '''Normalize destination and source fields to include route domain

        Adds the default route domain to the destination field if one is
        not provided.

        Also adds the destination route domain to the source field if it
        does not proivde one (probably could just force it since they both
        have to be in the same route domain).
        '''

        # Save the route domain info for use with the source field.
        ip_ver = 4
        dest_rd = default_rd
        if self._data.get('destination') is not None:
            # Add route domain if not supplied
            path, bigip_addr, port = self.destination[1:]
            bigip_addr, dest_ip, dest_rd = normalize_address_with_route_domain(
                bigip_addr, default_rd)
            ip_address = IPAddress(dest_ip)
            ip_ver = ip_address.version
            # force name to be defined as <ip>%<rd>:<port>
            if ip_ver == 4:
                dest_format = '/{}/{}:{}'
            else:
                dest_format = '/{}/{}.{}'
            self._data['destination'] = dest_format.format(
                path, bigip_addr, port)

        source = self._data.get('source')
        if source is None:
            if ip_ver == 4:
                source = '0.0.0.0%{}/0'.format(dest_rd)
            else:
                source = '::%{}/0'.format(dest_rd)
        else:
            match = self.source_pattern.match(source)
            if match:
                bigip_addr = match.group(1)
                mask = match.group(2)
                bigip_addr = normalize_address_with_route_domain(
                    bigip_addr, dest_rd)[0]
                source = '{}/{}'.format(bigip_addr, mask)
        self._data['source'] = source

    def find_profile(self, profile, other_profiles):
        """Find a profile in a list, accounting for the optional context."""
        for other in other_profiles:
            if profile.get('context', None) is not None:
                # if context exists, compare
                if profile == other:
                    return True
            else:
                # otherwise, remove context from comparison
                o = copy(other)
                o.pop('context', None)
                if profile == o:
                    return True

        return False

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
            LOGGER.error("unexpected destination address format")
            destination = (self._data['destination'], None, None, None)

        return destination

    def post_merge_adjustments(self):
        """Re-sort order of resource properties after merge"""

        for prop in ["profiles", "policies", "vlans"]:
            if prop in self._data:
                key = 'vlans' if prop == 'vlans' else 'name'
                self._data[prop] = sorted(self._data[prop],
                                          key=itemgetter(key))
        super(VirtualServer, self).post_merge_adjustments()

    def __eq__(self, other):
        if not isinstance(other, VirtualServer):
            return False

        for key in self._data:
            # compare list lengths
            if isinstance(self._data[key], list) and \
                    len(self._data[key]) != len(other.data.get(key, None)):
                return False

            if key == 'vlans' or key == 'policies' or key == 'rules':
                if sorted(self._data[key]) != \
                        sorted(other.data.get(key, None)):
                    return False
                continue

            if key == 'profiles':
                for profile in self._data[key]:
                    if not self.find_profile(profile,
                                             other.data.get(key, None)):
                        return False
                continue

            # All other types
            if self._data[key] != other.data.get(key, None):
                return False

        return True

    def __hash__(self):  # pylint: disable=useless-super-delegation
        return super(VirtualServer, self).__hash__()

    def _uri_path(self, bigip):
        return bigip.tm.ltm.virtuals.virtual


class ApiVirtualServer(VirtualServer):
    """Parse the CCCL input to create the canonical Virtual Server."""
    def __init__(self, name, partition, default_route_domain, **properties):
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

        super(ApiVirtualServer, self).__init__(name,
                                               partition,
                                               default_route_domain,
                                               enabled=enabled,
                                               disabled=disabled,
                                               vlansEnabled=vlansEnabled,
                                               vlansDisabled=vlansDisabled,
                                               **properties)


class IcrVirtualServer(VirtualServer):
    """Parse the iControl REST input to create the canonical Virtual Server."""
    def __init__(self, name, partition, default_route_domain, **properties):
        """Remove some of the properties that are not required."""
        self._filter_virtual_properties(**properties)

        profiles = self._flatten_profiles(**properties)
        policies = self._flatten_policies(**properties)

        super(IcrVirtualServer, self).__init__(name,
                                               partition,
                                               default_route_domain,
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
