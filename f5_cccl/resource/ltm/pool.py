#!/usr/bin/env python
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

import logging

import f5_cccl.exceptions as exceptions

from f5_cccl.resource import Resource

logger = logging.getLogger(__name__)

"""Hosts an interface for the BIG-IP Pool Resource.

This module references and holds items relevant to the orchestration of the F5
BIG-IP for purposes of abstracting the F5-SDK library.
"""


class Pool(Resource):
    """Creates a CCCL BIG-IP Pool Object of sub-type of Resource

This object hosts the ability to orchestrate basic CRUD actions against a
BIG-IP Pool via the F5-SDK.
    """
    _data = dict()

    def __dict__(self):
        """Dictionary converter method"""
        items = self._data
        # FIXME: handle the monitor and members attributes individually here
        return items

    def __eq__(self, compare):
        """Checks Equality between this CCCL Pool and another BIG-IP Pool

        This method will transform the comparison into a relative dict of the
        BIG-IP Pool properties addressed in CCCL's Pool and compare them.

        This intentionally includes a shallow dict comparison of schema-based
        attributes and a "left-to-the-member" comparison of pool members.  To
        add more of these, simply add more attributes to the CCCL Pool object.

        :param compare: [CCCL Pool object | dict(BIG-IP Pool Attributes)]
        :returns: Bool [True:=Pools are equal, False:=Not Equal]

        Use:
            obj == compare or obj.equals(compare) or obj.__eq__(compare)
        """
        # get rid of the most obvious case first...
        if not isinstance(compare, Pool) and not isinstance(compare, dict):
            return False
        comparison = extract_comparison(compare)
        myself = self.__dict__(True)
        # AssertionError is cycle-wise faster than if/then/else nests...
        try:
            self.__shallow_compare(myself, comparison)
            self.__member_compare(myself, comparison)
        except AssertionError as Err:
            # We're NE, log a reason when troubleshooting this and move on
            logger.debug(str(Err))  # this can get really noisy!
            return False
        except KeyError as Err:
            logger.debug(str(Err))
            return False
        return True

    def __init__(self, partition=None, description=None, name=None,
                 members=None, monitor=None, loadBalancingMode=None,
                 bigip=None):
        """Init method"""
        if not name or not partition:
            raise exceptions.F5CcclResourceCreateError(
                "Failed to create Pool due to missing requirement "
                "name({}) partition({})".format(name, partition))
        super(Pool, self).__init__(dict(name=name, partition=partition))
        self._data['description'] = description
        self._data['loadBalancingMode'] = loadBalancingMode
        self._data['members'] = members
        self._data['monitor'] = monitor

    def __member_compare(self, myself, comparison):
        """An internal Pool method"""
        # This method compares two sets of members against one another
        # :params: dict(members=<members>)
        # :returns: Bool [True:=Equal,False:=Not Equal]
        raise NotImplementedError("member handling not implemented yet")

    def __shallow_compare(self, myself, comparison, stop=False):
        """An internal Pool method"""
        # This method compares two dicts at a very shallow level (first keys)
        # :params: dict()
        # :returns: Bool [True:=Equal,False:=Not Equal]
        keys = list(self._data.keys())
        keys.remove('members')
        keys.remove('monitor')
        for item in keys:
            print(myself[item], comparison[item],
                  myself[item] == comparison[item])
            assert myself[item] == comparison[item], \
                'Because {} attr is not equal'.format(item)

    def __str__(self):
        """Str conversion method"""
        return "Pool(name={}, description={}, loadBalancingMode={})".format(
            self.name, self.description, self.loadBalancingMode)

    def create(self, bigip):
        """Creates New Pool on the BIG-IP based upon this CCCL Pool

        This method will store this CCCL Pool onto the BIG-IP by partition and
        name.  If it already exists, then an exception is thrown.

        :param new_pool: BIG-IP Pool item to be added to the partition
        :return: NoDef
        :exception: ResourceLtmCreationError - Could not create BIG-IP Pool
        """
        logger.debug("Attempting to create Pool(name={})".format(self.name))
        return super(Pool, self).create(bigip)

    def delete(self):
        """Delete this CCCL Pool from the BIG-IP by partition and name

        This method will attempt to delete this CCCL Pool from the BIG-IP via
        the F5-SDK.  It will do this by this CCCL Pool's partition and name.

        :params: None
        :return: NoDef
        """
        logger.debug("Deleting {} Pool".format(self.name))
        super(Pool, self).delete()

    def read(self, bigip):
        """Attempt to Retrieve this CCCL Pool from the BIG-IP

        This method wraps the F5-SDK and returns the BIG-IP's stored Pool value
        with this CCCL Pool's name and partition.

        :params: None
        :returns: BIG-IP Pool
        """
        logger.debug('Reading BIG-IP Pool {} from BIG-IP'.format(self.name))
        return super(Pool, self).read(bigip)

    def update(self, bigip):
        """Attempt to Update the BIG-IP with this CCCL Pool

        This method will take in an F5-SDK BIG-IP object and attempt to update
        the pool on the BIG-IP.

        :param bigip: F5-SDK BigIP object
        :returns: None
        """
        logger.debug('Update BIG-IP Pool {}'.format(self.name))
        super(Pool, self).update(bigip)

    def equals(self, pool_diff):
        """Compares 2 BIG-IP Pools.

        Takes a BIG-IP Pool and compares it against this CCCL Pool and returns
        a True/False on whether they are both equal to one another.

        :return: Bool := [True: The Two instances are equal,
                          False: They are not]
        """
        return self.__eq__(pool_diff)

    def member_list(self):
        """Returns the list of PoolMembers off of this CCCL Pool

        This method will return the list of PoolMembers on this CCCL Pool.

        NOTE: PoolMember instances will be returned in no specific order.

        :returns: [BIG-IP Members] |- List of BIG-IP Members
        """
        return self.members

    def add_member(self, member):
        """Adds a Single PoolMember to the CCCL Pool

        This method will add a BIG-IP PoolMember to this CCCL Pool.

        :param member: PoolMember instance to be added
        :return: None
        """
        logger.debug("Attemmping to add Member {} to Pool {}".format(
                     self, member))
        raise NotImplementedError("Member actions have not been implemented")

    def read_member(self, name):
        """Reads in a Single BIG-IP Member that exists in this BIG-IP Pool

        This method will take in a name of a BIG-IP Member and return that
        Member as a PoolMember if it exists in this BIG-IP Pool by partition
        and name.  If it does not exist, then an exception is thrown.

        :param name: The name of the BIG-IP Member
        :return: PoolMember - the member whose name was given
        :exception: MissingResourceError - No BIG-IP Member with this name
        """
        logger.debug(
            "Attemping to read a BIG-IP Member {} from Pool {}".format(
                    name, self))
        raise NotImplementedError("member actions have not been implemented")

    def remove_member(self, name):
        """Removes a BIG Member from the BIG-IP Pool by name

        This method will take in a name of a BIG-IP Member and remove it from
        the CCCL Pool.  If the Member does not exist on the CCCL Pool, then an
        exception will be thrown.

        :param name: The name of the Member referenced
        :returns: None
        :exception: MissingResourceError - No member with the name exists in
            the list of PoolMembers
        """
        logger.debug(
            "Attemping to remove a BIG-IP Member {} from Pool {}".format(
                    name, self))
        raise NotImplementedError("member actions have not been implemented")

    def find_member(self, name):
        """Searches the Pool for the BIG-IP Member Referenced by Name

        This method will return a True|False result on whether or not a BIG-IP
        member exists on the BIG-IP Pool.

        :param name: str The name of the BIG-IP Member
        :returns: Bool := [True: BIG-IP Member exists on this CCCL Pool
                           False: It does not]
        """
        logger.debug(
            "Attemping to find a BIG-IP Member {} from Pool {}".format(
                    name, self))
        raise NotImplementedError("member actions have not been implemented")

    @property
    def description(self):
        return self._data['description']

    @property
    def loadBalancingMode(self):
        return self._data['loadBalancingMode']

    @property
    def members(self):
        return self._data['members']

    @property
    def monitor(self):
        return self._data['monitor']


def extract_comparison(compare):
    """Digests and Transforms a Pool.__dict__() Comparible Form

    This method will return a CCCL Pool-comparible object regardless as to
    whether it comes from the BIG-IP via the SDK or an approved schema.

    :param compare: [CCCL Pool or BIG-IP Pool from the F5-SDK]
    :returns: comparison - a dict() that is comparible to a Pool() instance
    """
    if isinstance(compare, Pool):
        comparison = compare.__dict__()
    elif isinstance(compare, dict):
        comparison = compare
        if isinstance(comparison['members'], list):
            # Transform the list into the expected dict() format
            transformation = dict()
            for member in comparison['members']:
                if isinstance(member, dict):
                    transformation[member['name']] = member
                else:
                    # FIXME: This should include the PoolMember case
                    raise NotImplementedError(
                        "Cannot handle a member of type {} yet".format(
                            type(member)))
            comparison['members'] = transformation
        elif isinstance(comparison['members'], dict):
            pass
        else:
            # FIXME: this should be striped beteween a reference and a list
            # case...
            raise NotImplementedError(
                "Unable to handle members of type {}".format(
                    type(comparison['members'])))
    return comparison
