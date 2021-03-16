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
"""This module defines the schema validator used by f5-cccl."""



import logging
from time import time

import jsonschema
from jsonschema import Draft4Validator
from jsonschema import validators
import simplejson as json
import yaml

import f5_cccl.exceptions as cccl_exc

LOGGER = logging.getLogger(__name__)
DEFAULT_LTM_SCHEMA = "./f5_cccl/schemas/cccl-ltm-api-schema.yml"
DEFAULT_NET_SCHEMA = "./f5_cccl/schemas/cccl-net-api-schema.yml"


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
    if target.lower().endswith('.yaml') or target.lower().endswith('.yml'):
        return read_yaml(target)
    raise cccl_exc.F5CcclError(
        'CCCL API schema json or yaml file expected.')


class ServiceConfigValidator(object):
    """A schema validator used by f5-cccl service manager.

    Accepts a json BIG-IP service configuration and validates it against
    against the default schema.

    Optionally accepts an alternate json or yaml schema to validate against.

    """
    def __init__(self, schema=DEFAULT_LTM_SCHEMA):
        """Choose schema and initialize extended Draft4Validator.

        Raises:
            F5CcclSchemaError: Failed to read or validate the CCCL
            API schema file.
        """

        try:
            self.schema = read_yaml_or_json(schema)
        except json.JSONDecodeError as error:
            LOGGER.error("%s", error)
            raise cccl_exc.F5CcclSchemaError(
                'CCCL API schema could not be decoded.')
        except IOError as error:
            LOGGER.error("%s", error)
            raise cccl_exc.F5CcclSchemaError(
                'CCCL API schema could not be read.')

        try:
            Draft4Validator.check_schema(self.schema)
            self.validate_properties = Draft4Validator.VALIDATORS["properties"]
            validator_with_defaults = validators.extend(
                Draft4Validator,
                {"properties": self.__set_defaults})
            self.validator = validator_with_defaults(self.schema)
        except jsonschema.SchemaError as error:
            LOGGER.error("%s", error)
            raise cccl_exc.F5CcclSchemaError("Invalid API schema")

    def __set_defaults(self, validator, properties, instance, schema):
        """Helper function to simply return when setting defaults."""
        for item, subschema in list(properties.items()):
            if "default" in subschema:
                instance.setdefault(item, subschema["default"])

        for error in self.validate_properties(validator, properties, instance,
                                              schema):
            yield error

    def validate(self, cfg):
        """Check a config against the schema, returns `None` at succeess."""
        LOGGER.debug("Validating desired config against CCCL API schema.")
        start_time = time()

        try:
            LOGGER.debug("validate start")
            self.validator.validate(cfg)
        except jsonschema.exceptions.ValidationError as err:
            msg = str(err)
            raise cccl_exc.F5CcclValidationError(msg)
        finally:
            LOGGER.debug("validate took %.5f seconds.", (time() - start_time))
