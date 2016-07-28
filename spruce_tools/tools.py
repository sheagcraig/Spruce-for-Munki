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


import imp
import os
import sys

sys.path.append("/usr/local/munki")
from munkilib import FoundationPlist


PKGINFO_EXTENSIONS = (".pkginfo", ".plist")


def get_pkg_path():
    """Return the path to the repo's packages."""
    return os.path.join(get_repo_path(), "pkgs")


def get_pkgsinfo_path():
    """Return the path to the repo's packages."""
    return os.path.join(get_repo_path(), "pkgsinfo")


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


def get_icons_path():
    """Get path to the munki icons repo according to munkiimport."""
    munkiimport_prefs = get_munkiimport_prefs()
    return munkiimport_prefs.get(
        "IconURL", os.path.join(munkiimport_prefs.get("repo_path"), "icons"))


def get_unique_names(all_catalog):
    """Return a set of product names."""
    return {pkginfo.get("name", "*NO NAME*") for pkginfo in all_catalog}


# TODO: This needs to mount the repo if it isn't already.
def build_pkginfo_cache(repo):
    """Build a dictionary of pkgsinfo.

    Args:
        repo: String path to the base of a Munki repo.

    Returns:
        Dictionary of pkgsinfo with:
            key: path to pkginfo
            val: pkginfo dictionary
    """
    pkginfos, _ = build_pkginfo_cache_with_errors(repo)
    return pkginfos


def build_pkginfo_cache_with_errors(repo):
    """Build a dictionary of pkgsinfo.

    Args:
        repo: String path to the base of a Munki repo.

    Returns:
        Tuple of:
            Dictionary of pkgsinfo with:
                key: path to pkginfo.
                val: pkginfo dictionary.
            Dictionary of errors with:
                key: path to pkginfo.
                val: Exception message.

    """
    pkginfos = {}
    errors = {}
    pkginfo_dir = os.path.join(repo, "pkgsinfo")
    for dirpath, _, filenames in os.walk(pkginfo_dir):
        for ifile in filter(is_pkginfo, filenames):
            path = os.path.join(dirpath, ifile)
            try:
                pkginfo_file = FoundationPlist.readPlist(path)
            except FoundationPlist.FoundationPlistException as error:
                errors[path] = error.message
                continue

            pkginfos[path] = pkginfo_file

    return (pkginfos, errors)


def is_pkginfo(candidate):
    return os.path.splitext(candidate)[-1].lower() in PKGINFO_EXTENSIONS


def in_testing(pkginfo):
    testing_catalogs = ("development", "testing", "phase1", "phase2",
                        "phase3")
    return any(catalog.lower() in testing_catalogs for catalog in
               pkginfo.get("catalogs", []))


def in_production(pkginfo):
    return not in_testing(pkginfo)


def is_unattended_install(pkginfo):
    return pkginfo.get("unattended_install") == True


def is_not_unattended_install(pkginfo):
    return pkginfo.get("unattended_install", False) == False


def split_name_from_version(name_string):
    """Splits a string into the name and version number.
    Name and version must be seperated with a hyphen ('-')
    or double hyphen ('--').
    'TextWrangler-2.3b1' becomes ('TextWrangler', '2.3b1')
    'AdobePhotoshopCS3--11.2.1' becomes ('AdobePhotoshopCS3', '11.2.1')
    'MicrosoftOffice2008-12.2.1' becomes ('MicrosoftOffice2008', '12.2.1')
    """
    # This code comes from Munki.
    for delim in ('--', '-'):
        if name_string.count(delim) > 0:
            chunks = name_string.split(delim)
            vers = chunks.pop()
            name = delim.join(chunks)
            if vers[0] in '0123456789':
                return (name, vers)

    return (name_string, '')
