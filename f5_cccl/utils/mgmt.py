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
#
"""Wrapper functions for the f5-sdk"""

from f5.bigip import ManagementRoot


def mgmt_root(host, username, password, port, token, ca_certs=None):
    """Create a BIG-IP Management Root object with per-endpoint TLS support
    
    Args:
        host: BIG-IP management hostname or IP
        username: BIG-IP username for authentication
        password: BIG-IP password for authentication
        port: BIG-IP management port (e.g. 443)
        token: Optional token for authentication (bypasses username/password)
        ca_certs: Optional path to CA certificate file for TLS verification.
                 If provided, enables TLS verification using this CA bundle.
                 If None or empty, TLS verification is disabled (default).
    
    Returns:
        ManagementRoot: f5-sdk ManagementRoot instance for API operations
    
    Notes:
        E7 Requirement: Per-endpoint trusted certificates support for TMOS DNS endpoints.
        The f5-sdk ManagementRoot uses the 'verify' parameter for TLS certificate handling:
        - verify=False: No SSL verification (default, safe for self-signed certs)
        - verify=True: Use system default CA bundle
        - verify=<path>: Use specified CA certificate file
    """
    # Build kwargs for ManagementRoot
    # E7: When ca_certs is provided, enable TLS verification using the verify parameter
    # which is the officially supported mechanism in f5-sdk ManagementRoot
    kwargs = {
        'port': port,
        'token': token,
        'verify': ca_certs if ca_certs else False,  # E7: Per-endpoint trusted certs
    }
    
    return ManagementRoot(host, username, password, **kwargs)
