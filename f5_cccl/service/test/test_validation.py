#!/usr/bin/env python
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

import copy
import simplejson as json
import pdb
import pytest
import yaml

from jsonschema import validators, Draft4Validator, exceptions
from mock import Mock
from mock import mock_open
from mock import patch

import f5_cccl.service.validation
from f5_cccl.service.validation import ServiceConfigValidator

from f5_cccl.exceptions import F5CcclError
from f5_cccl.exceptions import F5CcclSchemaError
from f5_cccl.exceptions import F5CcclValidationError

read_yaml = f5_cccl.service.validation.read_yaml
mock_read_yaml = Mock()
validators_extend = validators.extend
mock_validators_extend = Mock()


class TestConfigValidator(object):
    """Test Class for testing validator.ServiceConfigValidator"""

    @pytest.fixture(autouse=True)
    def ltm_schema(self):
        with open('f5_cccl/schemas/cccl-ltm-api-schema.yml', 'r') as fp:
            yaml_data = yaml.load(fp)
        return yaml_data

    @pytest.fixture()
    def net_schema(self):
        with open('f5_cccl/schemas/cccl-net-api-schema.yml', 'r') as fp:
            yaml_data = yaml.load(fp)
        return yaml_data

    @pytest.fixture()
    def valid_ltm_config(self):
        with open('f5_cccl/schemas/tests/ltm_service.json', 'r') as fp:
            service_data = json.load(fp)
        return service_data

    @pytest.fixture()
    def valid_net_config(self):
        with open('f5_cccl/schemas/tests/net_service.json', 'r') as fp:
            service_data = json.load(fp)
        return service_data

    def test__init__(self, ltm_schema, net_schema):
        """Test the creation of the CCCL service config validator."""

        # Test a schema that does not exist.
        with pytest.raises(F5CcclSchemaError) as e:
            validator = ServiceConfigValidator(schema="test_schema.json")
        assert str(e.value) == ("F5CcclSchemaError - Schema provided is invalid: " +
                                "CCCL API schema could not be read.")

        bad_schema='f5_cccl/service/test/bad_schema.json'
        with pytest.raises(F5CcclSchemaError) as e:
            validator = ServiceConfigValidator(schema=bad_schema)
        assert str(e.value) == ("F5CcclSchemaError - Schema provided is invalid: " +
                                "Invalid API schema")

        bad_schema='f5_cccl/service/test/bad_decode_schema.json'
        with pytest.raises(F5CcclSchemaError) as e:
            validator = ServiceConfigValidator(schema=bad_schema)
        assert str(e.value) == ("F5CcclSchemaError - Schema provided is invalid: " +
                                "CCCL API schema could not be decoded.")

        validator = ServiceConfigValidator()
        assert validator.validator
        assert validator.validator.META_SCHEMA == Draft4Validator.META_SCHEMA
        assert validator.validator.schema == ltm_schema

        validator = ServiceConfigValidator(
            schema="f5_cccl/schemas/cccl-net-api-schema.yml")
        assert validator.validator
        assert validator.validator.META_SCHEMA == Draft4Validator.META_SCHEMA
        assert validator.validator.schema == net_schema

    def test_validate(self, valid_ltm_config, valid_net_config):
        """Test the validation method."""
        ltm_validator = ServiceConfigValidator()
        net_validator = ServiceConfigValidator(
            schema="f5_cccl/schemas/cccl-net-api-schema.yml")

        try:
            ltm_validator.validate(valid_ltm_config)
            net_validator.validate(valid_net_config)
        except F5CcclValidationError as e:
            assert False, "ValidationError raised for valid config"

        # Modify the configuration to make invalid.
        invalid_config = copy.deepcopy(valid_ltm_config)
        virtuals = invalid_config['virtualServers']
        for virtual in virtuals:
            virtual.pop('destination', None)
            virtual.pop('name', None)

        with pytest.raises(F5CcclValidationError):
            ltm_validator.validate(invalid_config)

        invalid_config = copy.deepcopy(valid_net_config)
        arps = invalid_config['arps']
        for arp in arps:
            arp.pop('ipAddress', None)

        with pytest.raises(F5CcclValidationError):
            net_validator.validate(invalid_config)


@pytest.fixture()
def store_read_yaml(request):
    def teardown():
        f5_cccl.service.validation.read_yaml = read_yaml

    request.addfinalizer(teardown)
    f5_cccl.service.validation.read_yaml = mock_read_yaml


@pytest.fixture()
def store_json_loads(request):
    def teardown():
        json.loads = json.loads.teardown

    request.addfinalizer(teardown)
    temp = Mock()
    temp.teardown = json.loads
    json.loads = temp


@pytest.fixture()
def store_validators_extend(request):
    def teardown():
        validators.extend = validators_extend

    request.addfinalizer(teardown)
    validators.extend = mock_validators_extend


def test_read_yaml_or_json(store_read_yaml):
    json_case = "foodogzoocoo.json"
    JSON_case = "randomforrandom.JSON"
    yaml_case = "somethingpizza.yaml"
    yml_case = "totallydifferent.yml"
    negative_case = "whatsortof.values"
    read_json = Mock()
    with patch('f5_cccl.service.validation.read_json', read_json, create=True):
        # json Case
        f5_cccl.service.validation.read_yaml_or_json(json_case)
        read_json.assert_called_once_with(json_case)
        read_json.reset_mock()
        # JSON Case:
        f5_cccl.service.validation.read_yaml_or_json(JSON_case)
        read_json.assert_called_once_with(JSON_case)
        read_json.reset_mock()
        # yaml case:
        f5_cccl.service.validation.read_yaml_or_json(yaml_case)
        mock_read_yaml.assert_called_once_with(yaml_case)
        mock_read_yaml.reset_mock()
        # yml Case
        f5_cccl.service.validation.read_yaml_or_json(yml_case)
        mock_read_yaml.assert_called_once_with(yml_case)
        mock_read_yaml.reset_mock()

    with pytest.raises(F5CcclError):
        f5_cccl.service.validation.read_yaml_or_json(negative_case)
        mock_read_yaml.assert_called_once_with(negative_case)


def test_read_yaml():
    expected = "I should get this back!"
    read_data = 'hello world'
    mock_yaml = Mock(return_value=expected)
    m = mock_open(read_data=read_data)
    with patch('f5_cccl.service.validation.open', m, create=True):
        with patch('yaml.load', mock_yaml, create=True):
            result = f5_cccl.service.validation.read_yaml('stuff')
            assert m.called, "We opened a file"
            assert result == expected, "We got what we came for"


def test_read_json(store_json_loads):
    expected = "I should get this back!"
    read_data = 'hello world'
    json.loads.return_value = expected
    m = mock_open(read_data=read_data)
    with patch('f5_cccl.service.validation.open', m, create=True):
        result = f5_cccl.service.validation.read_json('stuff')
        assert m.called, "We opened a file"
        json.loads.assert_called_once_with(read_data)
        assert result == expected, "We got what we came for"
