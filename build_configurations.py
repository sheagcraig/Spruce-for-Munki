#!/usr/bin/python


import argparse
import os

import FoundationPlist


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
                   "configured manifests and catalogs.")
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
