#!/usr/bin/env python
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
from collections import defaultdict
from distutils.version import LooseVersion
import csv
import os

import spruce_tools as tools


def run_names(args):
    all_plist = tools.get_all_catalog()
    if args.version:
        report = get_names_and_versions(all_plist)
    else:
        report = tools.get_unique_names(all_plist)

    print_report(report, args.name)


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
        names[pkginfo["name"]].append(LooseVersion(pkginfo["version"]))

    return names


def print_report(report, filter):
    if isinstance(report, dict):
        if filter:
            report = {key: val for key, val in report.items() if filter.upper()
                      in key.upper()}
        for name, versions in sorted(report.items()):
            print name
            for version in sorted(versions):
                print "\t" + str(version)
    else:
        print "\n".join(sorted(item for item in report if filter.upper() in
                               item.upper()))