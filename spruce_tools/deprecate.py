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


import glob
import os
import shutil
from subprocess import call, Popen, CalledProcessError, PIPE
import sys

from spruce_tools import FoundationPlist
from spruce_tools.repo import Repo, ApplicationVersion
from spruce_tools import report
from spruce_tools import tools


NO_CATEGORY = "*NO CATEGORY*"


def main():
    """Do nothing."""
    pass


def deprecate(args):
    """Handle arguments and execute commands."""
    if args.git and call(["which", "git"]) == 1:
        sys.exit("ERROR: git not found in path.")

    cache = tools.build_pkginfo_cache(tools.get_repo_path())
    repo = Repo(cache)

    removals = get_files_to_remove(args, repo)
    if not removals:
        sys.exit("Nothing to do! Exiting.")

    names = get_names_to_remove(removals, cache)

    removal_type = "archived" if args.archive else "removed"
    print_removals(removals, removal_type)
    import pdb; pdb.set_trace()
    print_manifest_removals(names)
    warn_about_multiple_refs(removals, repo)

    if not args.force:
        response = raw_input("Are you sure you want to continue? (Y|N): ")
        if response.upper() not in ("Y", "YES"):
            sys.exit()

    # TODO: Progress MARK
    if args.archive:
        move_to_archive(removals, args.archive)
    else:
        remove(removals)

    if args.git:
        git_rm(removals)

    remove_names_from_manifests(names)


def get_files_to_remove(args, repo):
    """Build and return a list of files to remove."""
    removals = set()
    # TODO: Refactor
    if args.auto:
        try:
            levels = int(args.auto)
        except ValueError:
            sys.exit("Please provide an integer value for the --auto option.")
        return get_removals_from_auto(levels, repo)
    if args.category:
        removals.update(get_removals_for_categories(args.category, repo))
    if args.name:
        removals.update(get_removals_for_names(args.name, repo))
    if args.plist:
        removals.update(get_removals_from_plist(args.plist, repo))
    return removals


def get_removals_from_auto(level, repo):
    munki_repo = tools.get_repo_path()

    manifest_items = report.get_manifest_items(
        report.get_manifests(munki_repo))
    used_items = repo.get_used_items(
        manifest_items, sys.maxint, ("production",))
    current_items = repo.get_used_items(manifest_items, level, ("production",))

    removals = used_items - current_items

    return removals


def get_removals_for_categories(categories, repo):
    """Get all pkginfo and pkg files to remove by category."""
    return {item for app in repo for item in repo[app] if
            item.pkginfo.get("category") in categories}


def get_removals_for_names(names, repo):
    """Get all pkginfo and pkg files to remove by name."""
    return {item for app in repo for item in repo[app] if item.name in names}


def get_removals_from_plist(path, repo):
    """Get all pkginfo and pkg files to remove from a plist."""
    try:
        data = FoundationPlist.readPlist(path)
    except FoundationPlist.NSPropertyListSerializationException:
        sys.exit("Invalid plist file provided as an argument. Exiting.")

    plist_removals = data.get("removals", [])

    pkgsinfo_prefix = tools.get_pkgsinfo_path()

    removals = set()
    for removal in plist_removals:
        path = removal.get("path")
        if not path:
            continue
        else:
            if pkgsinfo_prefix in path:
                removals.update(version for app in repo for version in
                                repo[app] if version.pkginfo_path == path)
            else:
                removals.add(path)

    return removals


def get_names_to_remove(removals, cache):
    """Return a set of all the 'name' values for pkginfos to remove."""
    # We only want to remove products from manifests if we are removing
    # ALL of that product.

    # Copy the pkginfo cache. You can't use copy.deepcopy on ObjC
    # objects. So we convert to dict (which copies).
    future_cache = dict(cache)
    # Remove all of the planned removals.
    for removal in removals:
        if isinstance(removal, ApplicationVersion):
            if removal.pkginfo_path in future_cache:
                del future_cache[removal.pkginfo_path]
        else:
            if removal in future_cache:
                del future_cache[removal]
    # Make a set of all of the remaining names.
    remaining_names = {future_cache[path].get("name") for path in future_cache}
    # Make a set of all of the names from removals list.
    removal_names = {cache[removal].get("name") for removal in removals if
                     isinstance(removal, basestring) and removal in cache}
    # removal_names = {cache[item].get("name") for removal in removals for item in removal.paths if item in
    #                  cache}
    removal_names.update(removal.name for removal in removals if
                         isinstance(removal, ApplicationVersion))
    # The difference tells us which products we are completely removing.
    names_to_remove = removal_names - remaining_names
    return names_to_remove


def print_removals(removals, removal_type):
    """Pretty print the files to remove."""
    bar = 75 * "-"
    print "Items to be {}".format(removal_type)
    last_name = ""
    app_versions = {item for item in removals if
                    isinstance(item, ApplicationVersion)}
    for item in sorted(app_versions):
        if last_name != item.name:
            print bar
        print "<pkginfo{}> {}".format(" + pkg" if item.pkg_path else "",
                                      str(item))
        last_name = item.name
    for item in sorted(removals - app_versions):
        print bar
        print item

    print


def print_manifest_removals(names):
    """Pretty print the names to remove from manifests."""
    print "Items to be removed from manifests:"
    for item in sorted(names):
        print "\t{}".format(item)

    print


def warn_about_multiple_refs(removals, repo):
    """Alert user about possible pkg removal dependencies."""
    # Check for pkginfo files that are NOT to be removed which reference
    # any pkgs to be removed and warn the user!
    # for path, plist in cache.items():
    #     if (not path in removals and
    #             plist.get("installer_item_location") in removals):
    #         print ("WARNING: Package '{}' is targeted for removal, but has "
    #                "references in pkginfo '{}' which is not targeted for "
    #                "removal.".format(
    #                    plist.get("intaller_item_location"), path))
    pkg_removals = {item.pkg_path for item in removals if item.pkg_path}
    for app in repo:
        for item in repo[app]:
            if (item not in removals and
                    item.pkginfo.get("installer_item_location") in
                    pkg_removals):
                print ("WARNING: Package '{}' is targeted for removal, but has "
                   "references in pkginfo '{}' which is not targeted for "
                   "removal.".format(
                       item.pkginfo.get("installer_item_location"), item.pkginfo_path))


def move_to_archive(removals, archive_path):
    """Move a list of files to an archive folder."""
    pkgs_folder = os.path.join(archive_path, "pkgs")
    pkgsinfo_folder = os.path.join(archive_path, "pkgsinfo")
    for folder in (pkgs_folder, pkgsinfo_folder):
        make_folders(folder)

    repo_prefix = tools.get_repo_path()
    for item in removals:
        if isinstance(item, ApplicationVersion):
            removal_paths = [item.pkginfo_path]
            if item.pkg_path:
                removal_paths.append(os.path.join(tools.get_pkg_path(),
                                                  item.pkg_path))
        else:
            removal_paths = [item]

        for item in removal_paths:
            archive_item = item.replace(
                repo_prefix, archive_path, 1)
            make_folders(os.path.dirname(archive_item))
            try:
                # TODO: Test and remove
                #shutil.move(item, archive_item)
                print "Archived '{}'.".format(item)
            except (IOError, OSError) as err:
                print "Failed to remove item '{}' with error '{}'.".format(
                    item, err.strerror)


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
    # TODO: Add exception handling and progress output from archive func.
    for item in removals:
        if item and os.path.isfile(item):
            try:
                os.remove(item)
            except OSError as error:
                print ("Unable to remove {} with error: {}".format(
                    item, error.message))
        elif item and os.path.isdir(item):
            try:
                shutil.rmtree(item)
            except OSError as error:
                print ("Unable to remove {} with error: {}".format(
                    item, error.message))
        else:
            print "Skipping '{}' as it does not seem to exist.".format(item)


def git_rm(removals):
    """Use git to stage deletions."""
    for removal in removals:
        proc = Popen(["git", "-C", tools.get_repo_path(),
                      "rm", "-r", removal], stdout=PIPE, stderr=PIPE)
        stdout, stderr = proc.communicate()

        if proc.returncode != 0:
            if "did not match any files" in stderr:
                print ("File '{}' is not under version control. "
                       "Skipping.".format(removal))
            else:
                print "git rm failed for {} with error: {}".format(
                    removal, stderr)


def remove_names_from_manifests(names):
    """Remove names from all manifests."""
    if not names:
        return

    # Build a new cache post-removal. We haven't run makecatalogs, so
    # we can't use the catalogs for this task.
    repo_path = tools.get_repo_path()
    manifests_root = os.path.join(repo_path, "manifests")

    cache = tools.build_pkginfo_cache(repo_path)
    remaining_names = {pkginfo.get("name") for pkginfo in cache.values()}
    # Use set arithmetic to remove names that are still active in the
    # repo from our removals set.
    names_to_remove = names - remaining_names

    manifests = get_manifests(manifests_root)
    for manifest_path, manifest in manifests.items():
        remove_names_from_manifest(manifest_path, manifest, names_to_remove)


def get_manifests(directory):
    # TODO: This should probably be a generator! Large repos with client
    # certificates will be completely loaded into memory!
    manifests = {}
    for dirpath, _, filenames in os.walk(directory):
        for filename in filenames:
            path = os.path.join(dirpath, filename)
            try:
                manifest = FoundationPlist.readPlist(path)
            except FoundationPlist.FoundationPlistException:
                print "Error reading manifest {}".format(path)
                continue
            manifests[path] = manifest

    return manifests


def remove_names_from_manifest(manifest_path, manifest, removals):
    keys = ("managed_installs",
            "optional_installs",
            "managed_updates",
            "managed_uninstalls")
    sections = {key: manifest[key] for key in keys if key in manifest}
    if "conditional_items" in manifest:
        sections.update(
            {"conditional_items/{}/{}".format(
                condition["condition"], key): condition[key]
             for condition in manifest["conditional_items"]
             for key in keys if key in condition})

    changed = False

    for section, array in sections.items():
        changes = handle_name_removal(array, removals)
        if changes:
            changed = True
            for change in changes:
                print ("\tRemoved '{}' from section '{}' of manifest"
                       "'{}'").format(change, section, manifest_path)

    if changed:
        FoundationPlist.writePlist(manifest, manifest_path)


def handle_name_removal(array, names_to_remove):
    """Remove names from a manifest.

    Args:
        array (list): The actual manifest array of names.
        names_to_remove (list of str): Names of items to remove if
        found.

    Returns:
        List of removed names.
    """
    removals = []
    changes = []

    for item in array:
        if item in names_to_remove:
            removals.append(item)
        elif (item.startswith(tuple(names_to_remove)) and not
              item.endswith(tuple(names_to_remove))):
            print ("\tDeprecator found item '{}' from section '{}' that may "
                   "match a name to remove, but the length is wrong. "
                   "Please remove manually if required!").format(item, section)
    for item in removals:
        array.remove(item)
        changes.append(item)

    return changes


if __name__ == "__main__":
    main()
