#!/usr/bin/env python
# coding=utf-8
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

from __future__ import print_function
import argparse
import json
import jsonschema
from jsonschema import validators
from jsonschema import Draft4Validator
import sys


def extend_with_default(validator_class):
    validate_properties = validator_class.VALIDATORS["properties"]

    def set_defaults(validator, properties, instance, schema):
        for property, subschema in properties.iteritems():
            if "default" in subschema:
                instance.setdefault(property, subschema["default"])

        for error in validate_properties(
                validator, properties, instance, schema,):
            yield error

    return validators.extend(
        validator_class, {"properties": set_defaults}
    )


def get_arg_parser():
    """Create the parser for the command-line args."""
    parser = argparse.ArgumentParser()

    parser.add_argument("--svcfile",
                        help="services filename")
    parser.add_argument("--schemafile",
                        help="schema filename")
    parser.add_argument("--dump",
                        action='store_true',
                        help="dump json output")
    return parser


def parse_args():
    """Entry point for parsing command-line args."""
    # Process arguments
    arg_parser = get_arg_parser()
    args = arg_parser.parse_args()

    if not args.svcfile:
        arg_parser.error('argument --svcfile is required: please ' +
                         'specify')
    if not args.schemafile:
        arg_parser.error('argument --schemafile is required: please ' +
                         'specify')
    return args


def main(argv):
    args = parse_args()
    DefaultValidatingDraft4Validator = extend_with_default(Draft4Validator)
    services = json.loads(open(args.svcfile, 'r').read())
    json_schema = args.schemafile

    with open(json_schema) as f:
        schema_data = f.read()
        schema = json.loads(schema_data)
        Draft4Validator.check_schema(schema)

    try:
        DefaultValidatingDraft4Validator(schema).validate(services)
        print("Schema Valid")
    except jsonschema.exceptions.SchemaError as e:
        print("Schema Error")
        print(e)
    except jsonschema.exceptions.ValidationError as e:
        print("Validator Error")
        print(e)
    if args.dump:
        print(json.dumps(services, indent=2))


if __name__ == '__main__':
    main(sys.argv)
