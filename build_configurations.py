#!/usr/bin/python
# Copyright (C) 2015 Shea G Craig
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


import argparse
import os

from munki_tools import FoundationPlist


def main():
    args = get_argument_parser().parse_args()
    preferences = FoundationPlist.readPlist(os.path.expanduser(
        "~/Library/Preferences/com.github.sheagcraig.build_configurations.plist"))
    template = preferences.get("munki_template",
                               "ManagedInstallsTemplate.mobileconfig")
    manifests = preferences.get("manifests", [])
    catalogs = preferences.get("catalogs", [])
    if manifests and catalogs:
        configs = get_permutations(manifests, catalogs)
        for config in configs:
            output_munki_config(config, args)


def get_argument_parser():
    """Create our argument parser."""
    description = ("Build configuration profiles with all permutations of "
                   "configured manifests and catalogs for client identifiers.")
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("version", help="Version to use in mobileconfig "
                        "filename")
    parser.add_argument("-o", "--output_dir",
                        help="Directory to write output into.", default=".")
    return parser


def get_permutations(manifests, catalogs):
    return ((manifest, catalog.title()) for manifest in manifests for catalog
            in catalogs)

def output_munki_config(config, args):
    version = args.version
    output_dir = args.output_dir
    config_plist = build_munki_config(config)
    basename = "ManagedInstalls-{}-{}.mobileconfig".format(
        "-".join(config), version)
    path = os.path.join(output_dir, basename)
    write_config_to(config_plist, path)


def build_munki_config(config_type):
    plist = FoundationPlist.readPlist("ManagedInstallsTemplate.mobileconfig")
    plist["PayloadContent"][0]["PayloadContent"]["ManagedInstalls"]["Forced"][0]["mcx_preference_settings"][
        "ClientIdentifier"] = ( "-".join(config_type))
    return plist


def write_config_to(plist, path):
    try:
        FoundationPlist.writePlist(plist, os.path.expanduser(path))
    except FoundationPlist.NSPropertyListWriteException as error:
        print error.message


if __name__ == "__main__":
    main()
