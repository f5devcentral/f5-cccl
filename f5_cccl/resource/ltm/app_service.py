"""Provides a class for managing BIG-IP Application Service resources."""
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
from f5_cccl.utils.route_domain import normalize_address_with_route_domain


LOGGER = logging.getLogger(__name__)


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
            elif key == "template":
                self._data[key] = properties.get(key, value)

    def __eq__(self, other):
        if not isinstance(other, ApplicationService):
            LOGGER.warning(
                "Invalid comparison of Application Service object with object "
                "of type %s", type(other))
            return False

        if not all(v in self._data['variables']
                   for v in other.data['variables']):
            return False
        if not all(t in self._data['tables'] for t in other.data['tables']):
            return False

        for key in self._data:
            if key in ["variables", "tables"]:
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


class IcrApplicationService(ApplicationService):
    """Parse iControl REST input to create canonical Application Service."""
    def __init__(self, name, partition, **properties):
        super(IcrApplicationService, self).__init__(name,
                                                    partition,
                                                    **properties)
        for key, value in self.properties.items():
            if key == "variables":
                self._data[key] = properties.get(key, value)
                # Remove 'encrypted' key and its value from ICR data
                for v in self._data[key]:
                    v.pop('encrypted', None)
            if key == "tables":
                self._data[key] = properties.get(key, value)


class ApiApplicationService(ApplicationService):
    """Parse the CCCL input to create the canonical Application Service."""
    def __init__(self, name, partition, default_route_domain, **properties):
        self._default_route_domain = default_route_domain
        super(ApiApplicationService, self).__init__(name,
                                                    partition,
                                                    **properties)
        members = []
        if 'poolMemberTable' in properties:
            members = properties['poolMemberTable'].get("members", [])

        self._data["variables"] = self._iapp_build_variables(properties)
        self._data["tables"] = self._iapp_build_tables(members, properties)

    def _iapp_build_variables(self, config):
        """Create a list of name-value objects."""
        variables = []
        for key, value in config['variables'].items():
            var = {'name': key, 'value': value}
            if var['name'] == "pool__addr":
                var['value'] = normalize_address_with_route_domain(
                    var['value'], self._default_route_domain)[0]
            variables.append(var)

        return variables

    def _iapp_build_tables(self, members, config):
        """Create a dict that defines the tables for an iApp.

        Args:
            members: list of pool members
            config: BIG-IP config dict
        """
        tables = []
        if 'poolMemberTable' in config:
            tableConfig = config['poolMemberTable']

            # Construct columnNames array from the 'name' prop of each column
            columnNames = [col['name'] for col in tableConfig['columns']]

            # Construct rows array - one row for each node, interpret the
            # 'kind' or 'value' from the column spec.
            rows = []
            for node in members:
                row = []
                for col in tableConfig['columns']:
                    if 'value' in col:
                        row.append(col['value'])
                    elif 'kind' in col:
                        if col['kind'] == 'IPAddress':
                            address = normalize_address_with_route_domain(
                                node['address'], self._default_route_domain)[0]
                            row.append(address)
                        elif col['kind'] == 'Port':
                            row.append(str(node['port']))

                rows.append({'row': row})

            # Done - add the generated pool member table to the set of tables
            # we're going to configure.
            tables.append({
                'name': tableConfig['name'],
                'columnNames': columnNames,
                'rows': rows
            })

        # Add other tables
        if 'tables' in config:
            for key in config['tables']:
                data = config['tables'][key]
                table = {'columnNames': data['columns'],
                         'name': key,
                         'rows': []}
                for row in data['rows']:
                    table['rows'].append({'row': row})
                tables.append(table)

        return tables
