u"""This module provides class for managing resource configuration."""
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


from f5_cccl.resource.ltm.pool_member import ApiPoolMember
from f5_cccl.resource.ltm.pool_member import IcrPoolMember
from f5_cccl.resource import Resource


class Pool(Resource):
    u"""Pool class for deploying configuration on BIG-IP"""
    properties = dict(name=None,
                      partition=None,
                      loadBalancingMode="round-robin",
                      description=None,
                      monitor="default",
                      membersReference={})

    def __init__(self, name, partition, members=None, **properties):
        u"""Create a Pool instance from CCCL poolType."""
        super(Pool, self).__init__(name, partition)

        for key, value in self.properties.items():
            if key == "name" or key == "partition":
                continue
            self._data[key] = properties.get(key, value)

        self._data['membersReference'] = {
            'isSubcollection': True, 'items': []}

        if members:
            self.members = members
            self._data['membersReference']['items'] = [
                m.__dict__() for m in members]
        else:
            self.members = list()

    def __eq__(self, other):
        if not isinstance(other, Pool):
            raise ValueError(
                "Invalid comparison of Pool object with object "
                "of type {}".format(type(other)))

        for key in self.properties:
            if key == 'membersReference' or key == 'monitor':
                continue

            if self._data[key] != other.data.get(key, None):
                return False

        if len(self) != len(other):
            return False
        if set(self.members) - set(other.members):
            return False
        if not self._monitors_equal(other):
            return False

        return True

    def _monitors_equal(self, other):
        self_monitor_list = sorted(
            [m.rstrip() for m in self._data['monitor'].split(" and ")]
        )

        other_monitor_list = sorted(
            [m.rstrip() for m in other.data['monitor'].split(" and ")]
        )

        return self_monitor_list == other_monitor_list

    def __hash__(self):  # pylint: disable=useless-super-delegation
        return super(Pool, self).__hash__()

    def __len__(self):
        return len(self.members)

    def _uri_path(self, bigip):
        return bigip.tm.ltm.pools.pool


class ApiPool(Pool):
    """Parse the CCCL input to create the canonical Pool."""
    def __init__(self, name, partition, **properties):
        """Parse the CCCL schema input."""
        pool_config = dict()
        for k, v in properties.items():
            if k == "members" or k == "monitors":
                continue
            pool_config[k] = v

        members_config = properties.get('members', None)
        members = self._get_members(partition, members_config)

        monitors_config = properties.pop('monitors', None)
        pool_config['monitor'] = self._get_monitors(monitors_config)

        super(ApiPool, self).__init__(name, partition,
                                      members,
                                      **pool_config)

    def _get_members(self, partition, members):
        """Get a list of members from the pool definition"""
        members_list = list()
        if members:
            for member in members:
                m = ApiPoolMember(name=None,
                                  partition=partition,
                                  pool=self,
                                  **member)
                members_list.append(m)

        return members_list

    def _get_monitors(self, monitors):
        if not monitors:
            return "default"

        monitor_list = [monitor['refname'] for monitor in monitors]
        if monitor_list:
            return " and ".join(sorted(monitor_list))

        return "default"


class IcrPool(Pool):
    """Filter the iControl REST input to create the canonical Pool."""
    def __init__(self, name, partition, **properties):
        """Parse the iControl REST representation of the Pool"""
        members = self._get_members(**properties)
        super(IcrPool, self).__init__(name, partition,
                                      members,
                                      **properties)

    def _get_members(self, **properties):
        """Get a list of members from the pool definition"""
        try:
            members = (
                properties['membersReference'].get('items', [])
            )
        except KeyError:
            return list()

        return [
            IcrPoolMember(pool=self,
                          **member)
            for member in members]
