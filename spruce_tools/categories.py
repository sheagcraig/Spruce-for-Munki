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

from spruce_tools import FoundationPlist
import spruce_tools as tools


NO_CATEGORY = "*NO CATEGORY*"


def run_categories(args):
    """Output all present categories and counts of their use."""
    all_catalog = tools.get_all_catalog()
    if args.prepare:
        prepare_categories(args)
    elif not args.category:
        get_categories_and_counts(all_catalog)
    else:
        get_categories_and_files(all_catalog, args.category)


def get_categories_and_counts(all_catalog):
    all_categories = tools.get_categories(all_catalog)
    categories = Counter(all_categories)
    if "" in categories:
        if NO_CATEGORY not in categories:
            categories[NO_CATEGORY] = 0
        categories[NO_CATEGORY] += categories[""]
        del categories[""]
    for category in sorted(categories):
        print "{}: {}".format(category.encode("utf-8"), categories[category])


def get_categories_and_files(all_catalog, categories):
    cache = tools.build_pkginfo_cache(tools.get_repo_path())
    output = defaultdict(list)
    if "*NO CATEGORY*" in categories:
        categories.append("")
        categories.append(None)

    # Output only those pkginfos which are in the requested categories.
    for path, plist in cache.items():
        category = plist.get("category")
        if category in categories:
            output[category].append((plist.get("name"), path))

    for key, val in output.items():
        print "Category: {}".format(key)
        for entry in sorted(val):
            print "\t{}, {}".format(*entry)


def prepare_categories(_):
    """Build a plist of categories and their products."""
    # TODO: There should be a warning or bold the name or something when a
    # product is in multiple categories.
    all_catalog = tools.get_all_catalog()
    names = tools.get_unique_names(all_catalog)
    names_by_category = defaultdict(list)

    output = {}
    help_text_path = os.path.join(os.path.dirname(os.path.realpath(__file__)),
                             "recategorizer_help.txt")
    with open(help_text_path) as ifile:
        help_text = escape(ifile.read())
    output["Comment"] = help_text

    for name in names:
        name_filter = lambda n: n["name"] == name  # pylint: disable=cell-var-from-loop
        categories = tools.get_categories(all_catalog, name_filter)
        most_frequent_category = Counter(categories).most_common(1)[0][0]
        if most_frequent_category == "":
            most_frequent_category = NO_CATEGORY
        names_by_category[most_frequent_category].append(name)

    output.update(names_by_category)
    print FoundationPlist.writePlistToString(output)


def update_categories(args):
    """Update product pkginfo files to reflect specified categories."""
    changes = FoundationPlist.readPlist(os.path.expanduser(args.plist))

    # Remove the comment that we insert into the output of prepare.
    if "Comment" in changes:
        del changes["Comment"]

    products = {product for change_group in changes.values() for product in
                change_group}

    cache = tools.build_pkginfo_cache(tools.get_repo_path())

    changed = False
    # Update only those pkginfos which need changes applied.
    for path, plist in cache.items():
        name = plist.get("name")
        if name in products:
            new_category = get_category_for_name(name, changes)
            if new_category == NO_CATEGORY:
                new_category = ""
            category = plist.get("category")

            if new_category != category:
                plist["category"] = new_category
                FoundationPlist.writePlist(plist, path)
                changed = True
                print "Pkginfo {} category set to {}.".format(
                     path, new_category if new_category else "''")

    if changed:
        print "Please run 'makecatalogs' to rebuild catalogs."


def get_category_for_name(name, changes):
    """Get the desired category for product 'name'."""
    for category in changes:
        if name in changes[category]:
            return category


