#!/usr/bin/env python


import os

import FoundationPlist


def main():
    munkiimport = FoundationPlist.readPlist(os.path.expanduser(
        "~/Library/Preferences/com.googlecode.munki.munkiimport.plist"))
    munki_repo = munkiimport.get("repo_path")
    all_path = os.path.join(munki_repo, "catalogs", "all")
    all_plist = FoundationPlist.readPlist(all_path)
    all_names = sorted({pkginfo["name"] for pkginfo in all_plist})
    print "\n".join(all_names).encode("utf-8")


if __name__ == "__main__":
    main()