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
"""This module defines the schema validator used by f5-cccl."""

from __future__ import print_function

import logging

import jsonschema
from jsonschema import Draft4Validator
from jsonschema import validators
import simplejson as json
import yaml

import f5_cccl.exceptions as cccl_exc

LOGGER = logging.getLogger(__name__)
DEFAULT_SCHEMA = "./f5_cccl/schemas/cccl-api-schema.yml"


def read_yaml(target):
    """Open and read a yaml file."""
    with open(target, 'r') as yaml_file:
        yaml_data = yaml.load(yaml_file)
    return yaml_data


def read_json(target):
    """Open and read a json file."""
    with open(target, 'r') as json_file:
        json_data = json.loads(json_file.read())
    return json_data


def read_yaml_or_json(target):
    """Read json or yaml, return a dict."""
    if target.lower().endswith('.json'):
        return read_json(target)
    elif target.lower().endswith('.yaml') or target.lower().endswith('.yml'):
        return read_yaml(target)
    else:
        raise cccl_exc.F5CcclError(
            'CCCL API schema json or yaml file expected.')


class ServiceConfigValidator(object):
    """A schema validator used by f5-cccl service manager.

    Accepts a json BIG-IP service configuration and validates it against
    against the default schema.

    Optionally accepts an alternate json or yaml schema to validate against.

    """

    def __init__(self, schema=DEFAULT_SCHEMA):
        """Choose schema.

        Raises:
            F5CcclError: Failed to read the CCCL API schema.
        """
        try:
            self.schema = read_yaml_or_json(schema)
        except IOError as error:
            LOGGER.error("%s", error)
            raise cccl_exc.F5CcclError('CCCL API schema could not be read.')

        self.validate_properties = None

    def __set_defaults(self, validator, properties, instance, schema):
        """Helper function to simply return when setting defaults."""
        for item, subschema in properties.items():
            if "default" in subschema:
                instance.setdefault(item, subschema["default"])

        for error in self.validate_properties(validator, properties, instance,
                                              schema):
            yield error

    def _extend_with_default(self, validator_class):
        self.validate_properties = validator_class.VALIDATORS["properties"]
        return validators.extend(validator_class,
                                 {"properties": self.__set_defaults})

    def validate(self, cfg):
        """Check a config against the schema, returns `None` at succeess."""
        LOGGER.debug("Validating desired config against CCCL API schema.")

        validator_with_defaults = self._extend_with_default(Draft4Validator)
        try:
            return validator_with_defaults(self.schema).validate(cfg)
        except jsonschema.exceptions.SchemaError as err:
            msg = str(err)
            raise cccl_exc.SchemaError(msg)
        except jsonschema.exceptions.ValidationError as err:
            msg = str(err)
            raise cccl_exc.ValidationError(msg)
