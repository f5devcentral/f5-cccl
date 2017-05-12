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

from f5.sdk_exception import F5SDKError
import f5_cccl.exceptions as cccl_exc
from icontrol.exceptions import iControlUnexpectedHTTPError


class Resource(object):
    u"""Resource super class to wrap BIG-IP? configuration objects.

    A Resource represents a piece of CCCL configuration as represented
    by the cccl-api-schema.  It's purpose is to wrap configuration into
    an object that can later be used to perform Create, Read, Update,
    and Delete operations on the BIG-IP?

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

    def __init__(self, data):
        u"""Initialize a BIG-IP? resource object from a CCCL schema object."""
        self._data = data
        self._name = data.get('name', None)
        self._partition = data.get('partition', None)

    def create(self, bigip):
        u"""Create resource on a BIG-IP® system.

        The internal data model is applied to the BIG-IP?

        Args:
            bigip (f5.bigip.ManagementRoot): F5 SDK session object

        Returns: created resource object.

        Raises:
            F5CcclResourceCreateError: resouce cannot be created for an
            unspecified reason.

            F5CcclResourceConflictError: resouce cannot be created because
            it already exists on the BIG-IP?
        """
        try:
            obj = self._uri_path(bigip).create(**self._data)
            return obj
        except iControlUnexpectedHTTPError as err:
            self._handle_http_error(err)
        except F5SDKError as err:
            raise cccl_exc.F5CcclResourceCreateError(str(err))

    def read(self, bigip):
        u"""Retrieve a BIG-IP® resource from a BIG-IP®.

        Returns a resource object with attributes for instance on a
        BIG-IP® system.

        Args:
            bigip (f5.bigip.ManagementRoot): F5 SDK session object

        Returns: resource retrieved from BIG-IP?

        Raises:
            F5CcclResourceNotFoundError: resouce cannot be loaded because
            it does not exist on the BIG-IP?
        """
        try:
            obj = self._uri_path(bigip).load(
                name=self._name,
                partition=self._partition)
            return obj
        except iControlUnexpectedHTTPError as err:
            self._handle_http_error(err)
        except F5SDKError as err:
            raise cccl_exc.F5CcclError(str(err))

    def update(self, bigip):
        u"""Update a resource (e.g., pool) on a BIG-IP® system.

        Modifies a resource on a BIG-IP® system using attributes
        defined in the model object.
        The internal data model is applied to the BIG-IP?

        Args:
            bigip: BigIP instance to use for updating resource.

        Raises:
            F5CcclResourceUpdateError: resouce cannot be updated for an
            unspecified reason.

            F5CcclResourceNotFoundError: resouce cannot be updated because
            it does not exist on the BIG-IP?
        """
        try:
            obj = self._uri_path(bigip).load(
                name=self._name,
                partition=self._partition)
            obj.modify(**self._data)
        except iControlUnexpectedHTTPError as err:
            self._handle_http_error(err)
        except F5SDKError as err:
            raise cccl_exc.F5CcclResourceUpdateError(str(err))

    def delete(self, bigip):
        u"""Delete a resource on a BIG-IP® system.

        Loads a resource and deletes it.

        Args:
            bigip: BigIP instance to use for delete resource.

        Raises:
            F5CcclResourceDeleteError: resouce cannot be deleted for an
            unspecified reason.

            F5CcclResourceNotFoundError: resouce cannot be deleted because
            it already exists on the BIG-IP?
        """
        try:
            obj = self._uri_path(bigip).load(
                name=self._name,
                partition=self._partition)
            obj.delete()
        except iControlUnexpectedHTTPError as err:
            self._handle_http_error(err)
        except F5SDKError as err:
            raise cccl_exc.F5CcclResourceDeleteError(str(err))

    @property
    def name(self):
        u"""Get the name for this resource."""
        return self._name

    @property
    def partition(self):
        u"""Get the partition for this resource."""
        return self._partition

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
            raise cccl_exc.F5CcclResourceNotFoundError(
                error.response.message)
        elif code == 409:
            raise cccl_exc.F5CcclResourceConflictError(
                error.response.message)
        elif code >= 400 and code < 500:
            raise cccl_exc.F5CcclResourceRequestError(
                error.response.message)
        else:
            raise cccl_exc.F5CcclError(error.response.message)
