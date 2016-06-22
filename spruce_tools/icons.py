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

"""Report on and optionally remove unused icons."""


from collections import Counter, defaultdict
from functools import partial
import glob
import os
import shutil
import sys
from xml.sax.saxutils import escape

import FoundationPlist
import tools


NO_CATEGORY = "*NO CATEGORY*"


def main():
    pass


def handle_icons(args):
    """Build list of unused icons, and optionally remove/archive."""
    cache = tools.build_pkginfo_cache(tools.get_repo_path())
    unused_icons = get_unused_icons(tools.get_icons_path(), cache)
    if not unused_icons:
        print "No unused icons found."
        sys.exit()

    if not args.delete and not args.archive:
        report_list(unused_icons, "Unused Icons:")
        sys.exit()

    if args.archive:
        method = "archive to {}".format(args.archive)
        remove_icons = partial(move_to_archive, (args.archive))
    else:
        method = "delete"
        remove_icons = remove

    report_list(unused_icons, "Icons to {}:".format(method))

    if not args.force:
        response = raw_input("Are you sure you want to continue? (Y|N): ")
        if response.upper() not in ("Y", "YES"):
            sys.exit()

    remove_icons(unused_icons)


def get_used_icons(pkginfos):
    icons = []
    for pkginfo in pkginfos.values():
        icon = pkginfo.get("icon_name")
        if icon:
            if not os.path.splitext(icon)[1]:
                icon += ".png"
            icons.append(icon)
        else:
            icons.append("{}.png".format(pkginfo["name"]))

    return set(icons)


def get_unused_icons(icon_path, pkginfos):
    """Return a list of paths for unused icons."""
    used_icons = {os.path.join(icon_path, path) for path in
                  get_used_icons(pkginfos)}
    icons = set(get_sub_paths(icon_path))
    return icons - used_icons


def get_sub_paths(icon_path):
    """Return a list of relative paths to all file in icon_path."""
    for dirpath, dirnames, filenames in os.walk(icon_path):
        relative_paths = [os.path.join(dirpath, fname) for fname in filenames]

    return relative_paths


def report_list(items, header="Items:", footer=None):
    """Pretty print a list of items."""
    print header
    for item in sorted(items):
        print "\t{}".format(item)
    if footer:
        print footer
    print


def move_to_archive(archive_path, removals):
    """Move a list of files to an archive folder."""
    icons_folder = os.path.join(archive_path, "icons")
    make_folders(icons_folder)

    repo_prefix = tools.get_repo_path()
    for item in removals:
        archive_item = item.replace(repo_prefix, archive_path, 1)
        print "Archiving icon to: {}".format(archive_item)
        make_folders(os.path.dirname(archive_item))
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
            print "Deleting icon: {}".format(item)
            os.remove(item)
        except OSError as error:
            print ("Unable to remove {} with error: {}".format(
                item, error.message))


if __name__ == "__main__":
    main()
