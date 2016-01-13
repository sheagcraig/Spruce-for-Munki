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
from xml.sax.saxutils import escape

import FoundationPlist
import munki_helper_tools as tools


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
    all_catalog = tools.get_all_catalog()
    all_categories = tools.get_categories(all_catalog)
    categories = Counter(all_categories)
    if "" in categories:
        categories["BLANK CATEGORY"] = categories[""]
        del categories[""]
    for category in sorted(categories):
        print "{}: {}".format(category.encode("utf-8"), categories[category])


def prepare(_):
    """Build a plist of categories and their products."""
    all_catalog = tools.get_all_catalog()
    names = tools.get_unique_names(all_catalog)
    names_by_category = defaultdict(list)

    output = {}
    with open("recategorizer_help.txt") as ifile:
        help_text = escape(ifile.read())
    output["Comment"] = help_text

    for name in names:
        name_filter = lambda n: n["name"] == name  # pylint: disable=cell-var-from-loop
        categories = tools.get_categories(all_catalog, name_filter)
        most_frequent_category = Counter(categories).most_common(1)[0][0]
        names_by_category[most_frequent_category].append(name)

    output.update(names_by_category)
    print FoundationPlist.writePlistToString(output)


if __name__ == "__main__":
    main()
