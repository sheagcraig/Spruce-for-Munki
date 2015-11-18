#!/usr/bin/python


import FoundationPlist


def get_permutations(manifests, catalogs):
    return ((manifest, catalog) for manifest in manifests for catalog in
            catalogs)