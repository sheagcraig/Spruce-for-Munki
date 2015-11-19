#!/usr/bin/env python


import csv
import os

import FoundationPlist


def main():
    munkiimport = FoundationPlist.readPlist(os.path.expanduser(
        "~/Library/Preferences/com.googlecode.munki.munkiimport.plist"))
    munki_repo = munkiimport.get("repo_path")
    all_path = os.path.join(munki_repo, "catalogs", "all")
    all_plist = FoundationPlist.readPlist(all_path)
    all_names_and_versions = sorted(
        [(pkginfo["name"].encode("utf-8"),
          pkginfo.get("display_name", pkginfo["name"]).encode("utf-8"),
          pkginfo["version"].encode("utf-8")) for pkginfo in all_plist],
        key=lambda x: x[0])
    with open("output.csv", "wb") as output_file:
        writer = csv.writer(output_file)
        writer.writerows(all_names_and_versions)
    print all_names_and_versions


if __name__ == "__main__":
    main()