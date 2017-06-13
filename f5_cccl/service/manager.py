"""Manages the creation and deployment of desired services configuration."""
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

from __future__ import print_function

import f5_cccl.exceptions as exc
from f5_cccl.service.config_reader import ServiceConfigReader
from f5_cccl.service.validation import ServiceConfigValidator


class ServiceConfigDeployer(object):
    """CCCL config deployer class."""

    def __init__(self, bigip):
        """Initialize the config deployer."""
        self._bigip = bigip

    def _get_resource_tasks(self, existing, desired):
        """Get the list of resources to create, delete, update."""
        create_list = [
            desired[resource] for resource in
            set(desired) - set(existing)
        ]
        update_list = set(desired) & set(existing)
        update_list = [
            desired[resource] for resource in update_list
            if desired[resource] != existing[resource]
        ]
        delete_list = [
            existing[resource] for resource in
            set(existing) - set(desired)
        ]

        return (create_list, update_list, delete_list)

    def _create_resources(self, create_list):
        """Iterate over the resources and call create method."""
        retry_list = list()
        for resource in create_list:
            try:
                print("Creating %s..." % resource.name)
                resource.create(self._bigip)
            except exc.F5CcclResourceConflictError:
                print("Resource %s already exists, skipping task..." %
                      resource.name)
            except (exc.F5CcclResourceCreateError,
                    exc.F5CcclError) as e:
                print(str(e))
                print("Resource %s creation error, requeuing task..." %
                      resource.name)
                retry_list.append(resource)

        return retry_list

    def _update_resources(self, update_list):
        """Iterate over the resources and call update method."""
        retry_list = list()
        for resource in update_list:
            try:
                print("Updating %s..." % resource.name)
                resource.update(self._bigip)
            except exc.F5CcclResourceNotFoundError as e:
                print("Resource %s does not exist, skipping task..." %
                      resource.name)
            except (exc.F5CcclResourceUpdateError,
                    exc.F5CcclResourceRequestError,
                    exc.F5CcclError) as e:
                print(str(e))
                print("Resource %s update error, requeuing task" %
                      resource.name)
                retry_list.append(resource)

        return retry_list

    def _delete_resources(self, delete_list, retry=True):
        """Iterate over the resources and call delete method."""
        retry_list = list()
        for resource in delete_list:
            try:
                print("Deleting %s..." % resource.name)
                resource.delete(self._bigip)
            except exc.F5CcclResourceNotFoundError:
                print("Resource %s does not exist, skipping task..." %
                      resource.name)
            except (exc.F5CcclResourceDeleteError,
                    exc.F5CcclResourceRequestError,
                    exc.F5CcclError) as e:
                print(str(e))
                if retry:
                    print("Resource %s delete error, requeuing task" %
                          resource.name)
                    retry_list.append(resource)

        return retry_list

    def _get_monitor_tasks(self, desired_config):
        """Get CRUD tasks for all monitors."""
        create_monitors = list()
        delete_monitors = list()
        update_monitors = list()

        for hm_type in ['http', 'https', 'tcp', 'icmp']:
            existing = self._bigip.get_monitors(hm_type)
            config_key = "{}_monitors".format(hm_type)
            desired = desired_config.get(config_key, dict())

            (create_hm, update_hm, delete_hm) = (
                self._get_resource_tasks(existing, desired))

            create_monitors += create_hm
            update_monitors += update_hm
            delete_monitors += delete_hm

        return (create_monitors, update_monitors, delete_monitors)

    def _cleanup_nodes(self):
        """Delete any unused nodes in a partition from the BIG-IP."""
        self._bigip.refresh()
        nodes = self._bigip.get_nodes()
        pools = self._bigip.get_pools(True)

        # Search pool members for nodes still in-use, if the node is still
        # being used, remove it from nodes
        for pool in pools:
            for member in pools[pool].members:
                addr = member.name.split('%3A')[0]
                if addr in nodes:
                    # Still in-use
                    del nodes[addr]

        # What's left in nodes is not referenced, delete them
        node_list = [nodes[node] for node in nodes]
        self._delete_resources(node_list, False)

    def deploy(self, desired_config):  # pylint: disable=too-many-locals
        """Deploy the managed partition with the desired config.

        :param desired_config: A dictionary with the configuration
        to be applied to the bigip managed partition.

        :returns: The number of tasks that could not be completed.
        """
        self._bigip.refresh()

        # Get the list of virtual server tasks
        existing = self._bigip.get_virtuals()
        desired = desired_config.get('virtuals', dict())
        (create_virtuals, update_virtuals, delete_virtuals) = (
            self._get_resource_tasks(existing, desired))

        # Get the list of pool tasks
        existing = self._bigip.get_pools()
        desired = desired_config.get('pools', dict())
        (create_pools, update_pools, delete_pools) = (
            self._get_resource_tasks(existing, desired))

        # Get the list of iapp tasks
        existing = self._bigip.get_app_svcs()
        desired = desired_config.get('iapps', dict())
        (create_iapps, update_iapps, delete_iapps) = (
            self._get_resource_tasks(existing, desired))

        # Get the list of monitor tasks
        (create_monitors, update_monitors, delete_monitors) = (
            self._get_monitor_tasks(desired_config))

        create_tasks = create_monitors + create_pools + create_virtuals + \
            create_iapps
        update_tasks = update_monitors + update_pools + update_virtuals + \
            update_iapps
        delete_tasks = delete_iapps + delete_virtuals + delete_pools + \
            delete_monitors

        taskq_len = len(create_tasks) + len(update_tasks) + len(delete_tasks)

        # 'finished' indicates that the task queue is empty, or there is
        # no way to continue to make progress.  If there are errors in
        # deploying any resource, it is saved in the queue until another
        # pass can be made to deploy the configuration.  When we have
        # gone through the queue on a pass without shrinking the task
        # queue, it is determined that progress has stopped and the
        # loop is exited with work remaining.
        finished = False
        while not finished:
            # Iterate over the list of resources to create
            create_tasks = self._create_resources(create_tasks)

            # Iterate over the list of resources to update
            update_tasks = self._update_resources(update_tasks)

            # Iterate over the list of resources to delete
            delete_tasks = self._delete_resources(delete_tasks)

            tasks_remaining = (
                len(create_tasks) + len(update_tasks) + len(delete_tasks))

            # Did the task queue shrink?
            if tasks_remaining >= taskq_len:
                # No, we have stopped making progress.
                finished = True

            # Reset the taskq length.
            taskq_len = tasks_remaining

        # Delete unreferenced nodes
        self._cleanup_nodes()

        return taskq_len


class ServiceManager(object):
    """CCCL apply config implementation class."""

    def __init__(self, bigip, partition, schema, prefix=None):
        """Initialize the ServiceManager."""
        self._bigip = bigip
        self._partition = partition
        self._prefix = prefix
        self._config_validator = ServiceConfigValidator(schema)
        self._service_deployer = ServiceConfigDeployer(self._bigip)
        self._config_reader = ServiceConfigReader(self._partition)

    def apply_config(self, service_config):
        """Apply the desired service configuration."""
        # Validate the service configuration.
        self._config_validator.validate(service_config)

        # Read in the configuration
        desired_config = self._config_reader.read_config(service_config)

        # Refresh the BigIP state.
        self._bigip.refresh()

        # Deploy the service desired configuratio.
        return self._service_deployer.deploy(desired_config)
