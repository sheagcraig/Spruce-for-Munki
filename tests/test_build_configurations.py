#!/usr/bin/env python
# Copyright 2015 Shea G. Craig
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
#
# See the License for the specific language governing permissions and
# limitations under the License.


from munki_tools import FoundationPlist
from nose.tools import *

import build_configurations


class TestBuildConfigurations(object):

    def setUp(self):
        self.manifests = ("IT", "General", "JMP")
        self.catalogs = ("testing", "phase1", "phase2")

    def test_get_permutations(self):
        expecteds = [(manifest, catalog.title()) for manifest in self.manifests
                     for catalog in self.catalogs]
        results = list(build_configurations.get_permutations(
            self.manifests, self.catalogs))
        for expected in expecteds:
            assert_in(expected, results)

    def test_build_munki_config(self):
        expected_plist = FoundationPlist.readPlist(
            "tests/resources/Expected.plist")
        result = build_configurations.build_munki_config(("IT", "Testing"))
        test_values = ("ClientIdentifier",)
        for key in test_values:
            assert_equal(
                expected_plist["PayloadContent"][0]["PayloadContent"]["ManagedInstalls"]["Forced"][0]["mcx_preference_settings"][key],
                result["PayloadContent"][0]["PayloadContent"]["ManagedInstalls"]["Forced"][0]["mcx_preference_settings"][key])

