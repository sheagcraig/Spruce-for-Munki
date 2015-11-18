#!/usr/bin/env python


from nose.tools import *

import build_configurations


class TestBuildConfigurations(object):

    def test_get_permutations(self):
        manifests = ("IT", "General", "JMP")
        catalogs = ("testing", "phase1", "phase2")
        expecteds = [(manifest, catalog) for manifest in manifests for catalog
                     in catalogs]
        results = list(build_configurations.get_permutations(
            manifests, catalogs))
        for expected in expecteds:
            assert_in(expected, results)
