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


from f5_cccl.resource.ltm.pool_member import BigIPPoolMember
from f5_cccl.resource.ltm.pool_member import F5CcclPoolMember
from f5_cccl.resource import Resource


class Pool(Resource):
    u"""Pool class for deploying configuration on BIG-IP"""
    pool_properties = dict(name=None,
                           partition=None,
                           loadBalancingMode="round-robin",
                           description=None,
                           monitor="default",
                           membersReference={})

    def __init__(self, name, partition, members=None, **properties):
        u"""Create a Pool instance from CCCL poolType."""
        super(Pool, self).__init__(name, partition)

        self._data['loadBalancingMode'] = properties.get(
            'loadBalancingMode', 'round-robin')
        self._data['description'] = properties.get(
            'description', None)
        self._data['monitor'] = properties.get(
            'monitor', 'default')
        self._data['membersReference'] = {
            'isSubcollection': True, 'items': []}

        self.members = list()
        if members:
            self.members = members
            self._data['membersReference']['items'] = [
                m.__dict__() for m in members]

    def __eq__(self, other):
        if not isinstance(other, Pool):
            raise ValueError(
                "Invalid comparison of Pool object with object "
                "of type {}".format(type(other)))

        other_properties = other.data
        for key, _ in self._data.items():
            if self._data[key] != other_properties[key]:
                return False
        if len(self.members) != len(other):
            return False
        if set(self.members) - set(other.members):
            return False
        return True

    def __len__(self):
        if 'items' in self._data['membersReference']:
            return len(self._data['membersReference']['items'])
        return 0

    def __dict__(self):
        return self._data

    def _uri_path(self, bigip):
        return bigip.tm.ltm.pools.pool

    def __repr__(self):
        pass


class F5CcclPool(Pool):
    """Parse the CCCL input to create the canonical Pool."""
    def __init__(self, name, partition, **properties):
        """Parse the CCCL schema input."""
        pool_config = dict()
        for k, v in properties.items():
            if k == "members" or k == "monitor":
                continue
            pool_config[k] = v

        members = (
            self._get_members(partition, properties['members'])
        )
        super(F5CcclPool, self).__init__(name, partition,
                                         members,
                                         **pool_config)

    def _get_members(self, partition, members=None):
        """Get a list of members from the pool definition"""
        members_list = list()
        if members:
            for member in members:
                m = F5CcclPoolMember(name=None,
                                     partition=partition,
                                     pool=self,
                                     **member)
                members_list.append(m)

        return members_list


class BigIPPool(Pool):
    """Filter the F5 SDK input to create the canonical Pool."""
    def __init__(self, name, partition, **properties):
        """Parse the BigIP SDK representation of the Pool"""
        members = self._get_members(**properties)
        super(BigIPPool, self).__init__(name, partition,
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
            BigIPPoolMember(pool=self,
                            **member)
            for member in members]
