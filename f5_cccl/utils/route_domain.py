# coding=utf-8
#
# Copyright (c) 2017,2018, F5 Networks, Inc.
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
"""Helper functions for supporting route domains"""

import re
from requests.utils import quote as urlquote
from requests.utils import unquote as urlunquote


# Pattern: <ipaddr>%<route_domain>
ip_rd_re = re.compile(r'^([^%]*)%(\d+)$')

# Pattern: <partition/folder_paths>/<ipaddr>%<route_domain>[:|.]<port>
path_ip_rd_port_re = re.compile(r'^(.+)/(.+)%(\d+)[:|\.](.+)$')


def combine_ip_and_route_domain(ip, route_domain):
    """Return address that includes IP and route domain

    Input ip format must be of the form:
        <ipv4_or_ipv6>
    """
    address = "{}%{}".format(ip, route_domain)
    return address


def split_ip_with_route_domain(address):
    """Return ip and route-domain parts of address

    Input ip format must be of the form:
        <ip_v4_or_v6_addr>[%<route_domain_id>]
    """
    match = ip_rd_re.match(address)
    if match:
        ip = match.group(1)
        route_domain = int(match.group(2))
    else:
        ip = address
        route_domain = None

    return ip, route_domain


def normalize_address_with_route_domain(address, default_route_domain):
    """Return address with the route domain

    Return components of address, using the default route domain
    for the partition if one is not already specified.

    Input address is of the form:
        <ip_v4_or_v6_addr>[%<route_domain_id>]
    """
    match = ip_rd_re.match(address)
    if match:
        ip = match.group(1)
        route_domain = int(match.group(2))
    else:
        route_domain = default_route_domain
        ip = address
        address = combine_ip_and_route_domain(ip, route_domain)

    return address, ip, route_domain


def encoded_normalize_address_with_route_domain(address,
                                                default_route_domain,
                                                inputUrlEncoded,
                                                outputUrlEncoded):
    """URL Encoded-aware version of normalize_address_with_route_domain"""
    if inputUrlEncoded:
        address = urlunquote(address)

    address = normalize_address_with_route_domain(address,
                                                  default_route_domain)[0]

    if outputUrlEncoded:
        address = urlquote(address)
    return address


def split_fullpath_with_route_domain(address):
    """Determine the individual components of an address path

    Input address format must be of the form:
        <partition_and_folders>/<ipv4_or_ipv6>%<route_domain>[:|.]<port>
    """
    match = path_ip_rd_port_re.match(address)
    if match:
        path = match.group(1)
        ip = match.group(2)
        route_domain = int(match.group(3))
        port = int(match.group(4))
        return path, ip, route_domain, port

    # Future enhancment: we could pass in the default route domain
    # and then return path, ip, default_route_domain, port
    # (current implementation doesn't need this)
    return None, None, None, None
