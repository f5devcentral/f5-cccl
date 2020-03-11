"""Provides functions for merging identical BIG-IP resources togehter."""
# coding=utf-8
#
# Copyright 2018 F5 Networks Inc.
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
import logging

from functools import reduce as reducer  # name conflict between python 2 & 3
from itertools import groupby
from operator import itemgetter


LOGGER = logging.getLogger(__name__)


def _merge_dict_by():
    """Returns a function that merges two dictionaries dst and src.

       Keys are merged together between the dst and src dictionaries.
       If there is a conflict, the src values take precedence.
    """

    return lambda dst, src: {
        key: src[key] if key in src else dst[key]
        for key in list(set(dst.keys()) | set(src.keys()))
    }


def _merge_list_of_dict_by(key):
    """Returns a function that merges a list of dictionary records

       Records are grouped by the specified key.
    """

    keyprop = itemgetter(key)
    return lambda lst: [
        reducer(_merge_dict_by(), records)
        for _, records in groupby(sorted(lst, key=keyprop), keyprop)
    ]


def _merge_list_of_dict_by_name(dst, src):
    """Merge list of Big-IP dictionary records uniquely identified by name.

       Duplicates are not merged, but replaced. Src is added to front.
    """
    merge_list = []
    merge_set = set()
    for record in src:
        merge_list.append(record)
        merge_set.add(record['name'])
    for record in dst:
        if record['name'] not in merge_set:
            merge_list.append(record)
    return merge_list


def _merge_list_of_scalars(dst, src):
    """Merge list of scalars (add src first, then remaining unique dst)"""
    dst_copy = copy.copy(dst)
    src_set = set(src)
    dst = copy.copy(src)
    for val in dst_copy:
        if val not in src_set:
            dst.append(val)
    return dst


def _merge_list(dst, src):
    """Merge lists of a particular type

       Limitations: lists must be of a uniform type: scalar, list, or dict
    """

    if not dst:
        return src
    if isinstance(dst[0], dict):
        dst = _merge_list_of_dict_by_name(dst, src)
    elif isinstance(dst[0], list):
        # May cause duplicates (what is a duplicate for lists of lists?)
        dst = src + dst
    else:
        dst = _merge_list_of_scalars(dst, src)
    return dst


def _merge_dict(dst, src):
    """Merge two dictionaries together, with src overridding dst fields."""

    for key in list(src.keys()):
        dst[key] = merge(dst[key], src[key]) if key in dst else src[key]
    return dst


def merge(dst, src):
    """Merge two resources together with the src fields taking precedence.

       Note: this is specifically tailored for Big-IP resources and
             does not generically support all type variations)
    """

    LOGGER.debug("Merging source: %s", src)
    LOGGER.debug("Merging destination: %s", dst)
    # pylint: disable=C0123
    if type(dst) != type(src):
        # can't merge differing types, src wins everytime
        # (maybe this should be an error)
        dst = copy.deepcopy(src)
    elif isinstance(dst, dict):
        return _merge_dict(dst, src)
    elif isinstance(dst, list):
        return _merge_list(dst, src)
    else:
        # scalar
        dst = src
    LOGGER.debug("Merged result: %s", dst)
    return dst
