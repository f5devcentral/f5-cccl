# coding=utf-8
# -*- coding: utf-8 -*-
"""This module provides class for managing resource configuration."""
#
# Copyright (c) 2017-2021 F5 Networks, Inc.
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

import base64
import copy
import logging
import zlib

from operator import itemgetter
import jsonpatch

from f5.sdk_exception import F5SDKError
from icontrol.exceptions import iControlUnexpectedHTTPError
from requests.utils import quote as urlquote

import f5_cccl.exceptions as cccl_exc
import f5_cccl.utils.json_pos_patch as pospatch
from f5_cccl.utils.resource_merge import merge


LOGGER = logging.getLogger(__name__)


class Resource(object):
    """Resource super class to wrap BIG-IP configuration objects.

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

    common_properties = dict(metadata=None)

    @classmethod
    def classname(cls):
        """Return the class name of the resource."""
        return cls.__name__

    def __init__(self, name, partition, **properties):
        """Initialize a BIG-IP resource object from a CCCL schema object.

        Args:
            name (string): the name of the resource
            partition (string): the resource partition
        """
        if not name:
            LOGGER.error("Resource instantiation error: undefined name")
            raise ValueError(
                "must have at least name({})".format(name))

        self._data = dict()
        self._data['name'] = name
        self._data['partition'] = partition
        # user defined objects that must not be removed, even if not referenced
        self._whitelist = False
        # previously applied updates by CCCL to the resource
        self._whitelist_updates = None

        if properties:
            for key, default in list(self.common_properties.items()):
                value = properties.get(key, default)
                if value is not None:
                    self._data[key] = value
                    if key == 'metadata':
                        # set resource flags
                        self._process_metadata_flags(name, value)

    def __eq__(self, resource):
        """Compare two resources for equality.

        Args:
            resouce (Resource): The resource to compare
        Return:
            True if equal
            False otherwise
        """
        return self._data == resource.data

    def __ne__(self, resource):
        return not self.__eq__(resource)

    def __hash__(self):
        return hash((self.name, self.partition))

    def __lt__(self, resource):
        return self.full_path() < resource.full_path()

    def __str__(self):
        return str(self._data)

    def merge(self, desired_data):
        """Merge in properties from controller instead of replacing"""
        # 1. stop processing if no merging is needed
        prev_updates = self._retrieve_whitelist_updates()
        if desired_data == {} and prev_updates is None:
            # nothing needs to be done (cccl has not and will not make changes
            # to this resource)
            return False

        prev_data = copy.deepcopy(self._data)

        # 2. remove old CCCL updates
        pospatch.convert_to_positional_patch(self._data, prev_updates)

        try:
            # This actually backs out the previous updates
            # to get back to the original F5 resource state.
            if prev_updates:
                self._data = prev_updates.apply(self._data)
        except Exception as e:  # pylint: disable=broad-except
            LOGGER.warning("Failed removing updates to resource %s: %s",
                           self.name, e)

        # 3. perform new merge with latest CCCL specific config
        original_resource = copy.deepcopy(self)
        self._data = merge(self._data, desired_data)
        self.post_merge_adjustments()

        # 4. compute the new updates so we can back out next go-around
        cur_updates = jsonpatch.make_patch(self._data, original_resource.data)

        # 5. remove move / adjust indexes per resource specific
        pospatch.convert_from_positional_patch(self._data, cur_updates)

        changed = self._data != prev_data

        # 6. update metadata with new CCCL updates
        self._save_whitelist_updates(cur_updates)

        # 7. determine if there was a needed change
        return changed

    def post_merge_adjustments(self):
        """Make any resource adjustment after merge

           Inherited classes can override this to perform custom adjustments.
        """
        # Big-IP returns this metadata list in sorted order (by name)
        self._data['metadata'] = sorted(self._data['metadata'],
                                        key=itemgetter('name'))

    def create(self, bigip):
        """Create resource on a BIG-IP system.

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
        LOGGER.info("Creating %s: /%s/%s",
                    self.classname(), self.partition, self.name)
        try:
            obj = self._uri_path(bigip).create(**self._data)
            return obj
        except iControlUnexpectedHTTPError as err:
            self._handle_http_error(err)
        except F5SDKError as err:
            LOGGER.error("Create FAILED: /%s/%s", self.partition, self.name)
            raise cccl_exc.F5CcclResourceCreateError(str(err))

    def read(self, bigip):
        """Retrieve a BIG-IP resource from a BIG-IP.

        Returns a resource object with attributes for instance on a
        BIG-IP system.

        Args:
            bigip (f5.bigip.ManagementRoot): F5 SDK session object

        Returns: resource retrieved from BIG-IP

        Raises:
            F5CcclResourceNotFoundError: resouce cannot be loaded because
            it does not exist on the BIG-IP
        """
        LOGGER.info("Loading %s: /%s/%s",
                    self.classname(), self.partition, self.name)
        try:
            obj = self._uri_path(bigip).load(
                name=urlquote(self.name),
                partition=self.partition)
            return obj
        except iControlUnexpectedHTTPError as err:
            self._handle_http_error(err)
        except F5SDKError as err:
            LOGGER.error("Load FAILED: /%s/%s", self.partition, self.name)
            raise cccl_exc.F5CcclError(str(err))

    def update(self, bigip, data=None, modify=False):
        """Update a resource (e.g., pool) on a BIG-IP system.

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
        LOGGER.info("Updating %s: /%s/%s",
                    self.classname(), self.partition, self.name)
        if not data:
            data = self._data
        try:
            obj = self._uri_path(bigip).load(
                name=urlquote(self.name),
                partition=self.partition)
            payload = copy.copy(data)

            # removing the mutate read-only attribute 'ipAddress' while updating the ARP
            if self.classname() == "ApiArp":
                payload.pop("ipAddress")

            if modify:
                obj.modify(**payload)
            else:
                obj.update(**payload)
        except iControlUnexpectedHTTPError as err:
            self._handle_http_error(err)
        except F5SDKError as err:
            LOGGER.error("Update FAILED: /%s/%s", self.partition, self.name)
            raise cccl_exc.F5CcclResourceUpdateError(str(err))

    def delete(self, bigip):
        """Delete a resource on a BIG-IP system.

        Loads a resource and deletes it.

        Args:
            bigip: BigIP instance to use for delete resource.

        Raises:
            F5CcclResourceDeleteError: resouce cannot be deleted for an
            unspecified reason.

            F5CcclResourceNotFoundError: resouce cannot be deleted because
            it already exists on the BIG-IP
        """
        LOGGER.info("Deleting %s: /%s/%s",
                    self.classname(), self.partition, self.name)
        try:
            obj = self._uri_path(bigip).load(
                name=urlquote(self.name),
                partition=self.partition)
            obj.delete()
        except AttributeError as err:
            msg = "Could not delete {}, is it present on the BIG-IP?".format(
                str(self))
            raise cccl_exc.F5CcclResourceDeleteError(msg)
        except iControlUnexpectedHTTPError as err:
            self._handle_http_error(err)
        except F5SDKError as err:
            LOGGER.error("Delete FAILED: /%s/%s", self.partition, self.name)
            raise cccl_exc.F5CcclResourceDeleteError(str(err))

    @property
    def name(self):
        """Get the name for this resource."""
        return self._data['name']

    @property
    def partition(self):
        """Get the partition for this resource."""
        return self._data['partition']

    @property
    def data(self):
        """Get the internal data model for this resource."""
        return self._data

    @property
    def whitelist(self):
        """Flag to indicate if user-created resource should be ignored"""
        return self._whitelist

    def _save_whitelist_updates(self, updates):
        """Saves the updates applied to this whitelisted object"""
        if not self._whitelist:
            LOGGER.error('Cannot apply updates to the non-whitelisted '
                         'object %s', self.full_path())
        elif updates:
            b_content = bytes(updates.to_string().encode('ascii'))
            self._whitelist_updates = base64.b64encode(
                zlib.compress(b_content)).decode('ascii')
            metadata = {
                'name': 'cccl-whitelist-updates',
                'persist': 'true',
                'value': self._whitelist_updates
            }
            self._data['metadata'].append(metadata)

    def _retrieve_whitelist_updates(self):
        """Retrieves the updates and ret to this whitelisted object"""

        updates = None
        if not self._whitelist:
            LOGGER.error('Cannot retrieve updates to the non-whitelisted '
                         'object %s', self.full_path())
        else:
            if self._whitelist_updates is not None:
                try:
                    update_str = zlib.decompress(base64.b64decode(
                        self._whitelist_updates)).decode('ascii')
                    updates = jsonpatch.JsonPatch.from_string(update_str)
                except Exception:  # pylint: disable=broad-except
                    LOGGER.error('Cannot process previous updates for the '
                                 'whitelisted resource %s', self.full_path())
        return updates

    def full_path(self):
        """Concatenate the partition and name to form fullPath."""
        return "/{}/{}".format(self.partition, self.name)

    def _uri_path(self, bigip):
        """Get the URI resource path key for the F5 SDK.

        For example, a pool resource returns:

        bigip.tm.ltm.pools.pool

        This needs to be implemented by a Resouce subclass.
        """
        raise NotImplementedError

    def _handle_http_error(self, error):
        """Extract the error code and reraise a CCCL Error."""
        code = error.response.status_code
        LOGGER.error(
            "HTTP error(%d): CCCL resource(%s) /%s/%s.",
            code, self.classname(), self.partition, self.name)
        if code == 404:
            raise cccl_exc.F5CcclResourceNotFoundError(str(error))
        elif code == 409:
            raise cccl_exc.F5CcclResourceConflictError(str(error))
        elif 400 <= code < 500:
            raise cccl_exc.F5CcclResourceRequestError(str(error))
        else:
            raise cccl_exc.F5CcclError(str(error))

    def _process_metadata_flags(self, name, metadata_list):
        # look for supported flags
        metadata_update_idx = None
        metadata_whitelist_flag = False
        for idx, metadata in enumerate(metadata_list):
            if metadata['name'] == 'cccl-whitelist':
                metadata_whitelist_flag = True
                self._whitelist = metadata['value'] in [
                    'true', 'True', 'TRUE', '1', 1]
                LOGGER.debug('Resource %s cccl-whitelist: %s',
                             name, self._whitelist)
            if metadata['name'] == 'cccl-whitelist-updates':
                self._whitelist_updates = metadata['value']
                LOGGER.debug('Resource %s cccl-whitelist-updates: %s',
                             name, self._whitelist_updates)
                metadata_update_idx = idx

        # We want to remove the 'cccl-whitelist-updates' field from the
        # metadata that was retrieved from the Big-IP (this field indicates
        # the changes CCCL made to the existing resource and will be
        # recalculated). However, if the user deleted the 'cccl-whitelist'
        # metadata flag, we need to leave it in. This forces a miscompare
        # with the desired resource configuration. That in turn, causes an
        # update to occur, ensuring the metadata is removed on the Big-IP side.
        if metadata_update_idx is not None and metadata_whitelist_flag is True:
            del metadata_list[metadata_update_idx]
