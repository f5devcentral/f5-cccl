# Copyright 2017 F5 Networks
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""BIG-IP Configuration Manager for the Cloud.

The CloudBigIP class (derived from f5.bigip) manages the state of a BIG-IP
based upon changes in the state of apps and tasks in Marathon; or services,
nodes, and pods in Kubernetes.

CloudBigIP manages the following BIG-IP resources:

    * Virtual Servers
    * Virtual Addresses
    * Pools
    * Pool Members
    * Nodes
    * Health Monitors
    * Application Services
"""

import logging
import urllib

import ipaddress
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from f5_cccl.common import list_diff, list_intersect

import f5
from f5.bigip import BigIP
from f5_cccl.resource import Resource
import icontrol.session

logger = logging.getLogger('controller')
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)


def log_sequence(prefix, sequence_to_log):
    """Helper function to log a sequence.

    Dump a sequence to the logger, skip if it is empty

    Args:
        prefix: The prefix string to describe what's being logged
        sequence_to_log: The sequence being logged
    """
    if sequence_to_log:
        logger.debug(prefix + ': %s', (', '.join(sequence_to_log)))


def healthcheck_timeout_calculate(data):
    """Calculate a BIG-IP Health Monitor timeout.

    Args:
        data: BIG-IP config dict
    """
    # Calculate timeout
    # See the f5 monitor docs for explanation of settings:
    # https://goo.gl/JJWUIg
    # Formula to match up the cloud settings with f5 settings:
    # (( maxConsecutiveFailures - 1) * intervalSeconds )
    # + timeoutSeconds + 1
    timeout = (
        ((data['maxConsecutiveFailures'] - 1) * data['intervalSeconds']) +
        data['timeoutSeconds'] + 1
    )
    return timeout


def get_protocol(protocol):
    """Return the protocol (tcp or udp)."""
    if str(protocol).lower() == 'tcp':
        return 'tcp'
    if str(protocol).lower() == 'http':
        return 'tcp'
    if str(protocol).lower() == 'udp':
        return 'udp'
    else:
        return None


def has_partition(partitions, app_partition):
    """Check if the app_partition is one we're responsible for."""
    # App has no partition specified
    if not app_partition:
        return False

    # All partitions / wildcard match
    if '*' in partitions:
        return True

    # empty partition only
    if len(partitions) == 0 and not app_partition:
        raise Exception("No partitions specified")

    # Contains matching partitions
    if app_partition in partitions:
        return True

    return False


class CloudBigIP(BigIP):
    """CloudBigIP class.

    Generates a configuration for a BigIP based upon the apps/tasks managed
    by Marathon or services/pods/nodes in Kubernetes.

    - Matches apps/sevices by BigIP partition
    - Creates a Virtual Server and pool for each service type that matches a
      BigIP partition
    - For each backend (task, node, or pod), it creates a pool member and adds
      the member to the pool
    - If the app has a Marathon Health Monitor configured, create a
      corresponding health monitor for the BigIP pool member
    - Token-based authentication is used by specifying a token named 'tmos'.
      This will allow non-admin users to use the API (BIG-IP must configure
      the accounts with proper permissions, for either local or remote auth).

    Args:
        hostname: IP address of BIG-IP
        port: Port of BIG-IP
        username: BIG-IP username
        password: BIG-IP password
        partitions: List of BIG-IP partitions to manage
        token: The optional auth token to use with BIG-IP (e.g. "tmos")
    """

    def __init__(self, hostname, port, username, password, partitions,
                 token=None, manage_types=None):
        """Initialize the CloudBigIP object."""
        super_kwargs = {"port": port}
        if token:
            super_kwargs["token"] = token
        super(CloudBigIP, self).__init__(hostname, username, password,
                                         **super_kwargs)
        self._hostname = hostname
        self._port = port
        self._username = username
        self._password = password
        self._partitions = partitions
        self._lbmethods = (
            "dynamic-ratio-member",
            "least-connections-member",
            "observed-node",
            "ratio-least-connections-node",
            "round-robin",
            "dynamic-ratio-node",
            "least-connections-node",
            "predictive-member",
            "ratio-member",
            "weighted-least-connections-member",
            "fastest-app-response",
            "least-sessions",
            "predictive-node",
            "ratio-node",
            "weighted-least-connections-node",
            "fastest-node",
            "observed-member",
            "ratio-least-connections-member",
            "ratio-session"
        )
        # This currently hard codes what resources we care about until we
        # enable policy management.
        if manage_types is None:
            manage_types = ['/tm/ltm/virtual', '/tm/ltm/pool',
                            '/tm/ltm/monitor', '/tm/sys/application/service']

        self._manage_virtual = '/tm/ltm/virtual' in manage_types
        self._manage_pool = '/tm/ltm/pool' in manage_types
        self._manage_monitor = '/tm/ltm/monitor' in manage_types
        self._manage_policy = '/tm/ltm/policy' in manage_types
        self._manage_iapp = '/tm/sys/application/service' in manage_types

    def get_partitions(self):
        """Getter for partitions."""
        return self._partitions

    def is_label_data_valid(self, app):
        """Validate the Marathon app's label data.

        Args:
            app: The app to be validated
        """
        is_valid = True
        msg = 'Application label {0} for {1} contains an invalid value: {2}'

        # Validate mode
        if get_protocol(app.mode) is None:
            logger.error(msg.format('F5_MODE', app.appId, app.mode))
            is_valid = False

        # Validate port
        if app.servicePort < 1 or app.servicePort > 65535:
            logger.error(msg.format('F5_PORT', app.appId, app.servicePort))
            is_valid = False

        # Validate address
        if app.bindAddr is not None:
            try:
                ipaddress.ip_address(app.bindAddr)
            except ValueError:
                logger.error(msg.format('F5_BIND_ADDR',
                                        app.appId, app.bindAddr))
                is_valid = False

        # Validate LB method
        if app.balance not in self._lbmethods:
            logger.error(msg.format('F5_BALANCE', app.appId, app.balance))
            is_valid = False

        return is_valid

    def regenerate_config_f5(self, cfg):
        """Configure the BIG-IP based on the configuration.

        Args:
            cfg: configuration
        """
        try:
            self._apply_config(cfg)

        # Handle F5/BIG-IP exceptions here
        except requests.exceptions.ConnectionError as e:
            logger.error("Connection error: {}".format(e))
            # Indicate that we need to retry
            return True
        except f5.sdk_exception.F5SDKError as e:
            logger.error("Resource Error: {}".format(e))
            # Indicate that we need to retry
            return True
        except icontrol.exceptions.BigIPInvalidURL as e:
            logger.error("Invalid URL: {}".format(e))
            # Indicate that we need to retry
            return True
        except icontrol.exceptions.iControlUnexpectedHTTPError as e:
            logger.error("HTTP Error: {}".format(e))
            # Indicate that we need to retry
            return True
        except Exception:
            # Occasionally the SDK/BIG-IP fails to return an object and we
            # don't expect this to ever occur.
            logger.exception("Exception Error")
            # Indicate that we need to retry
            return True

        return False

    def _apply_config(self, config):
        """Apply the configuration to the BIG-IP.

        Args:
            config: BIG-IP config dict
        """
        svcs = config.get('virtualServers', {})
        policies = config.get('l7Policies', [])
        pools = config.get('pools', [])
        monitors = config.get('monitors', [])

        unique_partitions = self.get_managed_partition_names(self._partitions)
        for partition in unique_partitions:
            logger.debug("Doing config for partition '%s'", partition)

            cloud_virtual_list = []
            if self._manage_virtual:
                cloud_virtual_list = \
                    [x for x in svcs.keys()
                     if svcs[x]['partition'] == partition and
                     'iapp' not in svcs[x] and svcs[x]['virtual']]

            cloud_pool_list = []
            if self._manage_pool:
                for pool in pools:
                    # multiple pools per virtual need index stripped
                    vname = pool['name'].rsplit('_', 1)[0]
                    if pool['partition'] == partition:
                        svc = None
                        if pool['name'] in svcs:
                            svc = svcs[pool['name']]
                        elif vname in svcs:
                            svc = svcs[vname]

                        if None is svc:
                            cloud_pool_list.append(pool['name'])
                        else:
                            if 'iapp' not in svc:
                                cloud_pool_list.append(pool['name'])

            cloud_iapp_list = []
            if self._manage_iapp:
                cloud_iapp_list = \
                    [x for x in svcs.keys()
                     if svcs[x]['partition'] == partition and
                     'iapp' in svcs[x]]

            cloud_healthcheck_list = []
            if self._manage_monitor:
                for mon in monitors:
                    if mon['partition'] == partition and 'protocol' in mon:
                        cloud_healthcheck_list.append(mon['name'])

            cloud_policy_list = []
            if self._manage_policy:
                for policy in policies:
                        cloud_policy_list.append(policy['name'])

            # Configure iApps
            f5_iapp_list = []
            if self._manage_iapp:
                f5_iapp_list = self.get_iapp_list(partition)
            log_sequence('f5_iapp_list', f5_iapp_list)
            log_sequence('cloud_iapp_list', cloud_iapp_list)

            # iapp delete
            iapp_delete = list_diff(f5_iapp_list, cloud_iapp_list)
            log_sequence('iApps to delete', iapp_delete)
            for iapp in iapp_delete:
                self.iapp_delete(partition, iapp)

            f5_pool_list = []
            if self._manage_pool:
                f5_pool_list = self.get_pool_list(partition, False)
            f5_virtual_list = []
            if self._manage_virtual:
                f5_virtual_list = self.get_virtual_list(partition)
            f5_policy_list = []
            if self._manage_policy:
                f5_policy_list = self.get_policy_list(partition)

            # get_healthcheck_list() returns a dict with healthcheck names for
            # keys and a subkey of "type" with a value of "tcp", "http", etc.
            # We need to know the type to correctly reference the resource.
            # i.e. monitor types are different resources in the f5-sdk
            f5_healthcheck_list = []
            if self._manage_monitor:
                f5_healthcheck_dict = self.get_healthcheck_list(partition)
                logger.debug("f5_healthcheck_dict:   %s", f5_healthcheck_dict)
                # and then we need just the list to identify differences from
                # the list returned from the cloud environment
                f5_healthcheck_list = f5_healthcheck_dict.keys()

            log_sequence('f5_pool_list', f5_pool_list)
            log_sequence('f5_virtual_list', f5_virtual_list)
            log_sequence('f5_policy_list', f5_policy_list)
            log_sequence('f5_healthcheck_list', f5_healthcheck_list)
            log_sequence('cloud_pool_list', cloud_pool_list)
            log_sequence('cloud_virtual_list', cloud_virtual_list)

            # healthcheck config needs to happen before pool config because
            # the pool is where we add the healthcheck
            # healthcheck add: use the name of the virt for the healthcheck
            healthcheck_add = list_diff(cloud_healthcheck_list,
                                        f5_healthcheck_list)
            log_sequence('Healthchecks to add', healthcheck_add)

            # healthcheck add
            for mon in monitors:
                if (mon['partition'] == partition and
                        mon['name'] in healthcheck_add):
                    self.healthcheck_create(partition, mon)

            # pool add
            pool_add = list_diff(cloud_pool_list, f5_pool_list)
            log_sequence('Pools to add', pool_add)
            for pool in pools:
                if 'name' in pool and pool['name'] in pool_add:
                    self.pool_create(pool)

            # policy add
            policy_add = list_diff(cloud_policy_list, f5_policy_list)
            log_sequence('Policies to add', policy_add)
            for policy in policies:
                if 'name' in policy and policy['name'] in policy_add:
                    self.policy_create(policy)

            # virtual add
            virt_add = list_diff(cloud_virtual_list, f5_virtual_list)
            log_sequence('Virtual Servers to add', virt_add)
            for virt in virt_add:
                self.virtual_create(partition, virt, svcs[virt])

            # healthcheck intersection
            healthcheck_intersect = list_intersect(cloud_healthcheck_list,
                                                   f5_healthcheck_list)
            log_sequence('Healthchecks to update', healthcheck_intersect)

            # healthcheck intersect
            for mon in monitors:
                if (mon['partition'] == partition and
                        mon['name'] in healthcheck_intersect):
                    self.healthcheck_update(partition, mon['name'], mon)

            # pool intersection
            pool_intersect = list_intersect(cloud_pool_list, f5_pool_list)
            log_sequence('Pools to update', pool_intersect)
            for pool in pools:
                if 'name' in pool and pool['name'] in pool_intersect:
                    self.pool_update(pool['name'], pool)

            # policy intersection
            policy_intersect = list_intersect(cloud_policy_list,
                                              f5_policy_list)
            for policy in policies:
                if 'name' in policy and policy['name'] in policy_intersect:
                    self.policy_update(partition, policy)

            # virt intersection
            virt_intersect = list_intersect(cloud_virtual_list,
                                            f5_virtual_list)
            log_sequence('Virtual Servers to update', virt_intersect)

            for virt in virt_intersect:
                self.virtual_update(partition, virt, svcs[virt])

            # virtual delete
            virt_delete = list_diff(f5_virtual_list, cloud_virtual_list)
            log_sequence('Virtual Servers to delete', virt_delete)
            for virt in virt_delete:
                self.virtual_delete(partition, virt)

            # policy delete
            policy_delete = list_diff(f5_policy_list, cloud_policy_list)
            log_sequence('Policies to delete', policy_delete)
            for policy in policy_delete:
                self.policy_delete(partition, policy)

            # pool delete
            pool_delete_list = list_diff(f5_pool_list, cloud_pool_list)
            log_sequence('Pools to delete', pool_delete_list)
            for pool in pool_delete_list:
                self.pool_delete(partition, pool)

            # healthcheck delete
            health_delete = list_diff(f5_healthcheck_list,
                                      cloud_healthcheck_list)
            log_sequence('Healthchecks to delete', health_delete)
            for hc in health_delete:
                self.healthcheck_delete(partition, hc,
                                        f5_healthcheck_dict[hc]['type'])

            # iapp add
            iapp_add = list_diff(cloud_iapp_list, f5_iapp_list)
            log_sequence('iApps to add', iapp_add)
            for iapp in iapp_add:
                pool = None
                for p in pools:
                    if p['name'] == iapp:
                        pool = p
                self.iapp_create(partition, iapp, svcs[iapp], pool)

            # iapp update
            iapp_intersect = list_intersect(cloud_iapp_list, f5_iapp_list)
            log_sequence('iApps to update', iapp_intersect)
            for iapp in iapp_intersect:
                pool = None
                for p in pools:
                    if p['name'] == iapp:
                        pool = p
                self.iapp_update(partition, iapp, svcs[iapp], pool)

            # add/update/remove pool members
            # need to iterate over pool_add and pool_intersect (note that
            # removing a pool also removes members, so don't have to
            # worry about those)
            for pool in list(set(pool_add + pool_intersect)):
                logger.debug("Pool: %s", pool)

                f5_member_list = self.get_pool_member_list(partition, pool)
                for pl in pools:
                    if pl['name'] == pool:
                        cloud_member_list = (pl['members']).keys()

                member_delete_list = list_diff(f5_member_list,
                                               cloud_member_list)
                log_sequence('Pool members to delete', member_delete_list)
                for member in member_delete_list:
                    self.member_delete(partition, pool, member)

                member_add = list_diff(cloud_member_list, f5_member_list)
                log_sequence('Pool members to add', member_add)
                for member in member_add:
                    for pl in pools:
                        if pl['name'] == pool:
                            self.member_create(partition, pool, member,
                                               pl['members'][member])

                # Since we're only specifying hostname and port for members,
                # 'member_update' will never actually get called. Changing
                # either of these properties will result in a new member being
                # created and the old one being deleted. I'm leaving this here
                # though in case we add other properties to members
                member_update_list = list_intersect(cloud_member_list,
                                                    f5_member_list)
                log_sequence('Pool members to update', member_update_list)

                for member in member_update_list:
                    for pl in pools:
                        if pl['name'] == pool:
                            self.member_update(partition, pool, member,
                                               pl['members'][member])

            # Delete any unreferenced nodes
            self.cleanup_nodes(partition)

    def cleanup_nodes(self, partition):
        """Delete any unused nodes in a partition from the BIG-IP.

        Args:
            partition: Partition name
        """
        node_list = self.get_node_list(partition)
        pool_list = self.get_pool_list(partition, True)

        # Search pool members for nodes still in-use, if the node is still
        # being used, remove it from the node list
        for pool in pool_list:
            member_list = self.get_pool_member_list(partition, pool)
            for member in member_list:
                name = member[:member.find(':')]
                if name in node_list:
                    # Still in-use
                    node_list.remove(name)

                    node = self.get_node(name=name, partition=partition)
                    data = {'state': 'user-up', 'session': 'user-enabled'}

                    # Node state will be 'up' if it has a monitor attached,
                    # and 'unchecked' for no monitor
                    if node.state == 'up' or node.state == 'unchecked':
                        if 'enabled' in node.session:
                            continue

                    node.modify(**data)

        # What's left in the node list is not referenced, delete
        for node in node_list:
            self.node_delete(node, partition)

    def node_delete(self, node_name, partition):
        """Delete a node from the BIG-IP partition.

        Args:
            node_name: Node name
            partition: Partition name
        """
        node = self.ltm.nodes.node.load(name=urllib.quote(node_name),
                                        partition=partition)
        node.delete()

    def get_pool(self, partition, name):
        """Get a pool object.

        Args:
            partition: Partition name
            name: Pool name
        """
        # return pool object

        # FIXME(kenr): This is the efficient way to lookup a pool object:
        #
        #       p = self.ltm.pools.pool.load(
        #           name=name,
        #           partition=partition
        #       )
        #       return p
        #
        # However, this won't work for iapp created pools because they
        # add a subPath component that is the iapp name appended by '.app'.
        # To properly use the above code, we need to pass in the iapp name.
        #
        # The alternative (below) is to get the collection of pool objects
        # and then search the list for the matching pool name. However, we
        # will return the first pool found even though there are multiple
        # choices (if iapps are used).  See issue #138.
        pools = self.ltm.pools.get_collection()
        for pool in pools:
            if pool.partition == partition and pool.name == name:
                return pool
        raise Exception("Failed to retrieve resource for pool {} "
                        "in partition {}".format(name, partition))

    def get_pool_list(self, partition, all_pools):
        """Get a list of pool names for a partition.

        Args:
            partition: Partition name
            all_pools: Return all pools (True) or only non-appService
                       pools (False)
        """
        pool_list = []
        pools = self.ltm.pools.get_collection()
        for pool in pools:
            appService = getattr(pool, 'appService', None)
            # pool must match partition and not belong to an appService
            if pool.partition == partition and \
               (appService is None or all_pools):
                pool_list.append(pool.name)
        return pool_list

    def pool_create(self, pool):
        """Create a pool.

        Args:
            pool: Name of pool to create
            data: BIG-IP config dict
        """
        logger.debug("Creating pool %s", pool['name'])
        p = self.ltm.pools.pool

        p.create(**pool)

    def pool_delete(self, partition, pool):
        """Delete a pool.

        Args:
            partition: Partition name
            pool: Name of pool to delete
        """
        logger.debug("deleting pool %s", pool)
        p = self.get_pool(partition, pool)
        p.delete()

    def pool_update(self, pool, data):
        """Update a pool.

        Args:
            pool: Name of pool to update
            data: BIG-IP config dict
        """
        pool = self.get_pool(data['partition'], pool)

        def find_change(p, d):
            """Check if data for pool has been updated."""
            for key, val in p.__dict__.iteritems():
                if key in d:
                    if (val is not None and isinstance(val, str)
                            and (d[key] != val.strip())):
                        return True
                    elif (d[key] != val and isinstance(val, str)):
                        return True
            for key, _ in d.iteritems():
                if key not in p.__dict__:
                    return True
            return False

        if find_change(pool, data):
            pool.modify(**data)
            return True

        return False

    def get_member(self, partition, pool, member):
        """Get a pool-member object.

        Args:
            partition: Partition name
            pool: Name of pool
            member: Name of pool member
        """
        p = self.get_pool(partition, pool)
        m = p.members_s.members.load(name=urllib.quote(member),
                                     partition=partition)
        return m

    def get_pool_member_list(self, partition, pool):
        """Get a list of pool-member names.

        Args:
            partition: Partition name
            pool: Name of pool
        """
        member_list = []
        p = self.get_pool(partition, pool)
        members = p.members_s.get_collection()
        for member in members:
            member_list.append(member.name)

        return member_list

    def member_create(self, partition, pool, member, data):
        """Create a pool member.

        Args:
            partition: Partition name
            pool: Name of pool
            member: Name of pool member
            data: BIG-IP config dict
        """
        p = self.get_pool(partition, pool)
        member = p.members_s.members.create(
            name=member, partition=partition, **data)

    def member_delete(self, partition, pool, member):
        """Delete a pool member.

        Args:
            partition: Partition name
            pool: Name of pool
            member: Name of pool member
        """
        member = self.get_member(partition, pool, member)
        member.delete()

    def member_update(self, partition, pool, member, data):
        """Update a pool member.

        Args:
            partition: Partition name
            pool: Name of pool
            member: Name of pool member
            data: BIG-IP config dict
        """
        member = self.get_member(partition, pool, member)

        # Member state will be 'up' if it has a monitor attached,
        # and 'unchecked' for no monitor
        if member.state == 'up' or member.state == 'unchecked':
            if 'enabled' in member.session:
                return False

        member.modify(**data)
        return True

    def get_node(self, partition, name):
        """Get a node object.

        Args:
            partition: Partition name
            name: Name of the node
        """
        if self.ltm.nodes.node.exists(name=urllib.quote(name),
                                      partition=partition):
            return self.ltm.nodes.node.load(name=urllib.quote(name),
                                            partition=partition)
        else:
            return None

    def get_node_list(self, partition):
        """Get a list of node names for a partition.

        Args:
            partition: Partition name
        """
        node_list = []
        nodes = self.ltm.nodes.get_collection()
        for node in nodes:
            if node.partition == partition:
                node_list.append(node.name)

        return node_list

    def get_virtual(self, partition, virtual):
        """Get Virtual Server object.

        Args:
            partition: Partition name
            virtual: Name of the Virtual Server
        """
        # return virtual object
        v = self.ltm.virtuals.virtual.load(name=urllib.quote(virtual),
                                           partition=partition)
        return v

    def get_virtual_list(self, partition):
        """Get a list of virtual-server names for a partition.

        Args:
            partition: Partition name
        """
        virtual_list = []
        virtuals = self.ltm.virtuals.get_collection()
        for virtual in virtuals:
            appService = getattr(virtual, 'appService', None)
            # virtual must match partition and not belong to an appService
            if virtual.partition == partition and appService is None:
                virtual_list.append(virtual.name)

        return virtual_list

    def virtual_create(self, partition, virtual, data):
        """Create a Virtual Server.

        Args:
            partition: Partition name
            virtual: Name of the virtual server
            data: BIG-IP config dict
        """
        logger.debug("Creating Virtual Server %s", virtual)
        data = data['virtual']
        v = self.ltm.virtuals.virtual

        v.create(name=virtual, partition=partition, **data)

    def virtual_delete(self, partition, virtual):
        """Delete a Virtual Server.

        Args:
            partition: Partition name
            virtual: Name of the Virtual Server
        """
        logger.debug("Deleting Virtual Server %s", virtual)
        v = self.get_virtual(partition, virtual)
        v.delete()

    def virtual_update(self, partition, virtual, data):
        """Update a Virtual Server.

        Args:
            partition: Partition name
            virtual: Name of the Virtual Server
            data: BIG-IP config dict
        """
        addr = data['virtual_address']

        # Verify virtual address, recreate it if it doesn't exist
        v_addr = self.get_virtual_address(partition, addr)

        if v_addr is None:
            self.virtual_address_create(partition, addr)
        else:
            self.virtual_address_update(v_addr)

        # Verify Virtual Server
        data = data['virtual']

        v = self.get_virtual(partition, virtual)

        ADDR_IDX = 2
        IP_IDX = 0
        old_addr = \
            v.__dict__['destination'].split('/')[ADDR_IDX].split(':')[IP_IDX]

        no_change = all(data[key] == val for key, val in v.__dict__.iteritems()
                        if key in data)

        # Compare the actual and desired profiles
        profiles = self.get_virtual_profiles(v)

        # Remove inherited tcp profile of an http profile from SDK profiles
        http_profiles = [p for p in data['profiles'] if p['name'] == 'http']
        for http_p in http_profiles:
            inherited_tcp_p = {'name': 'tcp', 'partition': http_p['partition']}
            if inherited_tcp_p in profiles:
                profiles.remove(inherited_tcp_p)

        no_profile_change = sorted(profiles) == sorted(data['profiles'])

        # Compare actual and desired policies
        policies = self.get_virtual_policies(v)
        no_policy_change = sorted(policies) == sorted(data['policies'])

        if no_change and no_profile_change and no_policy_change:
            return False

        v.modify(**data)

        # If the virtual address has been updated cleanup the old one
        if addr != old_addr:
            self.virtual_address_delete(partition, old_addr)

        return True

    def get_virtual_profiles(self, virtual):
        """Get list of Virtual Server profiles from Virtual Server.

        Args:
            virtual: Virtual Server object
        """
        v_profiles = virtual.profiles_s.get_collection()
        profiles = []
        for profile in v_profiles:
            profiles.append({'name': profile.name,
                             'partition': profile.partition})

        return profiles

    def get_virtual_policies(self, virtual):
        """Get list of Virtual Server policies from Virtual Server.

        Args:
            virtual: Virtual Server object
        """
        v_policies = virtual.policies_s.get_collection()
        policies = []
        for policy in v_policies:
            policies.append({'name': policy.name,
                             'partition': policy.partition})

        return policies

    def get_virtual_address(self, partition, name):
        """Get Virtual Address object.

        Args:
            partition: Partition name
            name: Name of the Virtual Address
        """
        if not self.ltm.virtual_address_s.virtual_address.exists(
                name=urllib.quote(name), partition=partition):
            return None
        else:
            return self.ltm.virtual_address_s.virtual_address.load(
                name=urllib.quote(name), partition=partition)

    def virtual_address_create(self, partition, name):
        """Create a Virtual Address.

        Args:
            partition: Partition name
            name: Name of the virtual address
        """
        self.ltm.virtual_address_s.virtual_address.create(
            name=name, partition=partition)

    def virtual_address_update(self, virtual_address):
        """Update a Virtual Address.

        Args:
            virtual_address: Virtual Address object
        """
        if virtual_address.enabled == 'no':
            virtual_address.modify(enabled='yes')

    def virtual_address_delete(self, partition, name):
        """Delete a Virtual Address.
        Args:
            partition: Partition name
            name: Name of the virtual address
        """
        logger.debug("Deleting virtual address %s", name)
        virtual_address = self.get_virtual_address(partition, name)
        virtual_address.delete()

    def get_healthcheck(self, partition, hc, hc_type):
        """Get a Health Monitor object.

        Args:
            partition: Partition name
            hc: Name of the Health Monitor
            hc_type: Health Monitor type
        """
        # return hc object
        if hc_type == 'http':
            hc = self.ltm.monitor.https.http.load(name=urllib.quote(hc),
                                                  partition=partition)
        elif hc_type == 'tcp':
            hc = self.ltm.monitor.tcps.tcp.load(name=urllib.quote(hc),
                                                partition=partition)

        return hc

    def get_healthcheck_list(self, partition):
        """Get a dict of Health Monitors for a partition.

        Args:
            partition: Partition name
        """
        # will need to handle HTTP and TCP

        healthcheck_dict = {}

        # HTTP
        healthchecks = self.ltm.monitor.https.get_collection()
        for hc in healthchecks:
            appService = getattr(hc, 'appService', None)
            # hc must match partition and not belong to an appService
            if hc.partition == partition and appService is None:
                healthcheck_dict.update({hc.name: {'type': 'http'}})

        # TCP
        healthchecks = self.ltm.monitor.tcps.get_collection()
        for hc in healthchecks:
            appService = getattr(hc, 'appService', None)
            # hc must match partition and not belong to an appService
            if hc.partition == partition and appService is None:
                healthcheck_dict.update({hc.name: {'type': 'tcp'}})

        return healthcheck_dict

    def healthcheck_delete(self, partition, hc, hc_type):
        """Delete a Health Monitor.

        Args:
            partition: Partition name
            hc: Name of the Health Monitor
            hc_type: Health Monitor type
        """
        logger.debug("Deleting healthcheck %s", hc)
        hc = self.get_healthcheck(partition, hc, hc_type)
        hc.delete()

    def healthcheck_sendstring(self, data):
        """Return the 'send' string for a health monitor.

        Args:
            data: Health Monitor dict
        """
        if data['protocol'] == "http":
            send_string = 'GET / HTTP/1.0\\r\\n\\r\\n'
            if 'path' in data:
                send_string = 'GET %s HTTP/1.0\\r\\n\\r\\n' % data['path']
            return send_string
        else:
            return None

    def get_healthcheck_fields(self, data):
        """Return a new dict containing only supported health monitor data.

        Args:
            data: Health Monitor dict
        """
        if data['protocol'] == "http":
            send_keys = ('adaptive',
                         'adaptiveDivergenceType',
                         'adaptiveDivergenceValue',
                         'adaptiveLimit',
                         'adaptiveSamplingTimespan',
                         'appService',
                         'defaultsFrom',
                         'description',
                         'destination',
                         'interval',
                         'ipDscp',
                         'manualResume',
                         'name',
                         'tmPartition',
                         'password',
                         'recv',
                         'recvDisable',
                         'reverse',
                         'send',
                         'timeUntilUp',
                         'timeout',
                         'transparent',
                         'upInterval',
                         'username',)
        elif data['protocol'] == "tcp":
            send_keys = ('adaptive',
                         'adaptiveDivergenceType',
                         'adaptiveDivergenceValue',
                         'adaptiveLimit',
                         'adaptiveSamplingTimespan',
                         'appService',
                         'defaultsFrom',
                         'description',
                         'destination',
                         'interval',
                         'ipDscp',
                         'manualResume',
                         'name',
                         'tmPartition',
                         'recv',
                         'recvDisable',
                         'reverse',
                         'send',
                         'timeUntilUp',
                         'timeout',
                         'transparent',
                         'upInterval',)
        else:
            raise Exception(
                'Protocol {} is not supported.'.format(data['protocol']))

        send_data = {}
        for k in data:
            if k in send_keys:
                send_data[k] = data[k]
        return send_data

    def healthcheck_update(self, partition, name, data):
        """Update a Health Monitor.

        Args:
            partition: Partition name
            name: Name of the Health Monitor
            data: Health Monitor dict
        """
        he = self.healthcheck_exists(partition, name)
        httpcheck = he['http']
        tcpcheck = he['tcp']

        if ((httpcheck and data['protocol'] == 'http') or
                (tcpcheck and data['protocol'] == 'tcp')):
            logger.debug("Updating healthcheck %s", name)
            # get healthcheck object
            hc = self.get_healthcheck(partition, name, data['protocol'])

            send_data = self.get_healthcheck_fields(data)

            no_change = all(send_data[key] == val
                            for key, val in hc.__dict__.iteritems()
                            if key in send_data)

            if no_change:
                return False

            hc.modify(**send_data)
            return True
        elif httpcheck:
            self.monitor_protocol_change(partition, name, data, 'http')
        elif tcpcheck:
            self.monitor_protocol_change(partition, name, data, 'tcp')
        elif not httpcheck and not tcpcheck:
            self.healthcheck_create(partition, data)

    def healthcheck_exists(self, partition, name):
        """Check if the health monitor exists.

        Args:
            partition: Partition name
            name: Name of the Health Monitor
            protocol: Protocol to check
        """
        exists = {}
        exists['http'] = self.ltm.monitor.https.http.exists(
            name=urllib.quote(name), partition=partition)
        exists['tcp'] = self.ltm.monitor.tcps.tcp.exists(
            name=urllib.quote(name), partition=partition)
        return exists

    def get_http_healthmonitor(self):
        """Get an object than can create a http health monitor."""
        h = self.ltm.monitor.https
        return h.http

    def get_tcp_healthmonitor(self):
        """Get an object than can create a tcp health monitor."""
        h = self.ltm.monitor.tcps
        return h.tcp

    def healthcheck_create(self, partition, data):
        """Create a Health Monitor.

        Args:
            partition: Partition name
            data: Health Monitor dict
        """
        send_data = self.get_healthcheck_fields(data)

        if data['protocol'] == "http":
            http1 = self.get_http_healthmonitor()
            http1.create(partition=partition, **send_data)

        if data['protocol'] == "tcp":
            tcp1 = self.get_tcp_healthmonitor()
            tcp1.create(partition=partition, **send_data)

    def monitor_protocol_change(self, partition, name, data, old_protocol):
        """Change a health monitor from one protocol to another.

        Args:
            partition:
            name: Partition name
            data: Health Monitor dict
            old_protocol: Protocol health monitor currently uses
        """
        pool = self.get_pool(partition, name)
        pool.monitor = ''
        pool.update()
        self.healthcheck_delete(partition, name, old_protocol)
        self.healthcheck_create(partition, data)
        pool.monitor = name
        pool.update()

    def get_policy(self, partition, policy, requests_params={}):
        """Get Policy object.

        Args:
            partition: Partition name
            policy: Name of the policy
            requests_params: Object with query parameters
        """
        p = self.ltm.policys.policy.load(name=urllib.quote(policy),
                                         partition=partition,
                                         requests_params=requests_params)
        return p

    def get_policy_list(self, partition):
        """Get a list of policy names for a partition.

        Args:
            partition: Partition name
        """
        policy_list = []
        policies = self.ltm.policys.get_collection()
        for policy in policies:
            appService = getattr(policy, 'appService', None)
            # policy must match partition and not belong to an appService
            if policy.partition == partition and appService is None:
                policy_list.append(policy.name)
        return policy_list

    def policy_create(self, data):
        """Create a policy.

        Args:
            partition: Partition name
            data: BIG-IP config dict
        """
        p = self.ltm.policys.policy
        logger.debug("Creating policy %s", data['name'])
        p.create(**data)

    def policy_delete(self, partition, policy):
        """Delete a policy.

        Args:
            partition: Partition name
            policy: Name of policy to delete
        """
        logger.debug("Deleting Policy %s", policy)
        p = self.get_policy(partition, policy)
        p.delete()

    def policy_update(self, partition, data):
        """Update a policy.

        Args:
            partition: Partition name
            data: BIG-IP config dict
        """
        request_params = {'params': 'expandSubcollections=true'}
        bigip_policy = self.get_policy(partition, data['name'], request_params)
        # Convert old and new policy objects to the policy class for comparison
        old_policy = Policy(bigip_policy)
        new_policy = Policy(data)

        if old_policy != new_policy:
            logger.debug("Updating policy %s" % bigip_policy.name)
            bigip_policy.modify(**data)
            return True

        logger.debug("No change to policy %s" % bigip_policy.name)
        return False

    def get_managed_partition_names(self, partitions):
        """Get a list of BIG-IP partition names.

        Args:
            partitions: The list of partition names we're configured to manage
                        (Could be wildcard: '*')
        """
        if '*' in partitions:
            # Wildcard means all partitions, so we need to query BIG-IP for the
            # actual partition names
            partition_list = []
            for folder in self.sys.folders.get_collection():
                if (not folder.name == "Common" and not folder.name == "/" and
                        not folder.name.endswith(".app")):

                    partition_list.append(folder.name)
            return partition_list
        else:
            # No wildcard, so we just care about those already configured
            return partitions

    def iapp_build_definition(self, svcConfig, poolConfig):
        """Create a dict that defines the 'variables' and 'tables' for an iApp.

        Args:
            config: BIG-IP config dict
        """
        # Build variable list
        variables = []
        for key in svcConfig['iapp']['variables']:
            var = {'name': key, 'value': svcConfig['iapp']['variables'][key]}
            variables.append(var)

        # The schema says only one of poolMemberTable or tableName is
        # valid, so if the user set both it should have already been rejected.
        # But if not, prefer the new poolMemberTable over tableName.
        tables = []
        if 'poolMemberTable' in svcConfig['iapp']:
            tableConfig = svcConfig['iapp']['poolMemberTable']

            # Construct columnNames array from the 'name' prop of each column
            columnNames = []
            for col in tableConfig['columns']:
                columnNames.append(col['name'])

            # Construct rows array - one row for each node, interpret the
            # 'kind' or 'value' from the column spec.
            rows = []
            for member in poolConfig['members']:
                row = []
                (addr, port) = member.split(':')
                for i, col in enumerate(tableConfig['columns']):
                    if 'value' in col:
                        row.append(col['value'])
                    elif 'kind' in col:
                        if col['kind'] == 'IPAddress':
                            row.append(addr)
                        elif col['kind'] == 'Port':
                            row.append(port)
                        else:
                            raise ValueError('Unknown kind "%s"' % col['kind'])
                    else:
                        raise ValueError('Column %d has neither value nor kind'
                                         % i)
                rows.append({'row': row})

            # Done - add the generated pool member table to the set of tables
            # we're going to configure.
            tables.append({
                'name': tableConfig['name'],
                'columnNames': columnNames,
                'rows': rows
            })
        elif 'tableName' in svcConfig['iapp']:
            # Before adding the flexible poolMemberTable mode, we only
            # supported three fixed columns in order, and connection_limit was
            # hardcoded to 0 ("no limit")
            rows = []
            for member in poolConfig['members']:
                (addr, port) = member.split(':')
                rows.append({'row': [addr, port, '0']})
            tables.append({
                'name': svcConfig['iapp']['tableName'],
                'columnNames': ['addr', 'port', 'connection_limit'],
                'rows': rows
            })

        # Add other tables
        for key in svcConfig['iapp']['tables']:
            data = svcConfig['iapp']['tables'][key]
            table = {'columnNames': data['columns'],
                     'name': key,
                     'rows': []}
            for row in data['rows']:
                table['rows'].append({'row': row})
            tables.append(table)

        return {'variables': variables, 'tables': tables}

    def iapp_create(self, partition, name, svcConfig, poolConfig):
        """Create an iApp Application Service.

        Args:
            partition: Partition name
            name: Application Service name
            config: BIG-IP config dict
        """
        logger.debug("Creating iApp %s from template %s",
                     name, svcConfig['iapp']['template'])
        a = self.sys.application.services.service

        iapp_def = self.iapp_build_definition(svcConfig, poolConfig)

        a.create(
            name=name,
            template=svcConfig['iapp']['template'],
            partition=partition,
            variables=iapp_def['variables'],
            tables=iapp_def['tables'],
            **svcConfig['iapp']['options']
        )

    def iapp_delete(self, partition, name):
        """Delete an iApp Application Service.

        Args:
            partition: Partition name
            name: Application Service name
        """
        logger.debug("Deleting iApp %s", name)
        a = self.get_iapp(partition, name)
        a.delete()

    def iapp_update(self, partition, name, svcConfig, poolConfig):
        """Update an iApp Application Service.

        Args:
            partition: Partition name
            name: Application Service name
            config: BIG-IP config dict
        """
        a = self.get_iapp(partition, name)

        iapp_def = self.iapp_build_definition(svcConfig, poolConfig)

        # Remove encrypted key and its value from SDK variables
        for v in a.__dict__['variables']:
            v.pop('encrypted', None)

        no_variable_change = all(v in a.__dict__['variables'] for v in
                                 iapp_def['variables'])
        no_table_change = all(t in a.__dict__['tables'] for t in
                              iapp_def['tables'])
        no_option_change = True
        for k, v in a.__dict__.iteritems():
            if k in svcConfig['iapp']['options']:
                if svcConfig['iapp']['options'][k] != v:
                    # FIXME (rtalley): description is overwritten in appsvcs
                    # integration iApps this is a workaround until F5Networks/
                    # f5-application-services-integration-iApp #43 is resolved
                    if (k != 'description' and 'appsvcs_integration' in
                            svcConfig['iapp']['template']):
                        no_option_change = False

        if no_variable_change and no_table_change and no_option_change:
            return

        a.update(
            executeAction='definition',
            name=name,
            partition=partition,
            variables=iapp_def['variables'],
            tables=iapp_def['tables'],
            **svcConfig['iapp']['options']
        )

    def get_iapp(self, partition, name):
        """Get an iApp Application Service object.

        Args:
            partition: Partition name
            name: Application Service name
        """
        a = self.sys.application.services.service.load(
            name=urllib.quote(name),
            partition=partition
        )
        return a

    def get_iapp_list(self, partition):
        """Get a list of iApp Application Service names.

        Args:
            partition: Partition name
        """
        iapp_list = []
        iapps = self.sys.application.services.get_collection()
        for iapp in iapps:
            if iapp.partition == partition:
                iapp_list.append(iapp.name)

        return iapp_list


class Policy(Resource):
    """"""
    # The property names class attribute defines the names of the
    # properties that we wish to compare.
    properties = dict(
        name=None,
        partition=None,
        controls=None,
        strategy=None,
        legacy=True,
        requires=None,
        rules=None
    )

    def __init__(self, data):
        """Create the policy and nested class objects"""
        if isinstance(data, f5.bigip.tm.ltm.policy.Policy):
            data = self._flatten_policy(data)
        super(Policy, self).__init__(data['name'], data['partition'])
        for key, value in self.properties.items():
            if key == 'rules':
                self._data[key] = self._create_rules(
                    data['partition'], data[key])
                continue
            if key == 'name' or key == 'partition':
                continue
            self._data[key] = data.get(key, value)

    def __eq__(self, other):
        """Check the equality of the two objects.

        Only compare the properties as defined in the
        properties class dictionany.
        """
        if not isinstance(other, Policy):
            return False

        for key in self.properties:
            if key == 'rules':
                if len(self._data[key]) != len(other.data[key]):
                    logger.debug('Rule length is unequal')
                    return False
                for index, rule in enumerate(self._data[key]):
                    if rule != other.data[key][index]:
                        return False
                continue
            if self._data[key] != other.data.get(key, None):
                logger.debug(
                    'Policies are unequal, %s does not match: %s - %s',
                    key, self._data[key], other.data.get(key, None))
                return False
        return True

    def __str__(self):
        return str(self._data)

    def _create_rules(self, partition, rules):
        new_rules = []
        for rule in rules:
            new_rules.append(Rule(partition, rule))
        new_rules.sort(key=lambda x: x.data['ordinal'])
        return new_rules

    def _uri_path(self, bigip):
        return bigip.tm.ltm.policy

    def _flatten_policy(self, bigip_policy):
        policy = {}
        for key in Policy.properties:
            if key == 'rules':
                policy['rules'] = self._flatten_rules(
                    bigip_policy.__dict__['rulesReference']['items'])
            elif key == 'legacy':
                policy['legacy'] = True
            else:
                policy[key] = bigip_policy.__dict__.get(key)
        return policy

    def _flatten_rules(self, rules_list):
        rules = []
        for rule in rules_list:
            flat_rule = {}
            for key in Rule.properties:
                if key == 'actions':
                    flat_rule[key] = self._flatten_actions(rule)
                elif key == 'conditions':
                    flat_rule[key] = self._flatten_condition(rule)
                else:
                    flat_rule[key] = rule.get(key)
            rules.append(flat_rule)
        return rules

    def _flatten_actions(self, rule):
        actions = []
        for action in rule['actionsReference']['items']:
            flat_action = {}
            for key in Action.properties:
                flat_action[key] = action.get(key)
            actions.append(flat_action)
        return actions

    def _flatten_condition(self, rule):
        conditions = []
        if 'conditionsReference' not in rule:
            return conditions
        for condition in rule['conditionsReference']['items']:
            flat_condition = {}
            for key in Condition.properties:
                flat_condition[key] = condition.get(key)
            conditions.append(flat_condition)
        return conditions


class Rule(Resource):
    """"""
    # The property names class attribute defines the names of the
    # properties that we wish to compare.
    properties = dict(
        name=None,
        ordinal=None,
        actions=None,
        conditions=None
    )

    def __init__(self, partition, data):
        super(Rule, self).__init__(data['name'], partition)
        for key in self.properties:
            if key == 'actions':
                self._data[key] = self._create_actions(
                    partition, data[key])
                continue
            if key == 'conditions':
                conditions = data.get(key, [])
                self._data[key] = self._create_conditions(
                    partition, conditions)
                continue
            if key == 'name':
                continue
            self._data[key] = data.get(key)

    def __eq__(self, other):
        """Check the equality of the two objects.

        Only compare the properties as defined in the
        properties class dictionany.
        """
        if not isinstance(other, Rule):
            return False

        for key in self.properties:
            if key == 'actions' or key == 'conditions':
                if len(self._data[key]) != len(other.data[key]):
                    logger.debug('%s length is unequal', key)
                    return False
                for index, obj in enumerate(self._data[key]):
                    if obj != other.data[key][index]:
                        return False
                continue
            if self._data[key] != other.data.get(key, None):
                logger.debug(
                    'Rules are unequal, %s does not match: %s - %s',
                    key, self._data[key], other.data.get(key, None))
                return False
        return True

    def __str__(self):
        return str(self._data)

    def _create_actions(self, partition, actions):
        new_actions = []
        for action in actions:
            new_actions.append(Action(partition, action))
        return new_actions

    def _create_conditions(self, partition, conditions):
        new_conditions = []
        for condition in conditions:
            new_conditions.append(Condition(partition, condition))
        return new_conditions


class Action(Resource):
    """"""
    # The property names class attribute defines the names of the
    # properties that we wish to compare.
    properties = dict(
        name=None,
        pool=None,
        forward=None,
        request=None
    )

    def __init__(self, partition, data):
        super(Action, self).__init__(data['name'], partition)
        for key in self.properties:
            self._data[key] = data.get(key)

    def __eq__(self, other):
        """Check the equality of the two objects.

        Only compare the properties as defined in the
        properties class dictionany.
        """
        if not isinstance(other, Action):
            return False

        for key in self.properties:
            if self._data[key] != other.data.get(key, None):
                logger.debug(
                    'Actions are unequal, %s does not match: %s - %s',
                    key, self._data[key], other.data.get(key, None))
                return False
        return True

    def __str__(self):
        return str(self._data)


class Condition(Resource):
    """"""
    # The property names class attribute defines the names of the
    # properties that we wish to compare.
    properties = dict(
        name=None,
        index=None,
        request=None,
        equals=None,
        httpHost=False,
        host=False,
        httpUri=False,
        pathSegment=False,
        values=None
    )

    def __init__(self, partition, data):
        super(Condition, self).__init__(data['name'], partition)
        for key in self.properties:
            self._data[key] = data.get(key)

    def __eq__(self, other):
        """Check the equality of the two objects.

        Only compare the properties as defined in the
        properties class dictionany.
        """
        if not isinstance(other, Condition):
            return False

        for key in self.properties:
            if self._data[key] != other.data.get(key, None):
                logger.debug(
                    'Conditions are unequal, %s does not match: %s - %s',
                    key, self._data[key], other.data.get(key, None))
                return False
        return True

    def __str__(self):
        return str(self._data)
