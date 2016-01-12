#!/usr/bin/env python


from distutils.version import LooseVersion
import os
import plistlib
from xml.parsers.expat import ExpatError

import FoundationPlist


PKGINFO_EXTENSIONS = (".pkginfo", ".plist")


def main():
    munkiimport = FoundationPlist.readPlist(os.path.expanduser(
        "~/Library/Preferences/com.googlecode.munki.munkiimport.plist"))
    munki_repo = munkiimport.get("repo_path")
    all_path = os.path.join(munki_repo, "catalogs", "all")
    all_plist = FoundationPlist.readPlist(all_path)
    cache = build_pkginfo_cache(munki_repo)

    reports = (("Unattended Installs for Testing Pkgsinfo:",
                (in_testing, is_unattended_install)),
               ("Production Pkgsinfo lacking unattended:",
                (in_production, is_not_unattended_install)),
               ("force_install set for Production:",
                (in_production,
                 lambda x: x.get("force_install_after_date") is not None)),
               ("force_install not set for Testing:",
                (in_testing,
                 lambda x: x.get("force_install_after_date") is None)),
               ("Restart Action Configured:",
                (lambda x: x.get("RestartAction") is not None,))
               )
    report_results = {report[0]: get_info(all_plist, report[1], cache) for
                      report in reports}

    report_results["Items Not in Any Manifests"] = get_unused_in_manifests(
        cache, munki_repo)
    # TODO: This doesn't account for OS version differences (and
    # possibly others) that can result in a false positive for being
    # "out-of-date"
    report_results["Out of Date Items in Production"] = get_out_of_date(
        cache, munki_repo)
    print_output(report_results)

    # TODO: Just for testing ATM.
    unused_size = 0.0
    for item in (report_results["Items Not in Any Manifests"] +
                 report_results["Out of Date Items in Production"]):
        pkginfo = cache[item[2]]
        size = pkginfo.get("installer_item_size")
        if size:
            unused_size += size

    # Munki sizes are in kilobytes, so convert to true GIGA!
    print "Unused files account for {:,.2f} gigabytes".format(
        unused_size / (1024 ** 2))


def get_unused_in_manifests(cache, munki_repo):
    manifests = get_manifests(munki_repo)
    used_items = get_used_items(manifests)
    unused_items = get_unused_items_info(cache, used_items)
    return unused_items


def get_out_of_date(cache, munki_repo):
    manifests = get_manifests(munki_repo)
    used_items = get_used_items(manifests)
    unused_items = get_out_of_date_info(cache, used_items)
    return unused_items


def get_manifests(munki_repo):
    manifest_dir = os.path.join(munki_repo, "manifests")
    manifests = {}
    for dirpath, _, filenames in os.walk(manifest_dir):
        for filename in filenames:
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
                (pkginfo.get("name"), pkginfo.get("version"), pkginfo_fname,
                 output_size))

    return sorted(unused_items)


def get_out_of_date_info(cache, used_items):
    candidate_items = {}
    for pkginfo_fname, pkginfo in cache.items():
        name = pkginfo.get("name")
        if (name in used_items and
            not pkginfo.get("installer_type") == "apple_update_metadata" and
            in_production(pkginfo)):
            size = pkginfo.get("installer_item_size", 0)
            output_size = ("{:,.2f}M".format(float(size) / 1024) if size else
                           "")
            if name not in candidate_items:
                candidate_items[name] = []
            candidate_items[name].append(
                (pkginfo.get("name"), pkginfo.get("version"), pkginfo_fname,
                 output_size, pkginfo.get(
                     "minimum_os_version", "NO_MIN_OS_VERS"),
                 pkginfo.get("maximum_os_version", "NO_MAX_OS_VERS")))
    out_of_date_items = []
    for item_name, items in candidate_items.items():
        sorted_items = sorted(items, key=lambda x: LooseVersion(x[1]))
        _ = sorted_items.pop()
        out_of_date_items += sorted_items


    return sorted(out_of_date_items)


def print_output(report_results):
    for report in sorted(report_results):
        print report
        print_info(report_results[report])
        print


def get_info(all_plist, conditions, cache):
    return sorted({(pkginfo["name"], pkginfo["version"],
                    find_pkginfo_file_in_repo(pkginfo, cache)) for pkginfo in
                   all_plist if all([condition(pkginfo) for condition in
                                     conditions])})


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


def build_pkginfo_cache(repo):
    pkginfos = {}
    pkginfo_dir = os.path.join(repo, "pkgsinfo")
    for dirpath, dirnames, filenames in os.walk(pkginfo_dir):
        for file in filter(is_pkginfo, filenames):
            path = os.path.join(dirpath, file)
            try:
                pkginfo_file = plistlib.readPlist(path)
            except ExpatError:
                continue

            pkginfos[path] = pkginfo_file

    return pkginfos


def is_pkginfo(candidate):
    return os.path.splitext(candidate)[-1].lower() in PKGINFO_EXTENSIONS


if __name__ == "__main__":
    main()