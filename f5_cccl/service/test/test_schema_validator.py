#!/usr/bin/env python
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
import f5_cccl.service.validation as validation
import f5_cccl.exceptions as cccl_exc
import json
import jsonschema


def validate(validator, services):
    """Wrapper for validation of a service description."""
    try:
        validator.validate(services)
        return 'Schema Valid'
    except jsonschema.exceptions.SchemaError:
        return 'Schema Error'
    except cccl_exc.F5CcclValidationError as e:
        return 'Validator Error'


def validate_required(validator, schema, services, rsc_type, rscs):
    """Validate required values."""
    required = schema['definitions'][rsc_type]['required']

    # Go through the schema, find the 'required' fields, remove them and
    # verify that the validator catches the error
    for req in required:
        for idx, rsc in enumerate(services[rscs]):
            tmp = rsc[req]
            # delete it
            del rsc[req]
            services[rscs][idx] = rsc

            # Required field is missing, should be an error
            result = validate(validator, services)
            assert result == 'Validator Error'

            rsc[req] = tmp
            services[rscs][idx] = rsc


def validate_defaults(validator, schema, services, rsc_type, rscs):
    """Validate default values."""
    properties = schema['definitions'][rsc_type]['properties']

    # Go through the schema, find the 'default' fields, and verify that the
    # validator has added the defaults
    for key, value in list(properties.items()):
        default = value.get('default')
        if default is not None:
            for idx, rsc in enumerate(services[rscs]):
                assert rsc[key] == default


def validate_string(validator, schema, services, rsc, key, prop):
    """Validate a string property."""
    tmp = rsc.get(key)
    if tmp is not None:
        # not a string, validation should fail
        rsc[key] = 100
        result = validate(validator, services)
        assert result == 'Validator Error'
        rsc[key] = tmp

    minLength = prop.get('minLength')
    if minLength is not None and minLength > 0:
        tmp = rsc.get(key)
        if tmp is not None:
            # less than min length, validation should fail
            rsc[key] = ''
            result = validate(validator, services)
            assert result == 'Validator Error'
            rsc[key] = tmp

    maxLength = prop.get('maxLength')
    if maxLength is not None:
        tmp = rsc.get(key)
        if tmp is not None:
            # greater than max length, validation should fail
            rsc[key] = 'x' * (maxLength + 1)
            result = validate(validator, services)
            assert result == 'Validator Error'
            rsc[key] = tmp


def validate_integer(validator, schema, services, rsc, key, prop):
    """Validate an integer property."""
    tmp = rsc.get(key)
    if tmp is not None:
        # not an integer, validation should fail
        rsc[key] = 'This is not a number!'
        result = validate(validator, services)
        assert result == 'Validator Error'
        rsc[key] = tmp

    minimum = prop.get('minimum')
    if minimum is not None:
        tmp = rsc.get(key)
        if tmp is not None:
            # less than min value, validation should fail
            rsc[key] = minimum - 1
            result = validate(validator, services)
            assert result == 'Validator Error'
            rsc[key] = tmp

    maximum = prop.get('maximum')
    if maximum is not None:
        tmp = rsc.get(key)
        if tmp is not None:
            # greater than max value, validation should fail
            rsc[key] = maximum + 1
            result = validate(validator, services)
            assert result == 'Validator Error'
            rsc[key] = tmp


def validate_types(validator, schema, services, rsc_type, rscs):
    """Validate the basic types in the schema."""
    properties = schema['definitions'][rsc_type]['properties']

    # Go through the schema; find the strings, integers, and enums and
    # change them to invalid values and verify that the validator catches
    # the errors
    for key, value in list(properties.items()):
        val_type = value.get('type')
        if val_type is not None:
            for idx, rsc in enumerate(services[rscs]):
                # check strings
                if val_type == 'string':
                    validate_string(validator, schema, services, rsc, key,
                                    value)

                # check integers
                if val_type == 'integer':
                    validate_integer(validator, schema, services, rsc, key,
                                     value)

                # check enums
                enum = value.get('enum')
                if enum is not None:
                    tmp = rsc.get(key)
                    if tmp is not None:
                        rsc[key] = 'This string will match no enums'
                        result = validate(validator, services)
                        assert result == 'Validator Error'
                        rsc[key] = tmp


def test_resources():
    """Load a service description and validate it with the schema."""
    resourceTypes = [
        {
            'file': 'f5_cccl/schemas/tests/ltm_service.json',
            'schema': validation.DEFAULT_LTM_SCHEMA,
            'resources': {
                'virtualServerType': 'virtualServers',
                'poolType': 'pools',
                'l7PolicyType': 'l7Policies',
                'healthMonitorType': 'monitors',
                'iAppType': 'iapps'
            }
        },
        {
            'file': 'f5_cccl/schemas/tests/net_service.json',
            'schema': validation.DEFAULT_NET_SCHEMA,
            'resources': {
                'arpType': 'arps',
                'fdbTunnelType': 'fdbTunnels'
            }
        }
    ]
    for rType in resourceTypes:
        svcfile = rType['file']
        services = json.loads(open(svcfile, 'r').read())
    
        validator = validation.ServiceConfigValidator(rType['schema'])
        result = validate(validator, services)
        assert result == 'Schema Valid'
    
        schema = validation.read_yaml_or_json(rType['schema'])
    
        # Test the validator and verify that it:
        # - catches missing required fields
        # - supplies correct defaults
        # - catches invalid parameter values and types
        for key, value in list(rType['resources'].items()):
            validate_required(validator, schema, services, key, value)
            validate_defaults(validator, schema, services, key, value)
            validate_types(validator, schema, services, key, value)
