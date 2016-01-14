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

"""Remove items from a Munki repo, with the option to relocate them
to a deprecated repository."""


import argparse
from collections import Counter, defaultdict
import os
from xml.sax.saxutils import escape

import FoundationPlist
import munki_helper_tools as tools


NO_CATEGORY = "*NO CATEGORY*"


def main():
    """Handle arguments and execute commands."""
    args = get_argument_parser().parse_args()
    cache = tools.build_pkginfo_cache(tools.get_repo_path())

    removals = get_files_to_remove(args, cache)
    if args.archive:
        move_to_archive(removals)
    else:
        remove(removals)


def get_argument_parser():
    """Create our argument parser."""
    description = ("Remove unwanted products from a Munki repo.")
    parser = argparse.ArgumentParser(description=description)

    parser.add_argument_group("Global Arguments")
    phelp = ("Move, rather than delete, pkginfos and pkgs to 'ARCHIVE'. The "
             "original folder structure will be preserved.")
    parser.add_argument("-a", "--archive", help=phelp)
    phelp = "Don't prompt before removal or archiving procedure."
    parser.add_argument("-f", "--force", help=phelp, action="store_true")

    deprecator_parser = parser.add_argument_group("Deprecation Arguments")
    phelp = "Remove all pkginfos and pkgs with category 'CATEGORY'."
    deprecator_parser.add_argument("-c", "--category", help=phelp, nargs="+")
    phelp = "Remove all pkginfos and pkgs with name 'NAME'."
    deprecator_parser.add_argument("-n", "--name", help=phelp, nargs="+")

    return parser


def get_files_to_remove(args, cache):
    """Build and return a list of files to remove."""
    removals = []
    removals += get_removals_for_categories(args.category, cache)
    removals += get_removals_for_names(args.name, cache)
    print removals
    return removals


def get_removals_for_categories(categories, cache):
    """Get all pkginfo and pkg files to remove by category."""
    pkginfo_removals = []
    pkg_removals = []
    pkg_prefix = tools.get_pkg_path()
    for path, plist in cache.items():
        if plist.get("category") in categories:
            pkginfo_removals.append(path)
            if plist.get("installer_item_location"):
                pkg_removals.append(
                    os.path.join(pkg_prefix, plist["installer_item_location"]))

    # Check for pkginfo files that are NOT to be removed which reference
    # any pkgs to be removed and warn the user!
    for path, plist in cache.items():
        if (not path in pkginfo_removals and
                plist.get("installer_item_location") in pkg_removals):
            print ("WARNING: Package '{}' is targeted for removal, but has "
                   "references in pkginfo '{}' which is not targeted for "
                   "removal.".format(
                       plist.get("intaller_item_location"), path))

    return pkginfo_removals + pkg_removals


def get_removals_for_names(names, cache):
    """Get all pkginfo and pkg files to remove by name."""
    return []


def move_to_archive(removals):
    """Move a list of files to an archive folder."""
    pass


def remove(removals):
    """Delete a list of files."""
    pass


# def run_categories(args):
#     """Output all present categories and counts of their use."""
#     all_catalog = tools.get_all_catalog()
#     if not args.category:
#         get_categories_and_counts(all_catalog)
#     else:
#         get_categories_and_files(all_catalog, args.category)


# def get_categories_and_counts(all_catalog):
#     all_categories = tools.get_categories(all_catalog)
#     categories = Counter(all_categories)
#     if "" in categories:
#         if NO_CATEGORY not in categories:
#             categories[NO_CATEGORY] = 0
#         categories[NO_CATEGORY] += categories[""]
#         del categories[""]
#     for category in sorted(categories):
#         print "{}: {}".format(category.encode("utf-8"), categories[category])


# def get_categories_and_files(all_catalog, categories):
#     cache = tools.build_pkginfo_cache(tools.get_repo_path())
#     output = defaultdict(list)

#     # Output only those pkginfos which are in the requested categories.
#     for path, plist in cache.items():
#         category = plist.get("category")
#         if category in categories:
#             output[category].append((plist.get("name"), path))

#     for key, val in output.items():
#         print "Category: {}".format(key)
#         for entry in sorted(val):
#             print "\t{}, {}".format(*entry)


# def prepare(_):
#     """Build a plist of categories and their products."""
#     all_catalog = tools.get_all_catalog()
#     names = tools.get_unique_names(all_catalog)
#     names_by_category = defaultdict(list)

#     output = {}
#     with open("recategorizer_help.txt") as ifile:
#         help_text = escape(ifile.read())
#     output["Comment"] = help_text

#     for name in names:
#         name_filter = lambda n: n["name"] == name  # pylint: disable=cell-var-from-loop
#         categories = tools.get_categories(all_catalog, name_filter)
#         most_frequent_category = Counter(categories).most_common(1)[0][0]
#         if most_frequent_category == "":
#             most_frequent_category = NO_CATEGORY
#         names_by_category[most_frequent_category].append(name)

#     output.update(names_by_category)
#     print FoundationPlist.writePlistToString(output)


# def update(args):
#     """Update product pkginfo files to reflect specified categories."""
#     changes = FoundationPlist.readPlist(os.path.expanduser(args.plist))

#     # Remove the comment that we instert into the output of prepare.
#     if "Comment" in changes:
#         del changes["Comment"]

#     products = {product for change_group in changes.values() for product in
#                 change_group}

#     cache = tools.build_pkginfo_cache(tools.get_repo_path())

#     # Update only those pkginfos which need changes applied.
#     for path, plist in cache.items():
#         name = plist.get("name")
#         if name in products:
#             new_category = get_category_for_name(name, changes)
#             if new_category == NO_CATEGORY:
#                 new_category = ""
#             category = plist.get("category")

#             if new_category != category:
#                 plist["category"] = new_category
#                 FoundationPlist.writePlist(plist, path)
#                 print "Pkginfo {} category set to {}.".format(
#                      path, new_category if new_category else "''")


# def get_category_for_name(name, changes):
#     """Get the desired category for product 'name'."""
#     for category in changes:
#         if name in changes[category]:
#             return category


if __name__ == "__main__":
    main()
