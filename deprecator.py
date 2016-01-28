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
import glob
import os
import shutil
import sys
from xml.sax.saxutils import escape

import FoundationPlist
import munki_helper_tools as tools


NO_CATEGORY = "*NO CATEGORY*"


def main():
    """Handle arguments and execute commands."""
    args = get_argument_parser().parse_args()
    cache = tools.build_pkginfo_cache(tools.get_repo_path())

    removals = get_files_to_remove(args, cache)
    names = get_names_to_remove(removals, cache)

    removal_type = "archived" if args.archive else "removed"
    print_removals(removals, removal_type)
    warn_about_multiple_pkg_references(removals, cache)

    if not args.force:
        response = raw_input("Are you sure you want to continue? (Y|N): ")
        if response.upper() not in ("Y", "YES"):
            sys.exit()

    if args.archive:
        move_to_archive(removals, args.archive)
    else:
        remove(removals)

    remove_names_from_manifests(names)


def get_argument_parser():
    """Create our argument parser."""
    description = (
        "Remove unwanted products from a Munki repo. Pkg and pkginfo files "
        "will be removed, or optionally can be archived in an archive repo. "
        "All products to be completely removed will then have their names "
        "removed from all manifests.")
    parser = argparse.ArgumentParser(description=description)

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
    if args.category:
        removals += get_removals_for_categories(args.category, cache)
    if args.name:
        removals += get_removals_for_names(args.name, cache)
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

    return pkginfo_removals + pkg_removals


def get_removals_for_names(names, cache):
    """Get all pkginfo and pkg files to remove by name."""
    pkginfo_removals = []
    pkg_removals = []
    pkg_prefix = tools.get_pkg_path()
    for path, plist in cache.items():
        if plist.get("name") in names:
            pkginfo_removals.append(path)
            if plist.get("installer_item_location"):
                pkg_removals.append(
                    os.path.join(pkg_prefix, plist["installer_item_location"]))

    return pkginfo_removals + pkg_removals


def get_names_to_remove(removals, cache):
    """Return a set of all the 'name' values for pkginfos to remove."""
    return {cache[path].get("name") for path in removals if path in cache}


def print_removals(removals, removal_type):
    """Pretty print the files to remove."""
    print "Items to be {}".format(removal_type)
    for item in sorted(removals):
        print "\t{}".format(item)

    print


def warn_about_multiple_pkg_references(removals, cache):
    """Alert user about possible pkg removal dependencies."""
    # Check for pkginfo files that are NOT to be removed which reference
    # any pkgs to be removed and warn the user!
    for path, plist in cache.items():
        if (not path in removals and
                plist.get("installer_item_location") in removals):
            print ("WARNING: Package '{}' is targeted for removal, but has "
                   "references in pkginfo '{}' which is not targeted for "
                   "removal.".format(
                       plist.get("intaller_item_location"), path))


def move_to_archive(removals, archive_path):
    """Move a list of files to an archive folder."""
    pkgs_folder = os.path.join(archive_path, "pkgs")
    pkgsinfo_folder = os.path.join(archive_path, "pkgsinfo")
    for folder in (pkgs_folder, pkgsinfo_folder):
        make_folders(folder)

    repo_prefix = tools.get_repo_path()
    for item in removals:
        archive_item = item.replace(repo_prefix, archive_path, 1)
        make_folders(os.path.dirname(archive_item))
        # TODO: Disabled until GO TIME.
        shutil.move(item, archive_item)


def make_folders(folder):
    """Make all folders in path that are missing."""
    if not os.path.exists(folder):
        try:
            os.makedirs(folder)
        except OSError:
            print ("Failed to create archive directory {}! "
                    "Quitting.".format(folder))
            sys.exit(1)


def remove(removals):
    """Delete a list of files."""
    for item in removals:
        try:
            os.remove(item)
        except OSError as error:
            print ("Unable to remove {} with error: {}".format(
                item, error.message))


def remove_names_from_manifests(names):
    """Remove names from all manifests."""
    # Build a new cache post-removal. We haven't run makecatalogs, so
    # we can't use the catalogs for this task.
    repo_path = tools.get_repo_path()
    manifests_path = os.path.join(repo_path, "manifests")

    cache = tools.build_pkginfo_cache(repo_path)
    remaining_names = {pkginfo.get("name") for pkginfo in cache.values()}
    # Use set arithmetic to remove names that are still active in the
    # repo from our removals set.
    names_to_remove = names - remaining_names
    import pdb;pdb.set_trace()

    keys = ("managed_installs", "optional_installs", "managed_updates",
            "managed_uninstalls")

    for manifest_path in glob.glob(os.path.join(manifests_path, "*")):
        changed = False
        try:
            manifest = FoundationPlist.readPlist(manifest_path)
        except FoundationPlist.FoundationPlistException:
            print "Error reading manifest {}".format(manifest_path)
            next
        print "Looking for name removals in {}".format(manifest_path)

        for key in keys:
            product_array = manifest.get(key)
            if product_array:
                changes = handle_name_removal(product_array, names_to_remove,
                                              key)
                if changes:
                    changed = True

        # TODO: This can be refactored out as it's a duplicate, just
        # one layer deeper in the manifest.
        if "conditional_items" in manifest:
            conditionals = manifest["conditional_items"]
            for conditional in conditionals:
                for key in keys:
                    product_array = conditional.get(key)
                    if product_array:
                        changes = handle_name_removal(
                            product_array, names_to_remove,
                            "conditional " + key)
                        if changes:
                            changed = True

        if changed:
            FoundationPlist.writePlist(manifest, manifest_path)


def handle_name_removal(product_array, names_to_remove, key):
    removals = []
    changes = False
    for item in product_array:
        if item in names_to_remove:
            print "\tRemoving {} from {}".format(item, key)
            removals.append(item)
        elif (item.startswith(tuple(names_to_remove)) and not
                item.endswith(tuple(names_to_remove))):
            print ("\tDeprecator found item {} that may match a "
                    "name to remove, but the length is wrong. "
                    "Please remove manually if required!").format(
                        item)
    for item in removals:
        product_array.remove(item)
        changes = True

    return changes


if __name__ == "__main__":
    main()
