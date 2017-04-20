#!/usr/bin/env python3
#
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

"""Common utility functions."""

import sys
import time
import json
import logging
import socket
import argparse

import jwt
import requests

from requests.auth import AuthBase


def parse_log_level(log_level_arg):
    """Parse the log level from the args.

    Args:
        log_level_arg: String representation of log level
    """
    LOG_LEVELS = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']
    if log_level_arg not in LOG_LEVELS:
        msg = 'Invalid option: {0} (Valid choices are {1})'.format(
            log_level_arg, LOG_LEVELS)
        raise argparse.ArgumentTypeError(msg)

    log_level = getattr(logging, log_level_arg, logging.INFO)

    return log_level


def setup_logging(logger, log_format, log_level):
    """Configure logging."""
    logger.setLevel(log_level)

    formatter = logging.Formatter(log_format)

    consoleHandler = logging.StreamHandler(sys.stdout)
    consoleHandler.setFormatter(formatter)
    logger.addHandler(consoleHandler)
    logger.propagate = False


def set_marathon_auth_args(parser):
    """Set the authorization for Marathon."""
    parser.add_argument("--marathon-auth-credential-file",
                        env_var='F5_CC_MARATHON_AUTH',
                        help="Path to file containing a user/pass for "
                        "the Marathon HTTP API in the format of 'user:pass'.")
    parser.add_argument("--dcos-auth-credentials",
                        env_var='F5_CC_DCOS_AUTH_CREDENTIALS',
                        help="DC/OS service account credentials")
    parser.add_argument("--dcos-auth-token",
                        env_var='F5_CC_DCOS_AUTH_TOKEN',
                        help="DC/OS ACS Token")

    return parser


class DCOSAuth(AuthBase):
    """DCOSAuth class.

    Manage authorization credentials for DCOS
    """

    def __init__(self, credentials, ca_cert, token):
        """Initialize DCOSAuth."""
        if credentials:
            creds = json.loads(credentials)
            self.scheme = creds['scheme']
            self.uid = creds['uid']
            self.private_key = creds['private_key']
            self.login_endpoint = creds['login_endpoint']
        self.token = token
        self.verify = False
        self.auth_header = None
        self.expiry = 0
        if ca_cert:
            self.verify = ca_cert

    def __call__(self, auth_request):
        """Get the ACS token."""
        if self.token:
            self.auth_header = 'token=' + self.token
            auth_request.headers['Authorization'] = self.auth_header
            return auth_request

        if not self.auth_header or int(time.time()) >= self.expiry - 10:
            self.expiry = int(time.time()) + 3600
            payload = {
                'uid': self.uid,
                # This is the expiry of the auth request params
                'exp': int(time.time()) + 60,
            }
            token = jwt.encode(payload, self.private_key, self.scheme)

            data = {
                'uid': self.uid,
                'token': token.decode('ascii'),
                # This is the expiry for the token itself
                'exp': self.expiry,
            }
            r = requests.post(self.login_endpoint,
                              json=data,
                              timeout=(3.05, 46),
                              verify=self.verify)
            r.raise_for_status()

            self.auth_header = 'token=' + r.cookies['dcos-acs-auth-cookie']

        auth_request.headers['Authorization'] = self.auth_header
        return auth_request


def get_marathon_auth_params(args):
    """Get the Marathon credentials."""
    marathon_auth = None
    if args.marathon_auth_credential_file:
        with open(args.marathon_auth_credential_file, 'r') as f:
            line = f.readline().rstrip('\r\n')

        if line:
            marathon_auth = tuple(line.split(':'))
    elif args.dcos_auth_credentials or args.dcos_auth_token:
        return DCOSAuth(args.dcos_auth_credentials, args.marathon_ca_cert,
                        args.dcos_auth_token)

    if marathon_auth and len(marathon_auth) != 2:
        print(
            "Please provide marathon credentials in user:pass format"
        )
        sys.exit(1)

    return marathon_auth


def set_logging_args(parser):
    """Add logging-related args to the parser."""
    parser.add_argument("--log-format",
                        env_var='F5_CC_LOG_FORMAT',
                        help="Set log message format",
                        default="%(asctime)s %(name)s: %(levelname)"
                        " -8s: %(message)s")
    parser.add_argument("--log-level",
                        env_var='F5_CC_LOG_LEVEL',
                        type=parse_log_level,
                        help="Set logging level. Valid log levels are: "
                        "DEBUG, INFO, WARNING, ERROR, and CRITICAL",
                        default='INFO')
    return parser


def list_diff(list1, list2):
    """Return items found only in list1."""
    return list(set(list1) - set(list2))


def list_diff_exclusive(list1, list2):
    """Return items found only in list1 or list2."""
    return list(set(list1) ^ set(list2))


def list_intersect(list1, list2):
    """Return the intersection of two lists."""
    return list(set.intersection(set(list1), set(list2)))


ip_cache = dict()


def resolve_ip(host):
    """Get the IP address for a hostname."""
    cached_ip = ip_cache.get(host, None)
    if cached_ip:
        return cached_ip
    else:
        try:
            ip = socket.gethostbyname(host)
            ip_cache[host] = ip
            return ip
        except socket.gaierror:
            return None


class PartitionNameError(Exception):
    """Exception type for F5 resource name."""

    def __init__(self, msg):
        """Create partition name exception object."""
        Exception.__init__(self, msg)


def extract_partition_and_name(f5_partition_name):
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


class IPV4FormatError(Exception):
    """Exception type for improperly formatted IPv4 address."""

    def __init__(self, msg):
        """Create ipv4 format exception object."""
        Exception.__init__(self, msg)


def ipv4_to_mac(ip_str):
    """Convert an IPV4 string to a fake MAC address."""
    ip = ip_str.split('.')
    if len(ip) != 4:
        raise IPV4FormatError('Bad IPv4 address format specified for '
                              'FDB record: {}'.format(ip_str))

    return "0a:0a:%02x:%02x:%02x:%02x" % (
        int(ip[0]), int(ip[1]), int(ip[2]), int(ip[3]))
