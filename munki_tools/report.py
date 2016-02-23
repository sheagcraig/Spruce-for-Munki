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


from collections import OrderedDict
from distutils.version import LooseVersion
import os
import plistlib
from xml.parsers.expat import ExpatError

from munki_tools import tools
from munki_tools import FoundationPlist


PKGINFO_EXTENSIONS = (".pkginfo", ".plist")
IGNORED_FILES = ('.DS_Store',)


def main():
    pass


def run_reports(args):
    munkiimport = FoundationPlist.readPlist(os.path.expanduser(
        "~/Library/Preferences/com.googlecode.munki.munkiimport.plist"))
    munki_repo = munkiimport.get("repo_path")
    all_path = os.path.join(munki_repo, "catalogs", "all")
    all_plist = FoundationPlist.readPlist(all_path)
    cache, errors = tools.build_pkginfo_cache_with_errors(munki_repo)

    # TODO: Add sorting to output or reporting.
    # TODO: Need to figure out how to handle domain-specific reports.
    reports = (("Unattended Installs for Testing Pkgsinfo:",
                (in_testing, is_unattended_install)),
               ("Production Pkgsinfo lacking unattended",
                (in_production, is_not_unattended_install)),
               ("force_install set for Production",
                (in_production,
                 lambda x: x.get("force_install_after_date") is not None)),
               ("force_install not set for Testing",
                (in_testing,
                 lambda x: x.get("force_install_after_date") is None)),
               ("Restart Action Configured",
                (lambda x: x.get("RestartAction") is not None,))
               )
    results = {report[0]: get_info(all_plist, report[1], cache) for report in
               reports}
    report_results = OrderedDict(results)

    report_results["Items Not in Any Manifests"] = get_unused_in_manifests(
        cache, munki_repo)
    # TODO: This doesn't account for OS version differences (and
    # possibly others) that can result in a false positive for being
    # "out-of-date"
    # Need to consider the highest version number for each OS version as
    # "current"
    report_results["Out of Date Items in Production"] = get_out_of_date(
        cache, munki_repo)
    report_results["Pkgsinfo With Syntax Errors"] = [errors]
    report_results["Unused Item Disk Usage"] = get_unused_disk_usage(
        report_results, cache)

    if args.plist:
        print FoundationPlist.writePlistToString(report_results)
    else:
        print_output(report_results)


def get_unused_in_manifests(cache, munki_repo):
    manifests = get_manifests(munki_repo)
    used_items = get_used_items(manifests)
    return get_unused_items_info(cache, used_items)


def get_manifests(munki_repo):
    manifest_dir = os.path.join(munki_repo, "manifests")
    manifests = {}
    for dirpath, _, filenames in os.walk(manifest_dir):
        for filename in filenames:
            if filename not in IGNORED_FILES:
                manifest_filename = os.path.join(dirpath, filename)
                manifests[manifest_filename] = FoundationPlist.readPlist(
                    manifest_filename)
    return manifests


def get_used_items(manifests):
    collections = ("managed_installs", "managed_uninstalls",
                   "optional_installs", "managed_updates")
    used_items = set()
    for manifest in manifests:
        for collection in collections:
            items = manifests[manifest].get(collection)
            if items:
                used_items.update(items)
        conditionals = manifests[manifest].get("conditional_items", [])
        for conditional in conditionals:
            for collection in collections:
                items = conditional.get(collection)
                if items:
                    used_items.update(items)
    return used_items


def get_unused_items_info(cache, used_items):
    unused_items = []
    for pkginfo_fname, pkginfo in cache.items():
        if (pkginfo.get("name") not in used_items and
                not pkginfo.get("installer_type") == "apple_update_metadata"):
            size = pkginfo.get("installer_item_size", 0)
            output_size = ("{:,.2f}M".format(float(size) / 1024) if size else
                           "")
            unused_items.append(
                {"name": pkginfo.get("name", ""),
                 "version": pkginfo.get("version", ""),
                 "path": pkginfo_fname,
                 "size": output_size})

    return sorted(unused_items)


def get_out_of_date(cache, munki_repo):
    manifests = get_manifests(munki_repo)
    used_items = get_used_items(manifests)
    return get_out_of_date_info(cache, used_items)


def get_out_of_date_info(cache, used_items):
    out_of_date_items = []
    for pkginfo_fname, pkginfo in cache.items():
        name = pkginfo.get("name")
        if (name in used_items and
            not pkginfo.get("installer_type") == "apple_update_metadata" and
            in_production(pkginfo)):
            size = pkginfo.get("installer_item_size", 0)
            output_size = ("{:,.2f}M".format(float(size) / 1024) if size else
                           "")
            item = {
                "name": name,
                "size": output_size,
                "path": pkginfo_fname,
                "version": pkginfo.get("version", ""),
                "minimum_os_version": pkginfo.get("minimum_os_version", ""),
                "maximum_os_version": pkginfo.get("maximum_os_version", "")}
            out_of_date_items.append(item)

    return sorted(out_of_date_items,
                  key=lambda x: (x["name"], LooseVersion(x["version"])))


def get_unused_disk_usage(report_results, cache):
    unused_size = 0.0
    for item in (report_results["Items Not in Any Manifests"] +
                 report_results["Out of Date Items in Production"]):
        pkginfo = cache[item["path"]]
        size = pkginfo.get("installer_item_size")
        if size:
            unused_size += size

    # Munki sizes are in kilobytes, so convert to true GIGA!
    return [{"Unused files account for": "{:,.2f} gigabytes".format(
        unused_size / (1024 ** 2))}]


def print_output(report_results):
    """Print formatted reports."""
    for report in report_results:
        print "{}:".format(report)
        for item in report_results[report]:
            print "\t" + "-" * 20
            for key, val in item.items():
                print "\t{}: {}".format(key, val)

        print


def print_output_list(report_results):
    for report in sorted(report_results):
        print report
        print_info(report_results[report])
        print


def get_info(all_plist, conditions, cache):
    return sorted([{"name": pkginfo["name"],
                    "version": pkginfo["version"],
                    "path": find_pkginfo_file_in_repo(pkginfo, cache)}
                   for pkginfo in all_plist if
                   all([condition(pkginfo) for condition in conditions])])


def in_testing(pkginfo):
    testing_catalogs = ("development", "testing", "phase1", "phase2",
                        "phase3")
    return any([catalog in pkginfo.get("catalogs") for catalog in
                testing_catalogs])


def in_production(pkginfo):
    return not in_testing(pkginfo)


def is_unattended_install(pkginfo):
    return pkginfo.get("unattended_install") == True


def is_not_unattended_install(pkginfo):
    return pkginfo.get("unattended_install", False) == False


def print_info(info):
    for item in info:
        print "\t" + ", ".join(item).encode("utf-8")
        # print str(item[0]).encode("utf-8")
        # for attribute in item[1:]:
        #     print "\t{}".format(str(attribute)).encode("utf-8")


def find_pkginfo_file_in_repo(pkginfo, pkginfos):
    """Find the pkginfo file that matches the input in the repo."""
    cmp_keys = ("name", "version", "installer_item_location")
    name = pkginfo["name"]
    version = pkginfo["version"]
    installer = pkginfo.get("installer_item_location")
    candidate_keys = (key for key in pkginfos if name in key and version in
                      key)

    for candidate_key in candidate_keys:
        pkginfo_file = pkginfos[candidate_key]
        if all(pkginfo.get(key) == pkginfo_file.get(key) for key in cmp_keys):
            return candidate_key

    # Brute force if we haven't found one yet.
    for pkg_key in pkginfos:
        pkginfo_file = pkginfos[pkg_key]
        if all(pkginfo.get(key) == pkginfo_file.get(key) for key in cmp_keys):
            return pkg_key

    return None


def is_pkginfo(candidate):
    return os.path.splitext(candidate)[-1].lower() in PKGINFO_EXTENSIONS


if __name__ == "__main__":
    main()
