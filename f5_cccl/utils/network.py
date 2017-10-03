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
"""Wrapper functions for the f5-sdk network config"""

import logging
try:
    from urllib import quote
except ImportError:
    from urllib.parse import quote

LOGGER = logging.getLogger(__name__)


class PartitionNameError(Exception):
    """Exception type for F5 resource name."""

    def __init__(self, msg):
        """Create partition name exception object."""
        Exception.__init__(self, msg)


class IPV4FormatError(Exception):
    """Exception type for improperly formatted IPv4 address."""

    def __init__(self, msg):
        """Create ipv4 format exception object."""
        Exception.__init__(self, msg)


def apply_network_fdb_config(mgmt_root, fdb_config):
    """Apply the network fdb configuration to the BIG-IP.

    Args:
        config: BIG-IP network fdb config dict
    """
    req_vxlan_name = fdb_config['vxlan-name']
    req_fdb_record_endpoint_list = fdb_config['vxlan-node-ips']
    try:
        f5_fdb_record_endpoint_list = _get_fdb_records(mgmt_root,
                                                       req_vxlan_name)

        _log_sequence('req_fdb_record_list', req_fdb_record_endpoint_list)
        _log_sequence('f5_fdb_record_list', f5_fdb_record_endpoint_list)

        # See if the list of records is different.
        # If so, update with new list.
        if _list_diff_exclusive(f5_fdb_record_endpoint_list,
                                req_fdb_record_endpoint_list):
            _fdb_records_update(mgmt_root,
                                req_vxlan_name,
                                req_fdb_record_endpoint_list)
        return 0
    except (PartitionNameError, IPV4FormatError) as e:
        LOGGER.error(e)
        return 0
    except Exception as e:  # pylint: disable=broad-except
        LOGGER.error('Failed to configure the FDB for VxLAN tunnel %s: %s',
                     req_vxlan_name, e)
        return 1


def _get_vxlan_tunnel(mgmt_root, vxlan_name):
    """Get a vxlan tunnel object.

    Args:
        vxlan_name: Name of the vxlan tunnel
    """
    partition, name = _extract_partition_and_name(vxlan_name)
    vxlan_tunnel = mgmt_root.tm.net.fdb.tunnels.tunnel.load(
        partition=partition, name=quote(name))
    return vxlan_tunnel


def _get_fdb_records(mgmt_root, vxlan_name):
    """Get a list of FDB records (just the endpoint list) for the vxlan.

    Args:
        vxlan_name: Name of the vxlan tunnel
    """
    endpoint_list = []
    vxlan_tunnel = _get_vxlan_tunnel(mgmt_root, vxlan_name)
    if hasattr(vxlan_tunnel, 'records'):
        for record in vxlan_tunnel.records:
            endpoint_list.append(record['endpoint'])

    return endpoint_list


def _fdb_records_update(mgmt_root, vxlan_name, endpoint_list):
    """Update the fdb records for a vxlan tunnel.

    Args:
        vxlan_name: Name of the vxlan tunnel
        fdb_record_list: IP address associated with the fdb record
    """
    vxlan_tunnel = _get_vxlan_tunnel(mgmt_root, vxlan_name)
    data = {'records': []}
    records = data['records']
    for endpoint in endpoint_list:
        record = {'name': _ipv4_to_mac(endpoint), 'endpoint': endpoint}
        records.append(record)
    LOGGER.debug("Updating records for vxlan tunnel %s: %s",
                 vxlan_name, data['records'])
    vxlan_tunnel.update(**data)


def _extract_partition_and_name(f5_partition_name):
    """Separate partition and name components for a Big-IP resource."""
    parts = f5_partition_name.split('/')
    count = len(parts)
    if f5_partition_name[0] == '/' and count == 3:
        # leading slash
        partition = parts[1]
        name = parts[2]
    elif f5_partition_name[0] != '/' and count == 2:
        # leading slash missing
        partition = parts[0]
        name = parts[1]
    else:
        raise PartitionNameError('Bad F5 resource name encountered: '
                                 '{}'.format(f5_partition_name))
    return partition, name


def _log_sequence(prefix, sequence_to_log):
    """Helper function to log a sequence.

    Dump a sequence to the logger, skip if it is empty

    Args:
        prefix: The prefix string to describe what's being logged
        sequence_to_log: The sequence being logged
    """
    if sequence_to_log:
        LOGGER.debug(prefix + ': %s', (', '.join(sequence_to_log)))


def _list_diff_exclusive(list1, list2):
    """Return items found only in list1 or list2."""
    return list(set(list1) ^ set(list2))


def _ipv4_to_mac(ip_str):
    """Convert an IPV4 string to a fake MAC address."""
    ip = ip_str.split('.')
    if len(ip) != 4:
        raise IPV4FormatError('Bad IPv4 address format specified for '
                              'FDB record: {}'.format(ip_str))

    return "0a:0a:%02x:%02x:%02x:%02x" % (
        int(ip[0]), int(ip[1]), int(ip[2]), int(ip[3]))
