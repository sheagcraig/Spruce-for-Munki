#!/usr/bin/env python
# Copyright (C) 2016 Shea G Craig
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


"""robo_print.py"""


import sys


ENDC = "\033[0m"

# Global variables.
COLOR_SETTING = True


class LogLevel(object):
    """Specify colors that are used in Terminal output."""
    DEBUG = ("\033[95m", "DEBUG")
    ERROR = ("\033[1;38;5;196m", "ERROR")
    LOG = ("", "")
    REMINDER = ("\033[1;38;5;33m", "REMINDER")
    VERBOSE = ("\033[0m", "")
    WARNING = ("\033[1;38;5;208m", "WARNING")


class OutputMode(object):
    """Manage global output mode state with a singleton."""
    verbose_mode = False  # Use --verbose command-line argument, or hard-code
                          # to "True" here for additional user-facing output.
    debug_mode = False  # Use --debug command-line argument, or hard-code
                        # to "True" here for additional development output.

    @classmethod
    def set_verbose_mode(cls, value):
        """Set the class variable for verbose_mode."""
        if isinstance(value, bool):
            cls.verbose_mode = value
        else:
            raise ValueError

    @classmethod
    def set_debug_mode(cls, value):
        """Set the class variable for debug_mode."""
        if isinstance(value, bool):
            cls.debug_mode = value
        else:
            raise ValueError


def robo_print(message, log_level=LogLevel.LOG, indent=0):
    """Print the specified message in an appropriate color, and only print
    debug output if debug_mode is True.

    Args:
        log_level: LogLevel property for desired loglevel.
        message: String to be printed to output.
    """
    color = log_level[0] if COLOR_SETTING else ""
    indents = indent * " "
    if log_level[1]:
        prefix = "[%s] " % log_level[1]
    else:
        prefix = ""
    suffix = ENDC if COLOR_SETTING else ""

    line = color + indents + prefix + message + suffix

    if log_level in (LogLevel.ERROR, LogLevel.WARNING):
        print_func = _print_stderr
    else:
        print_func = _print_stdout
    printable = (LogLevel.ERROR, LogLevel.REMINDER, LogLevel.WARNING,
                 LogLevel.LOG)
    if ((log_level in printable) or
        (log_level is LogLevel.DEBUG and OutputMode.debug_mode) or
        (log_level is LogLevel.VERBOSE and
         (OutputMode.verbose_mode or OutputMode.debug_mode))):
        print_func(line)


def _print_stderr(txt):
    print >> sys.stderr, txt


def _print_stdout(txt):
    print txt


def reset_term_colors():
    """Ensure terminal colors are normal."""
    sys.stdout.write(ENDC)

