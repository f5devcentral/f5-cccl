# coding=utf-8
# vim: set fileencoding=utf-8
# -*- coding: utf-8 -*-
u"""This module provides class for managing resource configuration."""
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

import copy

import f5_cccl.exceptions as cccl_exc

from f5.sdk_exception import F5SDKError
from icontrol.exceptions import iControlUnexpectedHTTPError

"""This module implements the F5 CCCL Resource super class."""


class Resource(object):
    u"""Resource super class to wrap BIG-IP configuration objects.

    A Resource represents a piece of CCCL configuration as represented
    by the cccl-api-schema.  It's purpose is to wrap configuration into
    an object that can later be used to perform Create, Read, Update,
    and Delete operations on the BIG-IP

    Data should only be initialized on creation of the Resouce object
    and not modified.  If a new representation is required a Resouce
    object with the corrected model should be created and the original
    discarded.

    The subclasses of Resource should only concern themselves with
    manipuation of the schema data to pack it into a payload that
    can be used to perform create, modify, and delete operations.
    Therefore, it is expected that the specialization of subclasses will
    be concentrated in the __init__, update, and __eq__ methodss.

    All subclasses are expected to implement the _uri_path method so
    that the appropriate resource URI is used when performing CRUD.

    """

    def __init__(self, name, partition):
        u"""Initialize a BIG-IP resource object from a CCCL schema object.

        Args:
            name (string): the name of the resource
            partition (string): the resource partition
        """
        self._data = {}
        self._data['name'] = name
        self._data['partition'] = partition

    def __dict__(self):
        u"""Create a dictionary of the resource data."""
        return self._data

    def __eq__(self, resource):
        u"""Compare two resources for equality.

        Args:
            resouce (Resource): The resource to compare
        Return:
            True if equal
            False otherwise
        """
        return (self._data['name'] == resource.name and
                self._data['partition'] == resource.partition)

    def create(self, bigip):
        u"""Create resource on a BIG-IP system.

        The internal data model is applied to the BIG-IP

        Args:
            bigip (f5.bigip.ManagementRoot): F5 SDK session object

        Returns: created resource object.

        Raises:
            F5CcclResourceCreateError: resouce cannot be created for an
            unspecified reason.

            F5CcclResourceConflictError: resouce cannot be created because
            it already exists on the BIG-IP
        """
        try:
            obj = self._uri_path(bigip).create(**self._data)
            return obj
        except iControlUnexpectedHTTPError as err:
            self._handle_http_error(err)
        except F5SDKError as err:
            raise cccl_exc.F5CcclResourceCreateError(str(err))

    def read(self, bigip):
        u"""Retrieve a BIG-IP resource from a BIG-IP.

        Returns a resource object with attributes for instance on a
        BIG-IP system.

        Args:
            bigip (f5.bigip.ManagementRoot): F5 SDK session object

        Returns: resource retrieved from BIG-IP

        Raises:
            F5CcclResourceNotFoundError: resouce cannot be loaded because
            it does not exist on the BIG-IP
        """
        try:
            obj = self._uri_path(bigip).load(
                name=self.name,
                partition=self.partition)
            return obj
        except iControlUnexpectedHTTPError as err:
            self._handle_http_error(err)
        except F5SDKError as err:
            raise cccl_exc.F5CcclError(str(err))

    def update(self, bigip, data=None, modify=True):
        u"""Update a resource (e.g., pool) on a BIG-IP system.

        Modifies a resource on a BIG-IP system using attributes
        defined in the model object.
        The internal data model is applied to the BIG-IP

        Args:
            bigip: BigIP instance to use for updating resource.
            data: Applies mostly for 'patching' or modify, but contains targets
                for update operation specifically
            modify: Specifies if this is a modify, or patch of specific
                Key/Value Pairs rather than the whole object

        Raises:
            F5CcclResourceUpdateError: resouce cannot be updated for an
            unspecified reason.

            F5CcclResourceNotFoundError: resouce cannot be updated because
            it does not exist on the BIG-IP
        """
        if not data:
            data = self.__dict__
        try:
            obj = self._uri_path(bigip).load(
                name=self.name,
                partition=self.partition)
            payload = copy.copy(self._data)
            if modify:
                obj.modify(**payload)
            else:
                obj.update(**payload)
        except iControlUnexpectedHTTPError as err:
            self._handle_http_error(err)
        except F5SDKError as err:
            raise cccl_exc.F5CcclResourceUpdateError(str(err))

    def delete(self, bigip):
        u"""Delete a resource on a BIG-IP system.

        Loads a resource and deletes it.

        Args:
            bigip: BigIP instance to use for delete resource.

        Raises:
            F5CcclResourceDeleteError: resouce cannot be deleted for an
            unspecified reason.

            F5CcclResourceNotFoundError: resouce cannot be deleted because
            it already exists on the BIG-IP
        """
        try:
            obj = self._uri_path(bigip).load(
                name=self.name,
                partition=self.partition)
            obj.delete()
        except AttributeError as err:
            msg = "Could not delete {}, is it present on the BIG-IP?".format(
                str(self))
            raise cccl_exc.F5CcclResourceDeleteError(msg)
        except iControlUnexpectedHTTPError as err:
            self._handle_http_error(err)
        except F5SDKError as err:
            raise cccl_exc.F5CcclResourceDeleteError(str(err))

    @property
    def name(self):
        u"""Get the name for this resource."""
        return self._data['name']

    @property
    def partition(self):
        u"""Get the partition for this resource."""
        return self._data['partition']

    @property
    def data(self):
        u"""Get the internal data model for this resource."""
        return self._data

    def _uri_path(self, bigip):
        u"""Get the URI resource path key for the F5 SDK.

        For example, a pool resource returns:

        bigip.tm.ltm.pools.pool

        This needs to be implemented by a Resouce subclass.
        """
        raise NotImplementedError

    @staticmethod
    def _handle_http_error(error):
        u"""Extract the error code and reraise a CCCL Error."""
        code = error.response.status_code
        if code == 404:
            raise cccl_exc.F5CcclResourceNotFoundError(str(error))
        elif code == 409:
            raise cccl_exc.F5CcclResourceConflictError(str(error))
        elif code >= 400 and code < 500:
            raise cccl_exc.F5CcclResourceRequestError(str(error))
        else:
            raise cccl_exc.F5CcclError(str(error))
