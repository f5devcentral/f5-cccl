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
import json
from operator import attrgetter
import os
import time
import urllib

import ipaddress
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from common import resolve_ip, list_diff, list_diff_exclusive, list_intersect,\
                   ipv4_to_mac, extract_partition_and_name,\
                   PartitionNameError, IPV4FormatError

import f5
from f5.bigip import BigIP
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
        cloud: cloud environment (marathon or kubernetes)
        hostname: IP address of BIG-IP
        port: Port of BIG-IP
        username: BIG-IP username
        password: BIG-IP password
        partitions: List of BIG-IP partitions to manage
        token: The optional auth token to use with BIG-IP (e.g. "tmos")
    """

    def __init__(self, cloud, hostname, port, username, password, partitions,
                 token=None):
        """Initialize the CloudBigIP object."""
        super_kwargs = {"port": port}
        if token:
            super_kwargs["token"] = token
        super(CloudBigIP, self).__init__(hostname, username, password,
                                         **super_kwargs)
        self._cloud = cloud
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
        try:
            ipaddress.ip_address(app.bindAddr)
        except ValueError:
            logger.error(msg.format('F5_BIND_ADDR', app.appId, app.bindAddr))
            is_valid = False

        # Validate LB method
        if app.balance not in self._lbmethods:
            logger.error(msg.format('F5_BALANCE', app.appId, app.balance))
            is_valid = False

        return is_valid

    def regenerate_config_f5(self, cloud_state):
        """Configure the BIG-IP based on the cloud state.

        Args:
            cloud_state: Marathon or Kubernetes state
        """
        try:
            if self._cloud == 'marathon':
                cfg = self._create_config_marathon(cloud_state)
            else:
                cfg = self._create_config_kubernetes(cloud_state)
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

        if os.environ.get('SCALE_PERF_ENABLE'):  # pragma: no cover
            test_data = {}
            app_count = 0
            backend_count = 0
            if self._cloud == 'marathon':
                for app in cloud_state:
                    if app.partition == 'test':
                        app_count += 1
                        backends = len(app.backends)
                        test_data[app.appId[1:]] = backends
                        backend_count += backends
            elif self._cloud == 'kubernetes':
                for service in cloud_state['services']:
                    app_count += 1
                    vs_backend = service['virtualServer']['backend']
                    backends = len(vs_backend['poolMemberAddrs'])
                    test_data[vs_backend['serviceName']] = backends
                    backend_count += backends

            test_data['Total_Services'] = app_count
            test_data['Total_Backends'] = backend_count
            test_data['Time'] = time.time()
            json_data = json.dumps(test_data)
            logger.info('SCALE_PERF: Test data: %s', json_data)
        return False

    def _create_config_kubernetes(self, config):
        """Create a BIG-IP configuration from the Kubernetes configuration.

        Args:
            config: Kubernetes BigIP config
        """
        logger.debug("Generating config for BIG-IP from Kubernetes state")
        f5 = {'ltm': {}, 'network': {}}
        if 'openshift-sdn' in config:
            f5['network'] = self._create_network_config_kubernetes(config)
        if 'services' in config:
            f5['ltm'] = self._create_ltm_config_kubernetes(config)

        return f5

    def _create_network_config_kubernetes(self, config):
        """Create a BIG-IP Network configuration from the Kubernetes config.

        Args:
            config: Kubernetes BigIP config which contains openshift-sdn defs
        """
        f5_network = {}
        if 'openshift-sdn' in config:
            openshift_sdn = config['openshift-sdn']
            f5_network['fdb'] = openshift_sdn
        return f5_network

    def _create_ltm_config_kubernetes(self, config):
        """Create a BIG-IP LTM configuration from the Kubernetes configuration.

        Args:
            config: Kubernetes BigIP config which contains a svc list
        """
        f5_services = {}

        # partitions this script is responsible for:
        partitions = frozenset(self._partitions)

        svcs = config['services']
        for svc in svcs:
            f5_service = {}

            backend = svc['virtualServer']['backend']
            frontend = svc['virtualServer']['frontend']
            health_monitors = backend.get('healthMonitors', [])

            # Only handle application if it's partition is one that this script
            # is responsible for
            if not has_partition(partitions, frontend['partition']):
                continue

            # No address for this port
            if (('virtualAddress' not in frontend or
                 'bindAddr' not in frontend['virtualAddress']) and
                    'iapp' not in frontend):
                continue

            frontend_name = frontend['virtualServerName']

            f5_service['name'] = frontend_name

            f5_service['partition'] = frontend['partition']

            if 'iapp' in frontend:
                f5_service['iapp'] = {'template': frontend['iapp'],
                                      'poolMemberTable':
                                      frontend['iappPoolMemberTable'],
                                      'variables': frontend['iappVariables'],
                                      'options': frontend['iappOptions']}
                f5_service['iapp']['tables'] = frontend.get('iappTables', {})
            else:
                f5_service['virtual'] = {}
                f5_service['pool'] = {}
                f5_service['health'] = []

                # Parse the SSL profile into partition and name
                profiles = []
                if 'sslProfile' in frontend:
                    profile = (
                        frontend['sslProfile']['f5ProfileName'].split('/'))
                    if len(profile) != 2:
                        logger.error("Could not parse partition and name from "
                                     "SSL profile: %s",
                                     frontend['sslProfile']['f5ProfileName'])
                    else:
                        profiles.append({'partition': profile[0],
                                         'name': profile[1]})

                # Add appropriate profiles
                if str(frontend['mode']).lower() == 'http':
                    profiles.append({'partition': 'Common', 'name': 'http'})
                elif get_protocol(frontend['mode']) == 'tcp':
                    profiles.append({'partition': 'Common', 'name': 'tcp'})

                f5_service['virtual_address'] = frontend['virtualAddress'][
                    'bindAddr']

                f5_service['virtual'].update({
                    'enabled': True,
                    'disabled': False,
                    'ipProtocol': get_protocol(frontend['mode']),
                    'destination':
                    "/%s/%s:%d" % (frontend['partition'],
                                   frontend['virtualAddress']['bindAddr'],
                                   frontend['virtualAddress']['port']),
                    'pool': "/%s/%s" % (frontend['partition'], frontend_name),
                    'sourceAddressTranslation': {'type': 'automap'},
                    'profiles': profiles
                })

                monitors = None
                # Health Monitors
                for index, health in enumerate(health_monitors):
                    logger.debug("Healthcheck for service %s: %s",
                                 backend['serviceName'], health)
                    if index == 0:
                        health['name'] = frontend_name
                    else:
                        health['name'] = frontend_name + '_' + str(index)
                        monitors = monitors + ' and '
                    f5_service['health'].append(health)

                    # monitors is a string of health-monitor names
                    # delimited by ' and '
                    monitor = "/%s/%s" % (frontend['partition'],
                                          f5_service['health'][index]['name'])

                    monitors = (monitors + monitor) if monitors is not None \
                        else monitor

                f5_service['pool'].update({
                    'monitor': monitors,
                    'loadBalancingMode': frontend['balance']
                })

            f5_service['nodes'] = {}
            if backend['poolMemberAddrs']:
                for node in backend['poolMemberAddrs']:
                    f5_service['nodes'].update({node: {
                        'state': 'user-up',
                        'session': 'user-enabled'
                    }})
            else:
                logger.warning(
                    'Virtual server "{}" has service "{}", which is empty - '
                    'configuring 0 pool members.'.format(
                        frontend_name, backend['serviceName']))

            f5_services.update({frontend_name: f5_service})

        return f5_services

    def _create_config_marathon(self, apps):
        """Create a BIG-IP configuration from the Marathon app list.

        Args:
            apps: Marathon app list
        """
        logger.debug(apps)
        for app in apps:
            logger.debug(app.__hash__())

        logger.info("Generating config for BIG-IP")
        f5 = {'ltm': {}}
        # partitions this script is responsible for:
        partitions = frozenset(self._partitions)

        for app in sorted(apps, key=attrgetter('appId', 'servicePort')):
            f5_service = {
                'virtual': {},
                'pool': {},
                'nodes': {},
                'health': [],
                'partition': '',
                'name': ''
            }
            # Only handle application if it's partition is one that this script
            # is responsible for
            if not has_partition(partitions, app.partition):
                continue

            # No address or iApp for this port
            if not app.bindAddr and not app.iapp:
                continue

            # Validate data from the app's labels
            if not app.iapp and not self.is_label_data_valid(app):
                continue

            f5_service['partition'] = app.partition

            if app.iapp:
                # Translate from the internal properties we set on app to the
                # naming expected by the common f5_service['iapp']
                # Only set properties that are actually present.
                #
                # tableName would be better as poolMemberTableName but it is
                # required to be tableName to match the tableName produced by
                # the k8s-bigip-ctlr
                f5_service['iapp'] = {}
                for k, v in {'template': 'iapp',
                             'tableName': 'iappPoolMemberTableName',
                             'poolMemberTable': 'iappPoolMemberTable',
                             'tables': 'iappTables',
                             'variables': 'iappVariables',
                             'options': 'iappOptions'}.iteritems():
                    if hasattr(app, v):
                        f5_service['iapp'][k] = getattr(app, v)

                # Decode the tables
                for key in app.iappTables:
                    f5_service['iapp']['tables'][key] = \
                        json.loads(app.iappTables[key])

            logger.info("Configuring app %s, partition %s", app.appId,
                        app.partition)
            backend = app.appId[1:].replace('/', '_') + '_' + \
                str(app.servicePort)

            frontend = 'iapp' if app.iapp else app.bindAddr
            frontend_name = "%s_%s_%d" % ((app.appId).lstrip('/'), frontend,
                                          app.servicePort)
            # The Marathon appId contains the full path, replace all '/' in
            # the name with '_'
            frontend_name = frontend_name.replace('/', '_')
            f5_service['name'] = frontend_name
            if app.bindAddr:
                logger.debug("Frontend at %s:%d with backend %s", app.bindAddr,
                             app.servicePort, backend)

            if app.healthCheck:
                for hc in app.healthCheck:
                    logger.debug("Healthcheck for app '%s': %s", app.appId, hc)
                    hc['name'] = frontend_name

                    # normalize healtcheck protocol name to lowercase
                    if 'protocol' in hc:
                        hc['protocol'] = (hc['protocol']).lower()
                    hc.update({
                        'interval': hc['intervalSeconds'],
                        'timeout': healthcheck_timeout_calculate(hc),
                        'send': self.healthcheck_sendstring(hc),
                        })
                    f5_service['health'].append(hc)

            # Parse the SSL profile into partition and name
            profiles = []
            if app.profile:
                profile = app.profile.split('/')
                if len(profile) != 2:
                    logger.error("Could not parse partition and name from SSL"
                                 " profile: %s", app.profile)
                else:
                    profiles.append({'partition': profile[0],
                                     'name': profile[1]})

            # Add appropriate profiles
            if str(app.mode).lower() == 'http':
                profiles.append({'partition': 'Common', 'name': 'http'})
            elif get_protocol(app.mode) == 'tcp':
                profiles.append({'partition': 'Common', 'name': 'tcp'})

            f5_service['virtual_address'] = app.bindAddr

            f5_service['virtual'].update({
                'enabled': True,
                'disabled': False,
                'ipProtocol': get_protocol(app.mode),
                'destination':
                "/%s/%s:%d" % (app.partition, app.bindAddr, app.servicePort),
                'pool': "/%s/%s" % (app.partition, frontend_name),
                'sourceAddressTranslation': {'type': 'automap'},
                'profiles': profiles
            })
            f5_service['pool'].update({
                'monitor': "/%s/%s" %
                           (app.partition, f5_service['health'][0]['name'])
                           if app.healthCheck else None,
                'loadBalancingMode': app.balance
            })

            key_func = attrgetter('host', 'port')
            for backendServer in sorted(app.backends, key=key_func):
                logger.debug("Found backend server at %s:%d for app %s",
                             backendServer.host, backendServer.port, app.appId)

                # Resolve backendServer hostname to IP address
                ipv4 = resolve_ip(backendServer.host)

                if ipv4 is not None:
                    f5_node_name = ipv4 + ':' + str(backendServer.port)
                    f5_service['nodes'].update({f5_node_name: {
                        'state': 'user-up',
                        'session': 'user-enabled'
                    }})
                else:
                    logger.warning("Could not resolve ip for host %s, "
                                   "ignoring this backend", backendServer.host)

            f5['ltm'].update({frontend_name: f5_service})

        logger.debug("F5 json config: %s", json.dumps(f5))

        return f5

    def _apply_config(self, config):
        """Apply the configuration to the BIG-IP.

        Args:
            config: BIG-IP config dict
        """
        if 'ltm' in config:
            self._apply_ltm_config(config['ltm'])

        if 'network' in config:
            self._apply_network_config(config['network'])

    def _apply_ltm_config(self, config):
        """Apply the local traffic configuration to the BIG-IP.

        Args:
            config: BIG-IP LTM config dict
        """
        unique_partitions = self.get_partitions(self._partitions)

        for partition in unique_partitions:
            logger.debug("Doing config for partition '%s'", partition)

            cloud_virtual_list = \
                [x for x in config.keys()
                 if config[x]['partition'] == partition and
                 'iapp' not in config[x]]
            cloud_pool_list = \
                [x for x in config.keys()
                 if config[x]['partition'] == partition and
                 'iapp' not in config[x]]
            cloud_iapp_list = \
                [x for x in config.keys()
                 if config[x]['partition'] == partition and
                 'iapp' in config[x]]

            # Configure iApps
            f5_iapp_list = self.get_iapp_list(partition)
            log_sequence('f5_iapp_list', f5_iapp_list)
            log_sequence('cloud_iapp_list', cloud_iapp_list)

            # iapp delete
            iapp_delete = list_diff(f5_iapp_list, cloud_iapp_list)
            log_sequence('iApps to delete', iapp_delete)
            for iapp in iapp_delete:
                self.iapp_delete(partition, iapp)

            # iapp add
            iapp_add = list_diff(cloud_iapp_list, f5_iapp_list)
            log_sequence('iApps to add', iapp_add)
            for iapp in iapp_add:
                self.iapp_create(partition, iapp, config[iapp])

            # iapp update
            iapp_intersect = list_intersect(cloud_iapp_list, f5_iapp_list)
            log_sequence('iApps to update', iapp_intersect)
            for iapp in iapp_intersect:
                self.iapp_update(partition, iapp, config[iapp])

            # this is kinda kludgey: health monitor has the same name as the
            # virtual, and there is no more than 1 monitor per virtual.
            cloud_healthcheck_list = []
            for v in cloud_virtual_list:
                for hc in config[v]['health']:
                    if 'protocol' in hc:
                        cloud_healthcheck_list.append(v)

            f5_pool_list = self.get_pool_list(partition)
            f5_virtual_list = self.get_virtual_list(partition)

            # get_healthcheck_list() returns a dict with healthcheck names for
            # keys and a subkey of "type" with a value of "tcp", "http", etc.
            # We need to know the type to correctly reference the resource.
            # i.e. monitor types are different resources in the f5-sdk
            f5_healthcheck_dict = self.get_healthcheck_list(partition)
            logger.debug("f5_healthcheck_dict:   %s", f5_healthcheck_dict)
            # and then we need just the list to identify differences from the
            # list returned from the cloud environment
            f5_healthcheck_list = f5_healthcheck_dict.keys()

            # The virtual servers, pools, and health monitors for iApps are
            # managed by the iApps themselves, so remove them from the lists we
            # manage
            for iapp in cloud_iapp_list:
                f5_virtual_list = \
                    [x for x in f5_virtual_list if not x.startswith(iapp)]
                f5_pool_list = \
                    [x for x in f5_pool_list if not x.startswith(iapp)]
                f5_healthcheck_list = \
                    [x for x in f5_healthcheck_list if not x.startswith(iapp)]

            log_sequence('f5_pool_list', f5_pool_list)
            log_sequence('f5_virtual_list', f5_virtual_list)
            log_sequence('f5_healthcheck_list', f5_healthcheck_list)
            log_sequence('cloud_pool_list', cloud_pool_list)
            log_sequence('cloud_virtual_list', cloud_virtual_list)

            # virtual delete
            virt_delete = list_diff(f5_virtual_list, cloud_virtual_list)
            log_sequence('Virtual Servers to delete', virt_delete)
            for virt in virt_delete:
                self.virtual_delete(partition, virt)

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

            # healthcheck config needs to happen before pool config because
            # the pool is where we add the healthcheck
            # healthcheck add: use the name of the virt for the healthcheck
            healthcheck_add = list_diff(cloud_healthcheck_list,
                                        f5_healthcheck_list)
            log_sequence('Healthchecks to add', healthcheck_add)
            for hc in healthcheck_add:
                for item in config[hc]['health']:
                    self.healthcheck_create(partition, item)

            # pool add
            pool_add = list_diff(cloud_pool_list, f5_pool_list)
            log_sequence('Pools to add', pool_add)
            for pool in pool_add:
                self.pool_create(partition, pool, config[pool])

            # virtual add
            virt_add = list_diff(cloud_virtual_list, f5_virtual_list)
            log_sequence('Virtual Servers to add', virt_add)
            for virt in virt_add:
                self.virtual_create(partition, virt, config[virt])

            # healthcheck intersection
            healthcheck_intersect = list_intersect(cloud_virtual_list,
                                                   f5_healthcheck_list)
            log_sequence('Healthchecks to update', healthcheck_intersect)

            for hc in healthcheck_intersect:
                for item in config[hc]['health']:
                    self.healthcheck_update(partition, hc, item)

            # pool intersection
            pool_intersect = list_intersect(cloud_pool_list, f5_pool_list)
            log_sequence('Pools to update', pool_intersect)
            for pool in pool_intersect:
                self.pool_update(partition, pool, config[pool])

            # virt intersection
            virt_intersect = list_intersect(cloud_virtual_list,
                                            f5_virtual_list)
            log_sequence('Virtual Servers to update', virt_intersect)

            for virt in virt_intersect:
                self.virtual_update(partition, virt, config[virt])

            # add/update/remove pool members
            # need to iterate over pool_add and pool_intersect (note that
            # removing a pool also removes members, so don't have to
            # worry about those)
            for pool in list(set(pool_add + pool_intersect)):
                logger.debug("Pool: %s", pool)

                f5_member_list = self.get_pool_member_list(partition, pool)
                cloud_member_list = (config[pool]['nodes']).keys()

                member_delete_list = list_diff(f5_member_list,
                                               cloud_member_list)
                log_sequence('Pool members to delete', member_delete_list)
                for member in member_delete_list:
                    self.member_delete(partition, pool, member)

                member_add = list_diff(cloud_member_list, f5_member_list)
                log_sequence('Pool members to add', member_add)
                for member in member_add:
                    self.member_create(partition, pool, member,
                                       config[pool]['nodes'][member])

                # Since we're only specifying hostname and port for members,
                # 'member_update' will never actually get called. Changing
                # either of these properties will result in a new member being
                # created and the old one being deleted. I'm leaving this here
                # though in case we add other properties to members
                member_update_list = list_intersect(cloud_member_list,
                                                    f5_member_list)
                log_sequence('Pool members to update', member_update_list)

                for member in member_update_list:
                    self.member_update(partition, pool, member,
                                       config[pool]['nodes'][member])

            # Delete any unreferenced nodes
            self.cleanup_nodes(partition)

    def _apply_network_config(self, config):
        """Apply the network configuration to the BIG-IP.

        Args:
            config: BIG-IP network config dict
        """
        if 'fdb' in config:
            self._apply_network_fdb_config(config['fdb'])

    def _apply_network_fdb_config(self, fdb_config):
        """Apply the network fdb configuration to the BIG-IP.

        Args:
            config: BIG-IP network fdb config dict
        """
        req_vxlan_name = fdb_config['vxlan-name']
        req_fdb_record_endpoint_list = fdb_config['vxlan-node-ips']
        try:
            f5_fdb_record_endpoint_list = self.get_fdb_records(req_vxlan_name)

            log_sequence('req_fdb_record_list', req_fdb_record_endpoint_list)
            log_sequence('f5_fdb_record_list', f5_fdb_record_endpoint_list)

            # See if the list of records is different.
            # If so, update with new list.
            if list_diff_exclusive(f5_fdb_record_endpoint_list,
                                   req_fdb_record_endpoint_list):
                self.fdb_records_update(req_vxlan_name,
                                        req_fdb_record_endpoint_list)
        except (PartitionNameError, IPV4FormatError) as e:
            logger.error(e)
            return
        except Exception as e:
            logger.error('Failed to configure the FDB for VxLAN tunnel '
                         '{}: {}'.format(req_vxlan_name, e))

    def cleanup_nodes(self, partition):
        """Delete any unused nodes in a partition from the BIG-IP.

        Args:
            partition: Partition name
        """
        node_list = self.get_node_list(partition)
        pool_list = self.get_pool_list(partition)

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

    def get_pool_list(self, partition):
        """Get a list of pool names for a partition.

        Args:
            partition: Partition name
        """
        pool_list = []
        pools = self.ltm.pools.get_collection()
        for pool in pools:
            if pool.partition == partition:
                pool_list.append(pool.name)
        return pool_list

    def pool_create(self, partition, pool, data):
        """Create a pool.

        Args:
            partition: Partition name
            pool: Name of pool to create
            data: BIG-IP config dict
        """
        logger.debug("Creating pool %s", pool)
        p = self.ltm.pools.pool

        p.create(partition=partition, name=pool, **data['pool'])

    def pool_delete(self, partition, pool):
        """Delete a pool.

        Args:
            partition: Partition name
            pool: Name of pool to delete
        """
        logger.debug("deleting pool %s", pool)
        p = self.get_pool(partition, pool)
        p.delete()

    def pool_update(self, partition, pool, data):
        """Update a pool.

        Args:
            partition: Partition name
            pool: Name of pool to update
            data: BIG-IP config dict
        """
        data = data['pool']
        pool = self.get_pool(partition, pool)

        def genChange(p, d):
            """Update pool members config data."""
            for key, val in p.__dict__.iteritems():
                if key in d:
                    if None is not val:
                        yield d[key] == val.strip()
                    else:
                        yield d[key] == val

        no_change = all(genChange(pool, data))

        if no_change:
            return False

        pool.modify(**data)
        return True

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
            if virtual.partition == partition:
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

        no_change = all(data[key] == val for key, val in v.__dict__.iteritems()
                        if key in data)

        # Compare the actual and desired profiles
        profiles = self.get_virtual_profiles(v)
        no_profile_change = sorted(profiles) == sorted(data['profiles'])

        if no_change and no_profile_change:
            return False

        v.modify(**data)

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
            if hc.partition == partition:
                healthcheck_dict.update({hc.name: {'type': 'http'}})

        # TCP
        healthchecks = self.ltm.monitor.tcps.get_collection()
        for hc in healthchecks:
            if hc.partition == partition:
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

    def get_partitions(self, partitions):
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

    def iapp_build_definition(self, config):
        """Create a dict that defines the 'variables' and 'tables' for an iApp.

        Args:
            config: BIG-IP config dict
        """
        # Build variable list
        variables = []
        for key in config['iapp']['variables']:
            var = {'name': key, 'value': config['iapp']['variables'][key]}
            variables.append(var)

        # The schema says only one of poolMemberTable or tableName is
        # valid, so if the user set both it should have already been rejected.
        # But if not, prefer the new poolMemberTable over tableName.
        tables = []
        if 'poolMemberTable' in config['iapp']:
            tableConfig = config['iapp']['poolMemberTable']

            # Construct columnNames array from the 'name' prop of each column
            columnNames = []
            for col in tableConfig['columns']:
                columnNames.append(col['name'])

            # Construct rows array - one row for each node, interpret the
            # 'kind' or 'value' from the column spec.
            rows = []
            for node in config['nodes']:
                row = []
                (addr, port) = node.split(':')
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
        elif 'tableName' in config['iapp']:
            # Before adding the flexible poolMemberTable mode, we only
            # supported three fixed columns in order, and connection_limit was
            # hardcoded to 0 ("no limit")
            rows = []
            for node in config['nodes']:
                (addr, port) = node.split(':')
                rows.append({'row': [addr, port, '0']})
            tables.append({
                'name': config['iapp']['tableName'],
                'columnNames': ['addr', 'port', 'connection_limit'],
                'rows': rows
            })

        # Add other tables
        for key in config['iapp']['tables']:
            data = config['iapp']['tables'][key]
            table = {'columnNames': data['columns'],
                     'name': key,
                     'rows': []}
            for row in data['rows']:
                table['rows'].append({'row': row})
            tables.append(table)

        return {'variables': variables, 'tables': tables}

    def iapp_create(self, partition, name, config):
        """Create an iApp Application Service.

        Args:
            partition: Partition name
            name: Application Service name
            config: BIG-IP config dict
        """
        logger.debug("Creating iApp %s from template %s",
                     name, config['iapp']['template'])
        a = self.sys.application.services.service

        iapp_def = self.iapp_build_definition(config)

        a.create(
            name=name,
            template=config['iapp']['template'],
            partition=partition,
            variables=iapp_def['variables'],
            tables=iapp_def['tables'],
            **config['iapp']['options']
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

    def iapp_update(self, partition, name, config):
        """Update an iApp Application Service.

        Args:
            partition: Partition name
            name: Application Service name
            config: BIG-IP config dict
        """
        a = self.get_iapp(partition, name)

        iapp_def = self.iapp_build_definition(config)

        a.update(
            executeAction='definition',
            name=name,
            partition=partition,
            variables=iapp_def['variables'],
            tables=iapp_def['tables'],
            **config['iapp']['options']
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

    def get_vxlan_tunnel(self, vxlan_name):
        """Get a vxlan tunnel object.

        Args:
            vxlan_name: Name of the vxlan tunnel
        """
        partition, name = extract_partition_and_name(vxlan_name)
        vxlan_tunnel = self.net.fdb.tunnels.tunnel.load(
            partition=partition, name=urllib.quote(name))
        return vxlan_tunnel

    def get_fdb_records(self, vxlan_name):
        """Get a list of FDB records (just the endpoint list) for the vxlan.

        Args:
            vxlan_name: Name of the vxlan tunnel
        """
        endpoint_list = []
        vxlan_tunnel = self.get_vxlan_tunnel(vxlan_name)
        if hasattr(vxlan_tunnel, 'records'):
            for record in vxlan_tunnel.records:
                endpoint_list.append(record['endpoint'])

        return endpoint_list

    def fdb_records_update(self, vxlan_name, endpoint_list):
        """Update the fdb records for a vxlan tunnel.

        Args:
            vxlan_name: Name of the vxlan tunnel
            fdb_record_list: IP address associated with the fdb record
        """
        vxlan_tunnel = self.get_vxlan_tunnel(vxlan_name)
        data = {'records': []}
        records = data['records']
        for endpoint in endpoint_list:
            record = {'name': ipv4_to_mac(endpoint), 'endpoint': endpoint}
            records.append(record)
        logger.debug("Updating records for vxlan tunnel {}: {}".format(
            vxlan_name, data['records']))
        vxlan_tunnel.update(**data)
