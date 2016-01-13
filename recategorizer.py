#!/usr/bin/python


import argparse
from collections import Counter, defaultdict
import os
from xml.sax.saxutils import escape

import FoundationPlist


PKGINFO_EXTENSIONS = (".pkginfo", ".plist")


def main():
    args = get_argument_parser().parse_args()
    args.func(args)
    # preferences = FoundationPlist.readPlist(os.path.expanduser(
    #     "~/Library/Preferences/com.github.sheagcraig.build_configurations.plist"))
    # template = preferences.get("munki_template",
    #                            "ManagedInstallsTemplate.mobileconfig")
    # manifests = preferences.get("manifests", [])
    # catalogs = preferences.get("catalogs", [])
    # if manifests and catalogs:
    #     configs = get_permutations(manifests, catalogs)
    #     for config in configs:
    #         output_munki_config(config, args)


def get_argument_parser():
    """Create our argument parser."""
    description = ("Polish Your Munki Categories to a Fine Lustre.")
    parser = argparse.ArgumentParser(description=description)
    subparser = parser.add_subparsers(help="Sub-command help")

    # List arguments
    phelp = ("List all categories present in the repo, and the count of "
             "pkginfo files in each.")
    collect_parser = subparser.add_parser("categories", help=phelp)
    collect_parser.set_defaults(func=categories)

    # Prepare arguments
    phelp = ("List all product names, sorted by category, as a plist. This "
             "command is used to generate the change file used for bulk"
             "recategorization. Products with multiple pkginfo files using "
             "different categories will be listed by the most frequently used "
             "category only.")
    collect_parser = subparser.add_parser("prepare", help=phelp)
    collect_parser.set_defaults(func=prepare)

    # parser.add_argument("", help=""
    #                     "filename")
    # parser.add_argument("-o", "--output_dir",
    #                     help="Directory to write output into.", default=".")
    return parser


def categories(args):
    all_catalog = get_all_catalog()
    all_categories = get_categories(all_catalog)
    categories = Counter(all_categories)
    if "" in categories:
        categories["BLANK CATEGORY"] = categories[""]
        del(categories[""])
    # with open("output.csv", "wb") as output_file:
    #     writer = csv.writer(output_file)
    #     writer.writerows(categories)
    for category in sorted(categories):
        print "{}: {}".format(category.encode("utf-8"), categories[category])


def get_all_catalog():
    munki_repo = get_repo_path()
    all_path = os.path.join(munki_repo, "catalogs", "all")
    return FoundationPlist.readPlist(all_path)


def get_repo_path():
    munkiimport_prefs = get_munkiimport_prefs()
    return munkiimport_prefs.get("repo_path")


def get_munkiimport_prefs():
    return FoundationPlist.readPlist(os.path.expanduser(
        "~/Library/Preferences/com.googlecode.munki.munkiimport.plist"))


def get_categories(all_catalog, filter=None):
    if not filter:
        filter = True
    return [pkginfo.get("category", "NO CATEGORY") for pkginfo in all_catalog
            if filter(pkginfo)]


def prepare(args):
    all_catalog = get_all_catalog()
    names = get_unique_names(all_catalog)
    names_by_category = defaultdict(list)

    output = {}
    with open("recategorizer_help.txt") as ifile:
        help_text = escape(ifile.read())
    output["Comment"] = help_text

    for name in names:
        categories = get_categories(all_catalog, lambda n: n["name"] == name)
        most_frequent_category = Counter(categories).most_common(1)[0][0]
        names_by_category[most_frequent_category].append(name)

    output.update(names_by_category)
    print FoundationPlist.writePlistToString(output)


def get_unique_names(all_catalog):
    return {pkginfo.get("name", "*NO NAME*") for pkginfo in all_catalog}


def build_pkginfo_cache(repo):
    pkginfos = {}
    pkginfo_dir = os.path.join(repo, "pkgsinfo")
    for dirpath, dirnames, filenames in os.walk(pkginfo_dir):
        for file in filter(is_pkginfo, filenames):
            path = os.path.join(dirpath, file)
            try:
                pkginfo_file = FoundationPlist.readPlist(path)
            except FoundationPlist.FoundationPlistException:
                continue

            pkginfos[path] = pkginfo_file

    return pkginfos


def is_pkginfo(candidate):
    return os.path.splitext(candidate)[-1].lower() in PKGINFO_EXTENSIONS


# def get_permutations(manifests, catalogs):
#     return ((manifest, catalog.title()) for manifest in manifests for catalog
#             in catalogs)

# def output_munki_config(config, args):
#     version = args.version
#     output_dir = args.output_dir
#     config_plist = build_munki_config(config)
#     basename = "ManagedInstalls-{}-{}.mobileconfig".format(
#         "-".join(config), version)
#     path = os.path.join(output_dir, basename)
#     write_config_to(config_plist, path)


# def build_munki_config(config_type):
#     plist = FoundationPlist.readPlist("ManagedInstallsTemplate.mobileconfig")
#     plist["PayloadContent"][0]["PayloadContent"]["ManagedInstalls"]["Forced"][0]["mcx_preference_settings"][
#         "ClientIdentifier"] = ( "-".join(config_type))
#     return plist


# def write_config_to(plist, path):
#     try:
#         FoundationPlist.writePlist(plist, os.path.expanduser(path))
#     except FoundationPlist.NSPropertyListWriteException as error:
#         print error.message


if __name__ == "__main__":
    main()
