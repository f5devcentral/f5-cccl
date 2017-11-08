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

import logging
import pkg_resources

from f5_cccl.bigip import BigIPProxy
from f5_cccl.service.manager import ServiceManager

resource_package = __name__
ltm_api_schema = "schemas/cccl-ltm-api-schema.yml"
net_api_schema = "schemas/cccl-net-api-schema.yml"

LOGGER = logging.getLogger("f5_cccl")


class F5CloudServiceManager(object):
    """F5 Common Controller Cloud Service Management.

    The F5 Common Controller Core Library (CCCL) is an orchestration package
    that provides a declarative API for defining BIG-IP LTM and NET services
    in diverse environments (e.g. Marathon, Kubernetes, OpenStack). The
    API will allow a user to create proxy services by specifying the:
    virtual servers, pools, L7 policy and rules, monitors, arps, or fdbTunnels
    as a service description object.  Each instance of the CCCL is initialized
    with namespace qualifiers to allow it to uniquely identify the resources
    under its control.
    """

    def __init__(self, bigip, partition, prefix=None, schema_path=None):
        """Initialize an instance of the F5 CCCL service manager.

        :param bigip: BIG-IP management root.
        :param partition: Name of BIG-IP partition to manage.
        :param prefix:  The prefix assigned to resources that should be
        managed by this CCCL instance.  This is prepended to the
        resource name (default: None)
        :param schema_path: User defined schema (default: from package)
        """
        LOGGER.debug("F5CloudServiceManager initialize")
        self._bigip_proxy = BigIPProxy(bigip,
                                       partition,
                                       prefix=prefix)

        if schema_path is None:
            schema_path = pkg_resources.resource_filename(resource_package,
                                                          ltm_api_schema)
        self._service_manager = ServiceManager(self._bigip_proxy,
                                               partition,
                                               schema_path)

    def apply_ltm_config(self, services):
        """Apply LTM service configurations to the BIG-IP partition.

        :param services: A serializable object that defines one or more
        services. Its schema is defined by cccl-ltm-api-schema.json.

        :return: True if successful, otherwise an exception is thrown.
        """
        return self._service_manager.apply_ltm_config(services)

    def apply_net_config(self, services):
        """Apply NET service configurations to the BIG-IP partition.

        :param services: A serializable object that defines one or more
        services. Its schema is defined by cccl-net-api-schema.json.

        :return: True if successful, otherwise an exception is thrown.
        """
        return self._service_manager.apply_net_config(services)

    def get_partition(self):
        """Get the name of the managed partition.

        :return: The managed partition name.
        """
        return self._service_manager.get_partition()

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
