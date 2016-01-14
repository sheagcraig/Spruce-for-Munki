#!/usr/bin/python
# Copyright 2016 Shea G. Craig
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

"""Helper functions for interacting with Munki repos."""


import os

import FoundationPlist


PKGINFO_EXTENSIONS = (".pkginfo", ".plist")


def get_pkg_path():
    """Return the path to the repo's packages."""
    return os.path.join(get_repo_path(), "pkgs")


def get_all_catalog():
    """Return the Munki 'all' catalog as a plist dict."""
    munki_repo = get_repo_path()
    all_path = os.path.join(munki_repo, "catalogs", "all")
    return FoundationPlist.readPlist(all_path)


def get_repo_path():
    """Get path to the munki repo according to munkiimport's prefs."""
    munkiimport_prefs = get_munkiimport_prefs()
    return munkiimport_prefs.get("repo_path")


def get_munkiimport_prefs():
    """Get the current user's munkiimport preferences as plist dict."""
    return FoundationPlist.readPlist(os.path.expanduser(
        "~/Library/Preferences/com.googlecode.munki.munkiimport.plist"))


def get_categories(all_catalog, filter_func=lambda x: True):
    """Return a list of the category for each pkginfo in the repo."""
    return [pkginfo.get("category", "*NO CATEGORY*") for pkginfo in all_catalog
            if filter_func(pkginfo)]


def get_unique_names(all_catalog):
    """Return a set of product names."""
    return {pkginfo.get("name", "*NO NAME*") for pkginfo in all_catalog}


def build_pkginfo_cache(repo):
    """Return a dict of all pkginfo files in the repo."""
    pkginfos = {}
    pkginfo_dir = os.path.join(repo, "pkgsinfo")
    for dirpath, _, filenames in os.walk(pkginfo_dir):
        for ifile in filter(is_pkginfo, filenames):
            path = os.path.join(dirpath, ifile)
            try:
                pkginfo_file = FoundationPlist.readPlist(path)
            except FoundationPlist.FoundationPlistException:
                continue

            pkginfos[path] = pkginfo_file

    return pkginfos


def is_pkginfo(candidate):
    return os.path.splitext(candidate)[-1].lower() in PKGINFO_EXTENSIONS
