# Spruce for Munki Change Log

All notable changes to this project will be documented in this file. This project adheres to [Semantic Versioning](http://semver.org/).


## [Unreleased][unreleased]

## [0.3.0] - 2016-09-02 - Klokov

### Added
- Added `docs` verb in very proof-of-concept form. Just outputs an items page at this time.
- Added descriptions to reports to make them more understandable without digging through the code.
- Added `deprecate --auto` option (argument specifies the number of items to keep).
- Added interactive preference configuration if missing.
- More!

### Changed
- Overhaul of report and deprecate output.
- Rewrite of deprecate and out-of-date Report code for determining dependencies and usage.

### Fixed
- Better error-handling around unmounted munki repo, and incorrect, missing, or incomplete prefs.
- More elegantly exit if user CTRL-C's.

## [0.2.0] - 2014-06-18

### Added
- Initial release.
- Out of Date items report ignores non-production catalog stuff.
- Out of Date items report takes into account update_for, and requires items as well.
- Orphaned package report. Spruce had a missing installer report; this is the inverse of that: packages (or other files) that are not referred to by any pkginfo file.
- deprecate can now use git rm to further speed up removal or archiving of unwanted items.
- deprecate can now remove anything with a path key in the removals plist (orphaned packages, for example).
- Added the spruce emoji to stdout reports.
- Added docs verb to (start) generating markdown or HTML documentation based on your Munki repo.
- name verb now allows you to provide an optional name argument to search for items that have that name as a substring.
- More error handling.

[unreleased]: https://github.com/sheagcraig/Spruce-For-Munki/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/sheagcraig/Spruce-For-Munki/compare/v0.2.0...v0.3.0
