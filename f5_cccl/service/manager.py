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

import logging
from time import time

import f5_cccl.exceptions as exc
from f5_cccl.service.config_reader import ServiceConfigReader
from f5_cccl.service.validation import ServiceConfigValidator
from f5_cccl.resource.ltm.node import Node


LOGGER = logging.getLogger(__name__)


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
        LOGGER.debug("Creating %d resources...", len(create_list))
        retry_list = list()
        for resource in create_list:
            try:
                start_time = time()
                resource.create(self._bigip)
                LOGGER.debug("Created %s in %.5f seconds.",
                             resource.name, (time() - start_time))
            except exc.F5CcclResourceConflictError:
                LOGGER.warning(
                    "Resource /%s/%s already exists, skipping task...",
                    resource.partition, resource.name)
            except (exc.F5CcclResourceCreateError,
                    exc.F5CcclError) as e:
                LOGGER.error(str(e))
                LOGGER.error(
                    "Resource /%s/%s creation error, requeuing task...",
                    resource.partition, resource.name)
                retry_list.append(resource)

        return retry_list

    def _update_resources(self, update_list):
        """Iterate over the resources and call update method."""
        LOGGER.debug("Updating %d resources...", len(update_list))
        retry_list = list()
        for resource in update_list:
            try:
                start_time = time()
                resource.update(self._bigip)
                LOGGER.debug("Updated %s in %.5f seconds.",
                             resource.name, (time() - start_time))
            except exc.F5CcclResourceNotFoundError as e:
                LOGGER.warning(
                    "Resource /%s/%s does not exist, skipping task...",
                    resource.partition, resource.name)
            except (exc.F5CcclResourceUpdateError,
                    exc.F5CcclResourceRequestError,
                    exc.F5CcclError) as e:
                LOGGER.error(str(e))
                LOGGER.error(
                    "Resource /%s/%s update error, requeuing task...",
                    resource.partition, resource.name)
                retry_list.append(resource)

        return retry_list

    def _delete_resources(self, delete_list, retry=True):
        """Iterate over the resources and call delete method."""
        LOGGER.debug("Deleting %d resources...", len(delete_list))
        retry_list = list()
        for resource in delete_list:
            try:
                start_time = time()
                resource.delete(self._bigip)
                LOGGER.debug("Deleted %s in %.5f seconds.",
                             resource.name, (time() - start_time))
            except exc.F5CcclResourceNotFoundError:
                LOGGER.warning(
                    "Resource /%s/%s does not exist, skipping task...",
                    resource.partition, resource.name)
            except (exc.F5CcclResourceDeleteError,
                    exc.F5CcclResourceRequestError,
                    exc.F5CcclError) as e:
                LOGGER.error(str(e))
                if retry:
                    LOGGER.error(
                        "Resource /%s/%s delete error, requeuing task...",
                        resource.partition, resource.name)
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

    def _desired_nodes(self):
        """Desired nodes is inferred from the active pool members."""
        desired_nodes = dict()

        nodes = self._bigip.get_nodes()
        pools = self._bigip.get_pools(True)
        for pool in pools:
            for member in pools[pool].members:
                addr = member.name.split('%3A')[0]
                # make a copy to iterate over, then delete from 'nodes'
                node_list = list(nodes.keys())
                for key in node_list:
                    if nodes[key].data['address'] == addr:
                        node = {'name': key,
                                'partition': nodes[key].partition,
                                'address': addr,
                                'state': 'user-up',
                                'session': 'user-enabled'}
                        desired_nodes[key] = Node(**node)

        return desired_nodes

    def _post_deploy(self, desired_config):
        """Perform post-deployment service tasks/cleanup.

        Remove superfluous resources that could not be inferred from the
        desired config.
        """
        LOGGER.debug("Perform post-deploy service tasks...")
        self._bigip.refresh()

        # Delete/update nodes (no creation)
        LOGGER.debug("Post-process nodes.")
        existing = self._bigip.get_nodes()
        desired = self._desired_nodes()
        (update_nodes, delete_nodes) = \
            self._get_resource_tasks(existing, desired)[1:3]
        self._update_resources(update_nodes)
        self._delete_resources(delete_nodes)

        # Delete extraneous virtual addresses
        LOGGER.debug("Remove superfluous virtual addresses.")
        desired = desired_config.get('virtual_addresses', dict())
        extra_vaddrs = self._bigip.find_unreferenced_virtual_addrs()
        delete_vaddrs = self._get_resource_tasks(extra_vaddrs, desired)[2]
        self._delete_resources(delete_vaddrs)

    def deploy(self, desired_config):  # pylint: disable=too-many-locals
        """Deploy the managed partition with the desired config.

        :param desired_config: A dictionary with the configuration
        to be applied to the bigip managed partition.

        :returns: The number of tasks that could not be completed.
        """
        self._bigip.refresh()

        # Get the list of virtual address tasks
        LOGGER.debug("Getting virtual address tasks...")
        existing = self._bigip.get_virtual_addresses()
        desired = desired_config.get('virtual_addresses', dict())
        (create_vaddrs, update_vaddrs) = (
            self._get_resource_tasks(existing, desired))[0:2]

        # Get the list of virtual server tasks
        LOGGER.debug("Getting virtual server tasks...")
        existing = self._bigip.get_virtuals()
        desired = desired_config.get('virtuals', dict())
        (create_virtuals, update_virtuals, delete_virtuals) = (
            self._get_resource_tasks(existing, desired))

        # Get the list of pool tasks
        LOGGER.debug("Getting pool tasks...")
        existing = self._bigip.get_pools()
        desired = desired_config.get('pools', dict())
        (create_pools, update_pools, delete_pools) = (
            self._get_resource_tasks(existing, desired))

        # Get the list of policy tasks
        LOGGER.debug("Getting policy tasks...")
        existing = self._bigip.get_l7policies()
        desired = desired_config.get('l7policies', dict())
        (create_policies, update_policies, delete_policies) = (
            self._get_resource_tasks(existing, desired))

        # Get the list of iapp tasks
        LOGGER.debug("Getting iApp tasks...")
        existing = self._bigip.get_app_svcs()
        desired = desired_config.get('iapps', dict())
        (create_iapps, update_iapps, delete_iapps) = (
            self._get_resource_tasks(existing, desired))

        # Get the list of monitor tasks
        LOGGER.debug("Getting monitor tasks...")
        (create_monitors, update_monitors, delete_monitors) = (
            self._get_monitor_tasks(desired_config))

        LOGGER.debug("Building task lists...")
        create_tasks = create_vaddrs + create_monitors + \
            create_pools + create_policies + create_virtuals + create_iapps
        update_tasks = update_vaddrs + update_monitors + \
            update_pools + update_policies + update_virtuals + update_iapps
        delete_tasks = delete_iapps + delete_virtuals + delete_policies + \
            delete_pools + delete_monitors

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
            LOGGER.debug("Service task queue length: %d", taskq_len)

            # Iterate over the list of resources to create
            create_tasks = self._create_resources(create_tasks)

            # Iterate over the list of resources to update
            update_tasks = self._update_resources(update_tasks)

            # Iterate over the list of resources to delete
            delete_tasks = self._delete_resources(delete_tasks)

            tasks_remaining = (
                len(create_tasks) + len(update_tasks) + len(delete_tasks))

            # Did the task queue shrink?
            if tasks_remaining >= taskq_len or tasks_remaining == 0:
                # No, we have stopped making progress.
                finished = True

            # Reset the taskq length.
            taskq_len = tasks_remaining

        self._post_deploy(desired_config)

        return taskq_len


class ServiceManager(object):
    """CCCL apply config implementation class."""

    def __init__(self, bigip, partition, schema, prefix=None):
        """Initialize the ServiceManager.

        Raises:
        F5CcclError: Error initializing the validator or reading the
        API schema.
        """
        self._bigip = bigip
        self._partition = partition
        self._prefix = prefix
        self._config_validator = ServiceConfigValidator(schema)
        self._service_deployer = ServiceConfigDeployer(self._bigip)
        self._config_reader = ServiceConfigReader(self._partition)

    def get_partition(self):
        """Get the name of the managed partition."""
        return self._partition

    def apply_config(self, service_config):
        """Apply the desired service configuration."""

        LOGGER.debug("apply_config start")
        start_time = time()

        # Validate the service configuration.
        self._config_validator.validate(service_config)

        # Read in the configuration
        desired_config = self._config_reader.read_config(service_config)

        # Deploy the service desired configuratio.
        retval = self._service_deployer.deploy(desired_config)

        LOGGER.debug(
            "apply_config took %.5f seconds.", (time() - start_time))

        return retval
