#!/usr/bin/env python


import argparse
from collections import defaultdict
import csv
import os

import munki_helper_tools as tools
import FoundationPlist


def main():
    parser = get_argument_parser()
    args = parser.parse_args()

    all_plist = tools.get_all_catalog()
    if args.version:
        report = get_names_and_versions(all_plist)
    else:
        report = tools.get_unique_names(all_plist)

    print_report(report)


def get_argument_parser():
    """Create our argument parser."""
    description = (
        "Output all unique product names present in the Munki all catalog.")
    parser = argparse.ArgumentParser(description=description)

    phelp = "Show each version of the software per name."
    parser.add_argument("-v", "--version", help=phelp, action="store_true")

    return parser


def get_names_and_versions(all_plist):
    names = defaultdict(list)
    for pkginfo in all_plist:
        names[pkginfo["name"]].append(pkginfo["version"])

    return names


def print_report(report):
    if isinstance(report, dict):
        for name, versions in sorted(report.items()):
            print name
            for version in versions:
                print "\t" + version
    else:
        print "\n".join(sorted(report))


if __name__ == "__main__":
    main()