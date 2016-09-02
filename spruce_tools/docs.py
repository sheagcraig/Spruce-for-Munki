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


import codecs
from collections import defaultdict
from distutils.version import LooseVersion
import os
import sys
from urllib import quote

try:
    import markdown
except ImportError:
    print ("Markdown->html output not supported.")
    print ("Please install the 'markdown' python package with either "
           "`pip install markdown` or `easy_install markdown`.")
    markdown = None

import tools


class Markdown(object):
    """Base class for representing a Markdown document."""

    def __init__(self, text=None):
        """Create a Markdown document tree.

        Note: At this time, there is no protection against putting
        Markdown objects inside of other Markdown objects that they
        contain. This should be avoided, as bad things will happen.

        Args:
            text (str/unicode, optional): Text to populate object.
        """
        super(Markdown, self).__init__()
        self._elements = []
        self.text = text if text else ""

    def append(self, element):
        """Append an element to the end of the document.

        Args:
            element (Markdown): The element to append.

        Raises:
            ValueError if element is not a Markdown subclass.
        """
        if self._test_input_is_markdown(element):
            self._elements.append(element)

    def insert(self, element, index):
        """Insert an element at index.

        Args:
            index (int): Document index to insert.

        Raises:
            ValueError if element is not a Markdown subclass.
            IndexError for invalid index.
            """
        if self._test_input_is_markdown(element):
            self._elements.append(element)

    def render(self):
        """Render Markdown tree to string."""
        result = [self.text + "\n"]
        for element in self._elements:
            result.append(element.render())
        return "\n".join(result)

    def render_to_html(self):
        pass

    def __repr__(self, indent=0):
        """Represent as indented list of contained objects"""
        result = ["{}: {}...".format(unicode(type(self)), self.text[:20])]
        indent += 1
        for element in self._elements:
            result.append("{}{}".format(
                indent * "\t", element.__repr__(indent)))
        return "\n".join(result)

    def __str__(self):
        """Represent as indented list of contained objects"""
        return self.render()

    def __len__(self):
        return len(self.text) + sum(len(element) for element in self._elements)

    def _test_input_is_markdown(self, element):
        """Return true if element is Markdown subclass, else raise."""
        if isinstance(element, Markdown):
            return True
        else:
            raise ValueError("element not a Markdown subclass!")


class Table(Markdown):
    """Represents a Markdown Table based on the GFM extension.

    At this time, do not nest a Table inside a Table header or data row.
    """

    def __init__(self, header=None, rows=None):
        """Instantiate a table with optional data.

        Args:
            header (sequence of strings): Column headers, in order.
            rows (sequence of sequences of strings): Data for table.
                Any missing values will be defaulted to an empty string.
        """
        super(Table, self).__init__()
        self.header = list(header) if header else []
        self.rows = [list(row) for row in rows] if rows else []

    def render(self):
        result = ""
        if self.header:
            max_table_width = max(len(row) for row in self.rows)

            # Pad empty cells.
            if len(self.header) < max_table_width:
                self.header += ["" for _ in xrange(
                    max_table_width - len(self.header))]
            for row in self.rows:
                if len(row) < max_table_width:
                    row += ["" for _ in xrange(max_table_width - len(row))]

            lengths = [3] * max_table_width

            # Determine max width for each cell.
            data = [self.header]
            data += [row for row in self.rows]

            for row in data:
                for cell, index in zip(row, xrange(len(row))):
                    if len(cell) > lengths[index]:
                        lengths[index] = len(cell)

            # Render data.
            formatted_headers = []
            for width, value in zip(lengths, self.header):
                cell = "{0:<{fill}}".format(value, fill=width)
                formatted_headers.append(cell)

            header = self._table_delimit(formatted_headers)
            sep = self._table_delimit("-" * width for width in lengths)

            formatted_data = []
            for row in self.rows:
                formatted_row = []
                for width, value in zip(lengths, row):
                    # TODO: Why did this get in here?
                    #value = unicode(value).encode("utf-8").strip()
                    #cell = "{0:<{fill}}".format(value.strip(), fill=width)
                    cell = u"{0:<{fill}}".format(value.strip(), fill=width)
                    formatted_row.append(cell)
                formatted_data.append(self._table_delimit(formatted_row))
            data = "\n".join(formatted_data)

            result = "\n".join((header, sep, data)) + "\n\n"

        # This is not the best way to handle this.
        # TODO: Break up classes to prevent Table from allowing inserts.
        for element in self._elements:
            result += element.render()

        return result

    def _table_delimit(self, row):
        """Add pipes before, after, and between all elements of row."""
        return u"| {} |".format(" | ".join(row))


def handle_docs(args):
    # TODO: See @homebysix for awesome mockups of future docs.
    if not os.path.isdir(args.outputdir):
        sys.exit("outputdir '{}' does not exist. Exiting.".format(
            args.outputdir))
    repo = tools.get_repo_path()
    pkgsinfo = tools.build_pkginfo_cache(repo)
    output = Markdown("# Items in Munki Repo")
    table_head = ("Name", "Display Name", "Versions Present", "Notes")

    rows = {}
    for name, item in get_item_info(pkgsinfo).items():
        versions = ", ".join("[{}]({})".format(
            ver[0].__str__(), quote(ver[1])) for
            ver in sorted(item["versions"]))
        row = (name, item["display_name"], versions,
               item["notes"].replace("\n", " "))
        rows[name] = row

    sorted_rows = (rows[row] for row in sorted(rows))
    output.append(Table(header=table_head, rows=sorted_rows))

    extension = "html" if args.html else "md"
    if args.html:
        # TODO: This is not a complete html page-create a template to add
        # the markdown output to as the body.
        extensions = ["markdown.extensions.tables"]
        output = markdown.markdown(
            output, extensions=extensions, output_format="html5")

    items_path = os.path.join(args.outputdir, "items.{}".format(extension))
    with codecs.open(items_path, encoding="utf-8", mode="w") as ofile:
        ofile.write(output.render())


def get_item_info(pkgsinfo):
    items = defaultdict(dict)
    for path, pkginfo in pkgsinfo.items():
        item = items[pkginfo.get("name")]
        if "versions" not in item:
            item["versions"] = []
        version = LooseVersion(pkginfo.get("version", "0.0"))
        item["versions"].append((version, path))
        # Update output item with highest version of each product.
        if version == max(ver[0] for ver in item["versions"]):
            keys = ("notes", "display_name")
            for key in keys:
                item[key] = pkginfo.get(key, "")

    return items
