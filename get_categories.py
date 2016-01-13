#!/usr/bin/env python

# Print a sorted list of all pkginfo categories and the count of items
# under each one. No category tag results in "NO CATEGORY", while an
# empty tag results in "BLANK CATEGORY".


import csv
from collections import Counter
import os

import FoundationPlist


def main():
    munkiimport = FoundationPlist.readPlist(os.path.expanduser(
        "~/Library/Preferences/com.googlecode.munki.munkiimport.plist"))
    munki_repo = munkiimport.get("repo_path")
    all_path = os.path.join(munki_repo, "catalogs", "all")
    all_plist = FoundationPlist.readPlist(all_path)
    all_categories = [pkginfo.get("category", "NO CATEGORY") for pkginfo in
                      all_plist]
    categories = Counter(all_categories)
    if "" in categories:
        categories["BLANK CATEGORY"] = categories[""]
        del(categories[""])
    with open("output.csv", "wb") as output_file:
        writer = csv.writer(output_file)
        writer.writerows(categories)
    for category in sorted(categories):
        print "{}: {}".format(category.encode("utf-8"), categories[category])


if __name__ == "__main__":
    main()