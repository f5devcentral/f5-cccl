# coding=utf-8
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


"""This module defines the exceptions used in f5_cccl."""


class F5CcclError(Exception):
    """Base class for f5_cccl exceptions."""

    def __init__(self, msg=None):
        """Initialize object members."""
        super(F5CcclError, self).__init__()
        self.msg = msg

    def __str__(self):
        """Generate a string representation of the object."""
        classname = self.__class__.__name__
        if self.msg:
            return "%s - %s" % (classname, self.msg)
        return classname


class F5CcclSchemaError(F5CcclError):
    """Error raised when base schema defining API is invalid."""

    def __init__(self, msg):
        """Initialize with base schema invalid message."""
        super(F5CcclSchemaError, self).__init__(msg)
        self.msg = 'Schema provided is invalid: ' + msg


class F5CcclValidationError(F5CcclError):
    """Error raised when service config is invalid against the API schema."""

    def __init__(self, msg):
        """Initialize with base config does not match schema message."""
        super(F5CcclValidationError, self).__init__(msg)
        self.msg = 'Service configuration provided does not match schema: ' + \
            msg


class F5CcclResourceCreateError(F5CcclError):
    """General resource creation failure."""


class F5CcclResourceConflictError(F5CcclError):
    """Resource already exists on BIG-IP?."""


class F5CcclResourceNotFoundError(F5CcclError):
    """Resource not found on BIG-IP?."""


class F5CcclResourceRequestError(F5CcclError):
    """Resource request client error on BIG-IP?."""


class F5CcclResourceUpdateError(F5CcclError):
    """General resource update failure."""


class F5CcclResourceDeleteError(F5CcclError):
    """General resource delete failure."""


class F5CcclApplyConfigError(F5CcclError):
    """General config deployment failure."""


class F5CcclCacheRefreshError(F5CcclError):
    """Failed to update the BigIP configuration state."""


class F5CcclConfigurationReadError(F5CcclError):
    """Failed to create a Resource from the API configuration."""
