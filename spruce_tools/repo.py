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


from distutils.version import LooseVersion
import os

from robo_print import robo_print, LogLevel
import tools


PKGINFO_EXTENSIONS = (".pkginfo", ".plist")
IGNORED_FILES = ('.DS_Store',)
# Apple uses the IEEE/ISO Megabyte, so we will too.
# (Munki uses Mebibytes).
KILOBYTE = 1000
MEGABYTE = KILOBYTE ** 2
GIGABYTE = KILOBYTE ** 3


class Repo(object):

    def __init__(self, pkgsinfo):
        self.applications = {}
        self.errors = set()
        for path, pkginfo in pkgsinfo.items():
            item = ApplicationVersion(path, pkginfo)
            name = item.name
            if name not in self:
                self[name] = Application(name, (item,))
            else:
                self[name].add(item)

        for app in self.applications.values():
            app.add_dependencies(self)

    def get_used_items(self, manifest_items, num_to_save, catalogs=None):
        used = set()
        for manifest_item in manifest_items:
            # TODO: Add parameter for os version support.
            # Support 10.9-10.12
            for major in xrange(8, 13):
                for minor in xrange(0, 10):
                    test_version = "10.{}.{}".format(major, minor)
                    used = (self.get_used_items_by_os(
                        manifest_item, self, test_version, num_to_save, used,
                        catalogs))

        return used

    def get_used_items_by_os(self, full_name, repo, os_version, keep,
                             used=None, catalogs=None):
        if not used:
            used = set()
        name, version = tools.split_name_from_version(full_name)
        if not name in repo:
            self.errors.add(
                "'{}' does not exist in the repo, but is specified in a "
                "manifest.".format(full_name))
            return used
        else:
            app = repo[name]

        if version:
            if version not in app:
                self.errors.add(
                    "'{}-{}' does not exist in the repo, but is specified in "
                    "a manifest.".format(name, version))
                return used
            else:
                candidates = (app[version],)
        else:
            candidates = app

        count = 0
        test_version = LooseVersion(os_version)

        # Application objects iterate in newest-to-oldest order.
        for item in candidates:
            min_version = LooseVersion(item.min_version or "10.4.0")
            max_version = LooseVersion(item.max_version or "10.12.99")

            if (test_version >= min_version and
                    test_version <= max_version and
                    self.meets_catalog_requirements(item, catalogs)):
                if item in used:
                    count += 1
                    if count == keep:
                        return used
                    continue
                else:
                    used.add(item)
                    count += 1

                for required in item.requires:
                    if isinstance(required, Application):
                        used = self.get_used_items_by_os(
                            required.name, repo, os_version, keep, used)
                    elif required in used:
                        continue
                    else:
                        used = self.get_used_items_by_os(
                            required.name, repo, os_version, keep, used)

                for update in item.updates:
                    if isinstance(update, Application):
                        used = self.get_used_items_by_os(
                            update.name, repo, os_version, keep, used)
                    elif update in used:
                        continue
                    else:
                        used = self.get_used_items_by_os(
                            update.name, repo, os_version, keep, used)

            assert count <= keep
            if count == keep:
                return used

        if len(used) == 0:
            # TODO: Specific OS versions would be helpful, but need to
            # handle this in a way that doesn't massively increase the
            # number of errors.
            self.errors.add(
                "Zero items were found for manifest item '{}' for a "
                "supported OS version.".format(full_name))
        return used

    def meets_catalog_requirements(self, item, catalogs):
        if catalogs:
            return any(
                cat in catalogs for cat in item.pkginfo.get("catalogs", []))
        else:
            return True

    def __getitem__(self, name):
        return self.applications[name]

    def __setitem__(self, name, value):
        self.applications[name] = value

    def __contains__(self, name):
        return name in self.applications


class Application(object):
    """Describes a software item from the Munki repo.

    This object acts as a container for managing instances of the
    ApplicationVersion class.
    """
    def __init__(self, name, app_versions=None):
        self.name = name
        self._app_versions = []
        if app_versions:
            for app_version in app_versions:
                self.add(app_version)

    def __iter__(self):
        """Return an iterator from newest to oldest version."""
        self._app_versions.sort(reverse=True)
        for app_version in self._app_versions:
            yield app_version

    def __len__(self):
        return len(self._app_versions)

    def __repr__(self):
        return "{}:\n{}".format(self.name, "\n".join(
            str(item) for item in self))

    def __getitem__(self, version):
        search = [item for item in self if item.version == version]
        if len(search) == 1:
            result = search[0]
        elif len(search) > 1:
            robo_print("More than one pkg with version '{}'!".format(
                version), LogLevel.WARNING)
            result = search[0]
        else:
            raise KeyError(version)
        return result

    def __contains__(self, version):
        return any(version == item.version for item in self)

    def add(self, app_version):
        if not isinstance(app_version, ApplicationVersion):
            raise ValueError("Unsupported argument type.")
        self._app_versions.append(app_version)
        self._app_versions.sort()

    def add_dependencies(self, repo):
        for version in self._app_versions:
            version.add_dependencies(repo)

    def get_newest(self, num):
        self._app_versions.sort(reverse=True)
        if num > len(self._app_versions):
            num = len(self._app_versions)

        return self._app_versions[0:num]


class ApplicationVersion(object):

    def __init__(self, pkginfo_path, pkginfo):
        self.pkginfo_path = pkginfo_path
        self.pkg_path = pkginfo.get("installer_item_location")
        self.name = pkginfo.get("name")
        self.min_version = pkginfo.get("minimum_os_version")
        self.max_version = pkginfo.get("maximum_os_version")
        self.version = pkginfo.get("version")
        self.pkginfo = pkginfo
        if self.pkg_path:
            # TODO: For now, let it raise an exception if pkg is missing
            size = os.stat(
                os.path.join(tools.get_pkg_path(), self.pkg_path)).st_size
        else:
            size = 0
        self.size = size
        self.requires = []
        self.required_by = []
        self.update_for = []
        self.updates = []
        self.errors = []

    def _human_readable_size(self):
        if self.size >= GIGABYTE:
            size = "{:,.2f}G".format(float(self.size) / GIGABYTE)
        elif self.size < GIGABYTE and self.size >= MEGABYTE:
            size = "{:,.2f}M".format(float(self.size) / MEGABYTE)
        elif self.size < MEGABYTE:
            size = "{:,.2f}K".format(float(self.size) / KILOBYTE)
        return size

    def __repr__(self):
        head_fmt = "{} {} ({} - {}): {}"

        output = head_fmt.format(self.name, self.version, self.min_version,
                                 self.max_version, self._human_readable_size())
        if self.requires:
            output += " Requires: {}".format(len(self.requires))
        if self.update_for:
            output += " update_for: {}".format(len(self.update_for))
        if self.updates:
            output += " Updates: {}".format(len(self.updates))

        return output

    def __cmp__(self, other):
        if self.name < other.name:
            return -1
        elif self.name > other.name:
            return 1
        else:
            version = LooseVersion(self.version)
            other = LooseVersion(other.version)
            if version < other:
                return -1
            elif version == other:
                return 0
            else:
                return 1

    def add_dependencies(self, repo):
        for required_name in self.pkginfo.get("requires", []):
            name, version = tools.split_name_from_version(required_name)
            if name not in repo:
                self.errors.append(
                    "'{}-{}' requires '{}', but there is not an item with that "
                    "name in the repo.".format(self.name, self.version, name))
                continue

            # Item requires a specific version.
            if version:
                if version not in repo[name]:
                    self.errors.append(
                        "'{}-{}' requires '{}-{}', but there is not an item "
                        "with that version.".format(
                            self.name, self.version, name, version))
                    continue
                else:
                    self.requires.append(repo[name][version])
                    repo[name][version].required_by.append(self)
            else:
                self.requires.append(repo[name])
                for item in repo[name]:
                    item.required_by.append(self)

        for update_for_name in self.pkginfo.get("update_for", []):
            name, version = tools.split_name_from_version(update_for_name)
            if name not in repo:
                self.errors.append(
                    "'{}-{}' is an update for '{}', but that item does not "
                    "exist.".format(self.name, self.version, name))
                continue

            # Update is for a specific version.
            if version:
                if version not in repo[name]:
                    self.errors.append(
                        "'{}-{}' is an update for '{}-{}', but there is not "
                        "an item with that version in the repo.".format(
                                   self.name, name, version))
                    continue
                else:
                    repo[name][version].add_update(self)
                    self.update_for.append(repo[name][version])
            else:
                for item in repo[name]:
                    item.add_update(self)
                    self.update_for.append(item)

    def add_update(self, update):
        self.updates.append(update)


