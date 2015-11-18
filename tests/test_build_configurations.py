#!/usr/bin/env python


import FoundationPlist
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

