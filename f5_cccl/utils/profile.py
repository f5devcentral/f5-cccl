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
"""Wrapper functions for custom-profile mgmt via the f5-sdk"""

import logging
import os

LOGGER = logging.getLogger(__name__)


def create_client_ssl_profile(mgmt, partition, profile):
    """Create a Client SSL Profile."""
    ssl_client_profile = mgmt.tm.ltm.profile.client_ssls.client_ssl
    incomplete = 0

    name = profile['name']

    # No need to create if it exists
    if ssl_client_profile.exists(name=name, partition=partition):
        return 0

    cert = profile['cert']
    cert_name = name + '.crt'
    if cert != "":
        incomplete = _install_certificate(mgmt, cert, cert_name)
    if incomplete > 0:
        # Unable to install cert
        return incomplete

    key = profile['key']
    key_name = name + '.key'
    if key != "":
        incomplete = _install_key(mgmt, key, key_name)
    if incomplete > 0:
        # Unable to install key
        return incomplete

    try:
        # create ssl-client profile from cert/key pair
        serverName = profile.get('serverName', None)
        sniDefault = profile.get('sniDefault', False)
        kwargs = {}
        if cert != "" and key != "":
            chain = [{'name': name,
                      'cert': '/Common/' + cert_name,
                      'key': '/Common/' + key_name}]
            kwargs = {'certKeyChain': chain}

        ssl_client_profile.create(name=name,
                                  partition=partition,
                                  serverName=serverName,
                                  sniDefault=sniDefault,
                                  defaultsFrom=None,
                                  **kwargs)
    except Exception as err:  # pylint: disable=broad-except
        LOGGER.error("Error creating client SSL profile: %s", str(err))
        incomplete = 1

    return incomplete


def create_server_ssl_profile(mgmt, partition, profile):
    """Create a Server SSL Profile."""
    ssl_server_profile = mgmt.tm.ltm.profile.server_ssls.server_ssl
    incomplete = 0

    name = profile['name']

    # No need to create if it exists
    if ssl_server_profile.exists(name=name, partition=partition):
        return 0

    cert = profile['cert']
    cert_name = name + '.crt'
    if cert != "":
        incomplete = _install_certificate(mgmt, cert, cert_name)
    if incomplete > 0:
        # Unable to install cert
        return incomplete

    try:
        # create ssl-server profile
        serverName = profile.get('serverName', None)
        sniDefault = profile.get('sniDefault', False)
        peerCertMode = profile.get('peerCertMode', 'ignore')
        kwargs = {}
        if cert != "":
            kwargs = {'chain': cert_name}

        ssl_server_profile.create(name=name,
                                  partition=partition,
                                  serverName=serverName,
                                  sniDefault=sniDefault,
                                  peerCertMode=peerCertMode,
                                  **kwargs)
    except Exception as err:  # pylint: disable=broad-except
        incomplete += 1
        LOGGER.error("Error creating server SSL profile: %s", str(err))

    return incomplete


def delete_unused_ssl_profiles(mgmt, partition, config):
    """Delete unused SSL Profiles."""
    incomplete = 0

    # client profiles
    try:
        client_profiles = mgmt.tm.ltm.profile.client_ssls.get_collection(
            requests_params={'params': '$filter=partition+eq+%s' % partition})
        incomplete += _delete_ssl_profiles(config, client_profiles)
    except Exception as err:  # pylint: disable=broad-except
        LOGGER.error("Error reading client SSL profiles from BIG-IP: %s",
                     str(err))
        incomplete += 1

    # server profiles
    try:
        server_profiles = mgmt.tm.ltm.profile.server_ssls.get_collection(
            requests_params={'params': '$filter=partition+eq+%s' % partition})
        incomplete += _delete_ssl_profiles(config, server_profiles)
    except Exception as err:  # pylint: disable=broad-except
        LOGGER.error("Error reading server SSL profiles from BIG-IP: %s",
                     str(err))
        incomplete += 1

    return incomplete


def _delete_ssl_profiles(config, profiles):
    incomplete = 0

    if 'customProfiles' not in config:
        # delete any profiles in managed partition
        for prof in profiles:
            try:
                prof.delete()
            except Exception as err:  # pylint: disable=broad-except
                LOGGER.error("Error deleting SSL profile: %s", str(err))
                incomplete += 1
    else:
        # delete profiles no longer in our config
        for prof in profiles:
            if not any(d['name'] == prof.name
                       for d in config['customProfiles']):
                try:
                    prof.delete()
                except Exception as err:  # pylint: disable=broad-except
                    LOGGER.error("Error deleting SSL profile: %s", str(err))
                    incomplete += 1

    return incomplete


def _upload_crypto_file(mgmt, file_data, file_name):
    # bigip object is of type f5.bigip.tm;
    # we need f5.bigip.shared for the uploader
    uploader = mgmt.shared.file_transfer.uploads

    # In-memory upload -- data not written to local file system but
    # is saved as a file on the BIG-IP
    uploader.upload_bytes(file_data, file_name)


def _import_certificate(mgmt, cert_name):
    cert_registrar = mgmt.tm.sys.crypto.certs
    param_set = {}
    param_set['name'] = cert_name
    param_set['from-local-file'] = os.path.join(
        '/var/config/rest/downloads', cert_name)
    cert_registrar.exec_cmd('install', **param_set)


def _import_key(mgmt, key_name):
    key_registrar = mgmt.tm.sys.crypto.keys
    param_set = {}
    param_set['name'] = key_name
    param_set['from-local-file'] = os.path.join(
        '/var/config/rest/downloads', key_name)
    key_registrar.exec_cmd('install', **param_set)


def _install_certificate(mgmt, cert_data, cert_name):
    incomplete = 0

    try:
        if not _certificate_exists(mgmt, cert_name):
            # Upload and install cert
            _upload_crypto_file(mgmt, cert_data, cert_name)
            _import_certificate(mgmt, cert_name)

    except Exception as err:  # pylint: disable=broad-except
        incomplete += 1
        LOGGER.error("Error uploading certificate %s: %s", cert_name, str(err))

    return incomplete


def _install_key(mgmt, key_data, key_name):
    incomplete = 0

    try:
        if not _key_exists(mgmt, key_name):
            # Upload and install cert
            _upload_crypto_file(mgmt, key_data, key_name)
            _import_key(mgmt, key_name)

    except Exception as err:  # pylint: disable=broad-except
        incomplete += 1
        LOGGER.error("Error uploading key %s: %s", key_name, str(err))

    return incomplete


def _certificate_exists(mgmt, cert_name):
    # All certs are in the Common partition
    name_to_find = "/Common/{}".format(cert_name)
    for cert in mgmt.tm.sys.crypto.certs.get_collection():
        if cert.name == name_to_find:
            return True
    return False


def _key_exists(mgmt, key_name):
    # All keys are in the Common partition
    name_to_find = "/Common/{}".format(key_name)
    for key in mgmt.tm.sys.crypto.keys.get_collection():
        if key.name == name_to_find:
            return True
    return False


def _delete_unused_ssl_profiles(mgmt, partition, config):
    incomplete = 0

    # client profiles
    try:
        client_profiles = mgmt.tm.ltm.profile.client_ssls.get_collection(
            requests_params={'params': '$filter=partition+eq+%s' % partition})
        incomplete += _delete_ssl_profiles(config, client_profiles)
    except Exception as err:  # pylint: disable=broad-except
        LOGGER.error("Error reading client SSL profiles from BIG-IP: %s",
                     str(err))
        incomplete += 1

    # server profiles
    try:
        server_profiles = mgmt.tm.ltm.profile.server_ssls.get_collection(
            requests_params={'params': '$filter=partition+eq+%s' % partition})
        incomplete += _delete_ssl_profiles(config, server_profiles)
    except Exception as err:  # pylint: disable=broad-except
        LOGGER.error("Error reading server SSL profiles from BIG-IP: %s",
                     str(err))
        incomplete += 1

    return incomplete
