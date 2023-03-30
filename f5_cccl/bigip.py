"""This module provides a class for managing a BIG-IP."""
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

from copy import copy
import logging
from time import time

import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning

from f5.sdk_exception import F5SDKError

import f5_cccl.exceptions as cccl_exc

# LTM resources
from f5_cccl.resource.ltm.app_service import IcrApplicationService
from f5_cccl.resource.ltm.monitor.http_monitor import IcrHTTPMonitor
from f5_cccl.resource.ltm.monitor.https_monitor import IcrHTTPSMonitor
from f5_cccl.resource.ltm.monitor.icmp_monitor import IcrICMPMonitor
from f5_cccl.resource.ltm.monitor.tcp_monitor import IcrTCPMonitor
from f5_cccl.resource.ltm.monitor.udp_monitor import IcrUDPMonitor
from f5_cccl.resource.ltm.policy import IcrPolicy
from f5_cccl.resource.ltm.pool import IcrPool
from f5_cccl.resource.ltm.virtual_address import IcrVirtualAddress
from f5_cccl.resource.ltm.virtual import IcrVirtualServer
from f5_cccl.resource.ltm.node import IcrNode
from f5_cccl.resource.ltm.irule import IcrIRule
from f5_cccl.resource.ltm.internal_data_group import IcrInternalDataGroup

# NET resources
from f5_cccl.resource.net.arp import IcrArp
from f5_cccl.resource.net.fdb.tunnel import IcrFDBTunnel
from f5_cccl.resource.net.route import IcrRoute

requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

LOGGER = logging.getLogger(__name__)


class BigIPProxy(object):
    """BigIPProxy class.

    Manages the resources for the partition(s) of the specified BIG-IP

    - Token-based authentication is used by specifying a token named 'tmos'.
      This will allow non-admin users to use the API (BIG-IP must configure
      the accounts with proper permissions, for either local or remote auth).

    Args:
        bigip: Management Root of the BIG-IP
        partitions: List of BIG-IP partitions to manage
        prefix: Optional string to prepend to resource names
    """

    def __init__(self, bigip, partition, prefix=None):
        """Initialize the BigIPProxy object."""
        LOGGER.debug("BigIPProxy.__init__()")

        self._bigip = bigip
        self._partition = partition

        self._prefix = ""
        if prefix:
            self._prefix = prefix

        # BIG-IP LTM resources
        self._virtuals = dict()
        self._pools = dict()
        self._all_pools = dict()
        self._policies = dict()
        self._iapps = dict()
        self._monitors = dict()
        self._nodes = dict()
        self._irules = dict()
        self._internal_data_groups = dict()

        # BIG-IP NET resources
        self._arps = dict()
        self._fdb_tunnels = dict()
        self._routes = dict()

    def mgmt_root(self):
        """Return a reference to the proxied BIG-IP."""
        return self._bigip

    def _manageable_resource(self, rsc):
        """Determine if the resource will be managed.

        Resource will be managed if it matches prefix and does not belong
        to an appService (iApp)

        Args:
            rsc: A BIG-IP resource
        """
        return rsc.name.startswith(self._prefix) and \
            getattr(rsc, 'appService', None) is None

    def get_virtual_address_references(self):
        """The list of virtual addresses to remove from existing config."""
        unreferenced = copy(self._virtual_addresses)
        all_virtuals = self._all_virtuals
        referenced = dict()

        # For each virtual in managed partition:
        for virtual in all_virtuals:
            # Get the name of virtual address from virtual destination.
            vaddr_name = all_virtuals[virtual].destination[2]

            # This virtual server references the virtual address.
            # Remove it from the list of unreferenced virtual addresses.
            # If the virtual name is not found, it is a no-op.
            vaddr = unreferenced.pop(vaddr_name, None)
            if vaddr:
                # This virtual refers to the virtual address.  Add it to
                # the map of referenced virtual addresses.
                referenced[vaddr_name] = vaddr

        return (referenced, unreferenced)

    def refresh_ltm(self):
        """Refresh the internal ltm cache with the BIG-IP state."""
        LOGGER.debug("Refreshing the BIG-IP ltm cached state...")
        try:
            self._refresh_ltm()
        except F5SDKError as error:
            LOGGER.error("F5 SDK Error: %s", error)
            raise cccl_exc.F5CcclCacheRefreshError(
                "BigIPProxy: failed to refresh internal BIG-IP ltm state.")

    def refresh_net(self):
        """Refresh the internal net cache with the BIG-IP state."""
        LOGGER.debug("Refreshing the BIG-IP net cached state...")
        try:
            self._refresh_net()
        except F5SDKError as error:
            LOGGER.error("F5 SDK Error: %s", error)
            raise cccl_exc.F5CcclCacheRefreshError(
                "BigIPProxy: failed to refresh internal BIG-IP net state.")

    def _create_resource(self, resource_type, resource_obj,
                         default_route_domain=None):
        """Create an iControl REST resource and handle exceptions on init.

        If some error occurs during the creation of a resource object,
        this wrapper will handle the known exceptions that might occur.

        We should never get a resource that does not have a name and
        partition, so creating a bare resource will allow us to try
        updates and to perform deletions.
        """
        icr_resource = None
        try:
            if default_route_domain is not None:
                icr_resource = resource_type(
                    default_route_domain=default_route_domain,
                    **resource_obj.raw)
            else:
                icr_resource = resource_type(**resource_obj.raw)

        except (ValueError, TypeError) as error:
            LOGGER.error(
                "Failed to create iControl REST resource %s, %s: error(%s)",
                resource_obj.name, resource_type.__name__, str(error))

            # An error occurred because the constructor did not like the
            # input.  Use resource name and partition to allow for its
            # management.  If we get a response from the big-ip, where
            # the object name and partition is not defined, then
            # add None.
            icr_resource = resource_type(resource_obj.name,
                                         resource_obj.partition)

        return icr_resource

    def _policy_status_check(self, policy, virtuals):
        """Delete non-legacy policies because they can't be updated."""
        if getattr(policy, 'status', 'legacy') != 'legacy':
            for v in virtuals:
                # First, remove non-legacy policies from virtuals
                policies = []
                policy_delete = False
                for p in v.policiesReference.get('items', []):
                    if p['name'] == policy.name:
                        policy_delete = True
                    else:
                        policies.append(p)

                if policy_delete:
                    v.policiesReference['items'] = policies
                    v.update()

            # delete policy
            LOGGER.warning("Deleting policy /%s/%s due to invalid status: %s",
                           policy.partition, policy.name, policy.status)
            policy.delete()
            return False

        return True

    def _refresh_ltm(self):  # pylint: disable=too-many-locals
        """Refresh the internal ltm cache with the BIG-IP state."""
        start_time = time()

        partition_filter = "$filter=partition+eq+{}".format(self._partition)

        #  Retrieve the list of virtual servers in managed partition.
        query = partition_filter

        #  Determine the current route domain default for the partition
        default_route_domain = self.get_default_route_domain()

        #  Retrieve the lists of health monitors
        LOGGER.debug("Retrieving http_monitors from BIG-IP /%s...",
                     self._partition)
        http_monitors = self._bigip.tm.ltm.monitor.https.get_collection(
            requests_params={"params": query})
        LOGGER.debug("Retrieving https_monitors from BIG-IP /%s...",
                     self._partition)
        https_monitors = self._bigip.tm.ltm.monitor.https_s.get_collection(
            requests_params={"params": query})
        LOGGER.debug("Retrieving tcp_monitors from BIG-IP /%s...",
                     self._partition)
        tcp_monitors = self._bigip.tm.ltm.monitor.tcps.get_collection(
            requests_params={"params": query})
        LOGGER.debug("Retrieving udp_monitors from BIG-IP /%s...",
                     self._partition)
        udp_monitors = self._bigip.tm.ltm.monitor.udps.get_collection(
            requests_params={"params": query})
        LOGGER.debug("Retrieving gateway icmp_monitors from BIG-IP /%s...",
                     self._partition)
        icmp_monitors = (
            self._bigip.tm.ltm.monitor.gateway_icmps.get_collection(
                requests_params={"params": query})
        )
        LOGGER.debug("Retrieving iApps from BIG-IP /%s...",
                     self._partition)
        iapps = self._bigip.tm.sys.application.services.get_collection(
            requests_params={"params": query})
        LOGGER.debug("Retrieving nodes from BIG-IP /%s...",
                     self._partition)
        nodes = self._bigip.tm.ltm.nodes.get_collection(
            requests_params={"params": query})
        LOGGER.debug("Retrieving virtual addresses from BIG-IP /%s...",
                     self._partition)
        virtual_addresses = \
            self._bigip.tm.ltm.virtual_address_s.get_collection(
                requests_params={"params": query})

        LOGGER.debug("Retrieving LTM iRules from BIG-IP /%s...",
                     self._partition)
        irules = self._bigip.tm.ltm.rules.get_collection(
            requests_params={"params": query})

        LOGGER.debug("Retrieving LTM Internal data-groups from BIG-IP /%s...",
                     self._partition)
        int_dgs = self._bigip.tm.ltm.data_group.internals.get_collection(
            requests_params={"params": query})

        #  Retrieve the list of virtuals, pools, and policies in the
        #  managed partition getting all subCollections.
        query = "{}&expandSubcollections=true".format(partition_filter)

        LOGGER.debug("Retrieving virtual servers from BIG-IP /%s...",
                     self._partition)
        virtuals = self._bigip.tm.ltm.virtuals.get_collection(
            requests_params={"params": query})

        LOGGER.debug("Retrieving pools from BIG-IP /%s...",
                     self._partition)
        pools = self._bigip.tm.ltm.pools.get_collection(
            requests_params={"params": query})

        LOGGER.debug("Retrieving LTM policies from BIG-IP /%s...",
                     self._partition)
        all_policies = self._bigip.tm.ltm.policys.get_collection(
            requests_params={"params": query})

        #  Delete non-legacy policies
        policies = [
            p for p in all_policies
            if self._manageable_resource(p)
            and self._policy_status_check(p, virtuals)
        ]

        #  Refresh the virtuals cache.
        self._virtuals = {
            v.name: self._create_resource(IcrVirtualServer, v,
                                          default_route_domain)
            for v in virtuals if self._manageable_resource(v)
        }

        #  Refresh the virtuals cache.
        self._all_virtuals = {
            v.name: self._create_resource(IcrVirtualServer, v,
                                          default_route_domain)
            for v in virtuals
        }

        #  Refresh the virtual address cache.
        self._virtual_addresses = {
            v.name: self._create_resource(IcrVirtualAddress, v,
                                          default_route_domain)
            for v in virtual_addresses if self._manageable_resource(v)
        }

        #  Refresh the pool cache
        self._pools = {
            p.name: self._create_resource(IcrPool, p)
            for p in pools if self._manageable_resource(p)
        }

        #  Refresh the all-pool cache
        self._all_pools = {
            p.name: self._create_resource(IcrPool, p)
            for p in pools
        }

        #  Refresh the iRule cache
        self._irules = {
            p.name: self._create_resource(IcrIRule, p)
            for p in irules if self._manageable_resource(p)
        }

        #  Refresh the data_group cache
        self._internal_data_groups = {
            p.name: self._create_resource(IcrInternalDataGroup, p)
            for p in int_dgs if self._manageable_resource(p)
        }

        #  Refresh the policy cache
        self._policies = {
            p.name: self._create_resource(IcrPolicy, p)
            for p in policies if self._manageable_resource(p)
        }

        #  Refresh the iapp cache
        self._iapps = {
            i.name: self._create_resource(IcrApplicationService, i)
            for i in iapps if i.name.startswith(self._prefix)
        }

        #  Refresh the node cache
        self._nodes = {
            n.name: self._create_resource(IcrNode, n, default_route_domain)
            for n in nodes
        }

        #  Refresh the health monitor cache
        self._monitors['http'] = {
            m.name: self._create_resource(IcrHTTPMonitor, m)
            for m in http_monitors if self._manageable_resource(m)
        }
        self._monitors['https'] = {
            m.name: self._create_resource(IcrHTTPSMonitor, m)
            for m in https_monitors if self._manageable_resource(m)
        }
        self._monitors['tcp'] = {
            m.name: self._create_resource(IcrTCPMonitor, m)
            for m in tcp_monitors if self._manageable_resource(m)
        }
        self._monitors['icmp'] = {
            m.name: self._create_resource(IcrICMPMonitor, m)
            for m in icmp_monitors if self._manageable_resource(m)
        }
        self._monitors['udp'] = {
            m.name: self._create_resource(IcrUDPMonitor, m)
            for m in udp_monitors if self._manageable_resource(m)
        }

        LOGGER.debug(
            "BIG-IP ltm refresh took %.5f seconds.", (time() - start_time))

    def _refresh_net(self):
        """Refresh the internal net cache with the BIG-IP state."""
        start_time = time()
        query = "$filter=partition+eq+{}".format(self._partition)

        #  Determine the current route domain default for the partition
        default_route_domain = self.get_default_route_domain()

        # Retrieve the list of arps
        LOGGER.debug("Retrieving arps from BIG-IP /%s...", self._partition)
        arps = self._bigip.tm.net.arps.get_collection(
            requests_params={"params": query})

        #Retrieve list of routes
        LOGGER.debug("Retrieving routes from BIG-IP /%s...", self._partition)
        routes = self._bigip.tm.net.routes.get_collection(
            requests_params={"params": query})
        # Retrieve the list of tunnels
        # WORKAROUND: We don't pass the request_params in the fdb tunnel case,
        # due to an issue with the f5-sdk expecting an object param, rather
        # than the usual string param used as the query above. For now, we get
        # all tunnels and then filter by partition when we create
        # our local list.
        LOGGER.debug(
            "Retrieving fdb tunnels from BIG-IP /%s...", self._partition)
        tunnels = self._bigip.tm.net.fdb.tunnels.get_collection()

        # Refresh the arp cache
        self._arps = {
            a.name: self._create_resource(IcrArp, a)
            for a in arps if self._manageable_resource(a)
        }

        # Refresh the route cache
        self._routes = {
            a.name: self._create_resource(IcrRoute, a)
            for a in routes if self._manageable_resource(a)
        }

        for tunnel in tunnels:
            tunnel.records = []
            for record in tunnel.records_s.get_collection():
                tunnel.records.append({'name': record.name, 'endpoint': record.endpoint})

        # Refresh the tunnel cache
        self._fdb_tunnels = {
            t.name: self._create_resource(IcrFDBTunnel, t,
                                          default_route_domain)
            for t in tunnels if (self._manageable_resource(t) and
                                 t.partition == self._partition)
        }
        self._all_fdb_tunnels = {
            t.name: self._create_resource(IcrFDBTunnel, t,
                                          default_route_domain)
            for t in tunnels if t.partition == self._partition
        }

        LOGGER.debug(
            "BIG-IP net refresh took %.5f seconds.", (time() - start_time))

    def get_default_route_domain(self):
        """Return the configured default route domain for the partition"""
        partition = self._bigip.tm.auth.partitions.partition.load(
            name=self._partition)
        # Note: This information is needed when processing the request config
        #       which occurs before self.refresh() is called
        return partition.defaultRouteDomain

    def get_virtuals(self, all_virtuals=False):
        """Return the index of virtual servers."""
        if all_virtuals:
            return self._all_virtuals

        return self._virtuals

    def get_pools(self, all_pools=False):
        """Return the index of pools."""
        if all_pools:
            return self._all_pools

        return self._pools

    def get_app_svcs(self):
        """Return the index of app services."""
        return self._iapps

    def get_monitors(self, hm_type=None):
        """Get all monitors or those of type, hm_type."""
        if hm_type:
            monitors = self._monitors.get(hm_type, dict())
        else:
            monitors = self._monitors

        return monitors

    def get_http_monitors(self):
        """Return the index of HTTP monitors."""
        return self.get_monitors('http')

    def get_tcp_monitors(self):
        """Return the index of TCP monitors."""
        return self.get_monitors('tcp')

    def get_udp_monitors(self):
        """Return the index of UDP monitors."""
        return self.get_monitors('udp')

    def get_https_monitors(self):
        """Return the index of HTTPS monitors."""
        return self.get_monitors('https')

    def get_icmp_monitors(self):
        """Return the index of gateway ICMP monitors."""
        return self.get_monitors('icmp')

    def get_l7policies(self):
        """Return the index of L7 policies."""
        return self._policies

    def get_iapps(self):
        """Return the index of iApps."""
        return self._iapps

    def get_nodes(self):
        """Return the index of nodes."""
        return self._nodes

    def get_virtual_addresses(self):
        """Return the index of virtual_addresses."""
        return self._virtual_addresses

    def get_irules(self):
        """Return the index of iRules."""
        return self._irules

    def get_internal_data_groups(self):
        """Return the index of internal data_groups."""
        return self._internal_data_groups

    def get_arps(self):
        """Return the index of arps."""
        return self._arps

    def get_fdb_tunnels(self, all_tunnels=False):
        """Return the index of tunnels."""
        if all_tunnels:
            return self._all_fdb_tunnels

        return self._fdb_tunnels

    def get_routes(self):
        """Return the index of arps."""
        return self._routes