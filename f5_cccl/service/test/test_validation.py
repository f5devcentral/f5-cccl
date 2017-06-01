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

import simplejson as json
import pytest

from jsonschema import validators, Draft4Validator, exceptions
from mock import Mock
from mock import mock_open
from mock import patch

import f5_cccl.service.validation

from f5_cccl.exceptions import F5CcclError

read_yaml = f5_cccl.service.validation.read_yaml
mock_read_yaml = Mock()
validators_extend = validators.extend
mock_validators_extend = Mock()


class TestSchemaValidator(object):
    """Test Class for testing validator.ServiceConfigValidator"""

    @pytest.fixture()
    def store_code_space(self):
        self.validators_extend = validators.extend

    @pytest.fixture(autouse=True)
    def create_target(self):
        self.schema = Mock()
        read_yaml_or_json = Mock()
        with patch('f5_cccl.service.validation.read_yaml_or_json',
                   read_yaml_or_json, create=True):
            self.validator = \
                f5_cccl.service.validation.ServiceConfigValidator(schema=self.schema)
        self.read_yaml_or_json = read_yaml_or_json

    @pytest.fixture()
    def extended_validator(self, request, store_code_space):
        request.addfinalizer(self.code_space_teardown)
        validators.extend = Mock()

    def code_space_teardown(self):
        validators.extend = self.validators_extend

    def create_generator(self, items):
        for item in items:
            yield item

    def test__init__(self):
        self.read_yaml_or_json.assert_called_once_with(self.schema)
        assert self.read_yaml_or_json() == self.validator.schema, \
            "ServiceConfigValidator.schema is what we expect.."

    def test__set_defaults(self):
        set_defaults = self.validator._ServiceConfigValidator__set_defaults
        validator, properties, instance, schema = \
            ('validator', Mock(), Mock(), 'schema')
        errors = [1, 2, 3]
        self.validator.validate_properties = \
            Mock(return_value=[errors])
        default = dict(default='default')
        properties.items = Mock(return_value=[['item', default]])
        result = set_defaults(validator, properties, instance, schema)
        assert errors in result, "Generator has our errors"
        self.validator.validate_properties.assert_called_once_with(
            validator, properties, instance, schema)

    def test_extend_with_default(self, extended_validator):
        validator_class = Mock()
        validator_class.VALIDATORS = dict(properties="baz")
        self.validator._extend_with_default(validator_class)
        validators.extend.assert_called_once_with(
            validator_class,
            dict(properties=self.validator._ServiceConfigValidator__set_defaults))
        assert self.validator.validate_properties == \
            validator_class.VALIDATORS["properties"], \
            "Confirm validator properties"

    def test_validate(self):
        # set up
        expected = "No exception"
        side_effect = [expected, exceptions.SchemaError("SchemaError"),
                       exceptions.ValidationError("ValidationError")]
        returned_defaults = Mock()
        validator_with_defaults = Mock(return_value=returned_defaults)
        validate = Mock(side_effect=side_effect)
        returned_defaults.validate = validate
        self.validator.schema = "schema"
        self.validator._extend_with_default = \
            Mock(return_value=validator_with_defaults)
        cfg = "cfg"

        # test positive case
        result = self.validator.validate(cfg)
        self.validator._extend_with_default.assert_called_once_with(
            Draft4Validator)
        assert result == expected, expected
        validate.assert_called_once_with(cfg)
        validator_with_defaults.assert_called_once_with(self.validator.schema)

        # test negative cases
        expected_exceptions = [F5CcclError, F5CcclError]
        while expected_exceptions:
            expected = expected_exceptions.pop(0)
            with pytest.raises(expected):
                self.validator.validate(cfg)


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
