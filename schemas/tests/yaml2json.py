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

import json
import sys
import yaml


def main(sys):

    yml_file = sys.argv[1]

    with open(yml_file, 'r') as service_data:
        data = yaml.load(service_data)
        service_data.close()

    print(json.dumps(data, indent=2))


if __name__ == '__main__':
    main(sys)
