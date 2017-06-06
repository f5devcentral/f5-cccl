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
"""F5 Common Controller Core Library to read, diff and apply BIG-IP config."""

from f5_cccl.bigip import CommonBigIP
from f5_cccl.service.manager import ServiceManager


API_SCHEMA = "./f5_cccl/schemas/cccl-api-schema.yml"


class F5CloudServiceManager(object):
    """F5 Common Controller Cloud Service Management.

    The F5 Common Controller Core Library (CCCL) is an orchestration package
    that provides a declarative API for defining BIG-IP LTM services in
    diverse environments (e.g. Marathon, Kubernetes, OpenStack).  The
    API will allow a user to create proxy services by specifying the:
    virtual servers, pools, L7 policy and rules, and monitors  as a service
    description object.  Each instance of the CCCL is initialized with
    namespace qualifiers to allow it to uniquely identify the resources
    under its control.
    """

    def __init__(self, hostname, username, password, partition, prefix=None,
                 port=443, token=None):
        """Initialize an instance of the F5 CCCL service manager.

        :param hostname: BIG-IP hostname or ip address.
        :param username: Access BIG-IP as user
        :param password: User password
        :param partition: Name of BIG-IP partition to manage.
        :param prefix: Optional string to prepend to resource names
        (default: None).
        :param port: Port to use for connection (default: 443)
        :param token: Use for token authentication (default None)
        """
        self._bigip = CommonBigIP(hostname,
                                  username,
                                  password,
                                  partition,
                                  prefix=prefix,
                                  port=port,
                                  token=token)

        self._service_manager = ServiceManager(self._bigip, partition,
                                               API_SCHEMA, prefix)

    def apply_config(self, services):
        """Apply service configurations to the BIG-IP partition.

        :param services: A serializable object that defines one or more
        services. Its schema is defined by cccl-api-schema.json.

        :return: True if successful, otherwise an exception is thrown.
        """
        return self._service_manager.apply_config(services)

    def get_status(self):
        """Get status for each service in the managed partition.

        :return: A serializable object of the statuses of each managed
        resource.

        Its structure is defined by:
            cccl-status-schema.json
        """
        status = {}

        return status

    def get_statistics(self):
        """Get statistics for each service in the managed partition.

        :return: A serializable object of the virtual server statistics
        for each service.

        Its structure is defined by:
            cccl-statistics-schema.json
        """
        statistics = {}

        return statistics
