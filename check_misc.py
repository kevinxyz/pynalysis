#!/usr/bin/python2.7

"""
Copyright (C) 2012 KevinX Chang.

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, Inc., 675 Mass Ave, Cambridge MA 02139,
USA; either version 2 of the License, or (at your option) any later
version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.


Usage:
check_check_basic_styling --skip=^.idea/,^.git/,^auto/,^chef/
"""
import argparse
import os
import re
import sys


def configure_argument_parser(parser=argparse.ArgumentParser()):
    """
    param {argparse.ArgumentParser} parser: a parser that we populate
        specific options.
    """
    parser.add_argument('--skip', dest='skip',
                        action='store',
                        help='Directories to skip, separated by commas.',
                        default=[])
    return parser


class FileCheckList:
    # rudimentary file checkers
    max_columns = 'max_columns'
    allow_tab = 'allow_tab'
    allow_empty_trailing_space = 'spaces'
    allow_trailing_backslash = 'allow_trailing_backslash'

    FILE_CHECK_ATTRIBUTES = {
        re.compile(r'\.py$', flags=re.IGNORECASE): {
            allow_trailing_backslash: False,
        },
        re.compile(r'\.java$', flags=re.IGNORECASE): {
            max_columns: 100,
            allow_tab: False,
            allow_empty_trailing_space: False
        },
        re.compile(r'\.r$', flags=re.IGNORECASE): {
            max_columns: 80,
            allow_tab: False,
            allow_empty_trailing_space: False
        },
        re.compile(r'^Makefile.*', flags=re.IGNORECASE): {
            max_columns: 100,
            allow_tab: True,
            allow_empty_trailing_space: False
        },
        re.compile(r'\.sql$', flags=re.IGNORECASE): {
            max_columns: 100,
            allow_tab: False,
            allow_empty_trailing_space: False
        },
        re.compile(r'\.sh$', flags=re.IGNORECASE): {
            max_columns: 80,
            allow_tab: False,
            allow_empty_trailing_space: False
        }
    }


def print_and_get_num_of_errors_in_file(rootpath, filename, attribute_hash):
    """
    Look at each filename and print out reasons for errors.
    """
    max_columns = attribute_hash.get(FileCheckList.max_columns, 80)
    allow_tab = attribute_hash.get(FileCheckList.allow_tab, False)
    allow_empty_trailing_space = (
        attribute_hash.get(FileCheckList.allow_empty_trailing_space), False)
    allow_trailing_backslash = (
        attribute_hash.get(FileCheckList.allow_trailing_backslash, True))

    file_path = os.path.join(rootpath, filename)
    fd = open(file_path)
    line_num = 0

    errors = 0
    for line in fd.readlines():
        line = re.sub(r'[\n\r]+$', '', line)

        line_num += 1
        if not allow_tab and re.search(r'\t', line):
            print("%s:%d: Should not contain tab:" %
                  (file_path, line_num))
            line = re.sub('\t', '<TAB>', line)
            print "  %s" % line
            errors += 1
        space_match = re.search('(\s+)$', line)
        if not allow_empty_trailing_space and space_match:
            print("%s:%d: Should not contain "
                  "trailing space:" %
                  (file_path, line_num))
            line = re.sub('\s+$', '', line) + (
                '_' * len(space_match.group(1)))
            print "  %s <= space" % line
            errors += 1
        if len(line) > max_columns:
            print("%s:%d: Has %d columns (exceeds limit of %d):" %
                  (file_path, line_num, len(line), max_columns))
            line = line[:max_columns - 4]
            print "  %s..." % line
            errors += 1
        if not allow_trailing_backslash:
            no_comment_line = re.sub(r'#.*$', '', line)
            if re.search(r'\\\s*$', line):
                print("%s:%d: Please replace backslash with parenthesis" % (
                    file_path, line_num))
                errors += 1

    return errors


def traverse_files(skip_regex):
    """
    Check Python programs for Todo strings
    """
    errors = 0
    for rootpath, _dirs, files in os.walk("./"):
        rootpath = os.path.normpath(rootpath)
        if skip_regex.search(rootpath):
            continue
        for filename in files:
            for check_regex, attribute_hash in (
                    FileCheckList.FILE_CHECK_ATTRIBUTES.iteritems()):
                match = check_regex.search(filename)
                if match:
                    errors += print_and_get_num_of_errors_in_file(
                        rootpath, filename, attribute_hash)
                    continue

    if errors:
        print "File contains %d errors." % errors
        sys.exit(1)


def run():
    parser = configure_argument_parser()
    options = parser.parse_args(sys.argv[1:])

    if len(options.skip) > 0:
        skip_regex = re.compile("|".join(options.skip.split(',')))
    else:
        skip_regex = re.compile(r"(^.idea|^.git|^auto|check_todos.py)")

    traverse_files(skip_regex)


if __name__ == '__main__':
    run()
