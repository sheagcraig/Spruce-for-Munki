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

"""Report on and mass-edit the categories used to classify software
on a Munki repository.
"""


import argparse
from collections import Counter, defaultdict
import os
from xml.sax.saxutils import escape

import FoundationPlist


PKGINFO_EXTENSIONS = (".pkginfo", ".plist")


def main():
    """Handle arguments and execute commands."""
    args = get_argument_parser().parse_args()
    args.func(args)


def get_argument_parser():
    """Create our argument parser."""
    description = ("Polish Your Munki Categories to a Fine Lustre.")
    parser = argparse.ArgumentParser(description=description)
    subparser = parser.add_subparsers(help="Sub-command help")

    # List arguments
    phelp = ("List all categories present in the repo, and the count of "
             "pkginfo files in each.")
    collect_parser = subparser.add_parser("categories", help=phelp)
    collect_parser.set_defaults(func=run_categories)

    # Prepare arguments
    phelp = ("List all product names, sorted by category, as a plist. This "
             "command is used to generate the change file used for bulk"
             "recategorization. Products with multiple pkginfo files using "
             "different categories will be listed by the most frequently used "
             "category only.")
    collect_parser = subparser.add_parser("prepare", help=phelp)
    collect_parser.set_defaults(func=prepare)

    return parser


def run_categories(_):
    """Output all present categories and counts of their use."""
    all_catalog = get_all_catalog()
    all_categories = get_categories(all_catalog)
    categories = Counter(all_categories)
    if "" in categories:
        categories["BLANK CATEGORY"] = categories[""]
        del categories[""]
    for category in sorted(categories):
        print "{}: {}".format(category.encode("utf-8"), categories[category])


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
    return FoundationPlist.readPlist(os.path.expanduser(
        "~/Library/Preferences/com.googlecode.munki.munkiimport.plist"))


def get_categories(all_catalog, filter_func=lambda x: True):
    """Return a list of the category for each pkginfo in the repo."""
    return [pkginfo.get("category", "NO CATEGORY") for pkginfo in all_catalog
            if filter_func(pkginfo)]


def prepare(_):
    """Build a plist of categories and their products."""
    all_catalog = get_all_catalog()
    names = get_unique_names(all_catalog)
    names_by_category = defaultdict(list)

    output = {}
    with open("recategorizer_help.txt") as ifile:
        help_text = escape(ifile.read())
    output["Comment"] = help_text

    for name in names:
        name_filter = lambda n: n["name"] == name  # pylint: disable=cell-var-from-loop
        categories = get_categories(all_catalog, name_filter)
        most_frequent_category = Counter(categories).most_common(1)[0][0]
        names_by_category[most_frequent_category].append(name)

    output.update(names_by_category)
    print FoundationPlist.writePlistToString(output)


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


if __name__ == "__main__":
    main()
