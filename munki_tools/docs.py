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

"""Module to build helpful markdown docs from a Munki repo."""


from collections import defaultdict
from distutils.version import LooseVersion

try:
    import markdown
except ImportError:
    print ("Markdown->html output not supported.")
    print ("Please install the 'markdown' python package with either "
           "`pip install markdown` or `easy_install markdown`.")
    markdown = None

import tools


class Markdown(object):
    pass


def handle_docs(args):
    repo = tools.get_repo_path()
    pkgsinfo = tools.build_pkginfo_cache(repo)
    # all_catalog = tools.get_all_catalog()
    output = "# Items in Munki Repo\n"
    output += "| Name | Display Name | Versions Present | Notes |\n"
    output += "| ---- | ------------ | ---------------- | ----- |\n"
    rows = {}
    for name, item in get_item_info(pkgsinfo).items():
        versions = ", ".join(ver.__str__() for ver in sorted(item["versions"]))
        row = u"|{}|{}|{}|{}|\n".format(
            name, item["display_name"], versions,
            item["notes"].replace("\n", " "))
        rows[name] = row
    for row_name in sorted(rows):
        output += rows[row_name]
    print output.encode("utf-8")


def get_item_info(pkgsinfo):
    items = defaultdict(dict)
    for path, pkginfo in pkgsinfo.items():
        item = items[pkginfo.get("name")]
        if "versions" not in item:
            item["versions"] = []
        version = LooseVersion(pkginfo.get("version", "0.0"))
        item["versions"].append(version)
        # Update output item with highest version of each product.
        if version == max(item["versions"]):
            keys = ("notes", "display_name")
            for key in keys:
                item[key] = pkginfo.get(key, "")

    return items
