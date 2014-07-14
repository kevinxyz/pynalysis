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


PEP8 (http://www.python.org/dev/peps/pep-0008/) is the most basic styling
for Python. It is akin to the English style guide for punctuation,
capitalization, and spelling rules. It does not address higher level concepts
such as object oriented design/patterns/structures.

Usage:
check_pep8.py --recursive --skip=^auto,^crawler,^chef
"""
import argparse
import glob
import os
import re
from sys import maxint

__author__ = 'kevinx'


def configure_argument_parser(parser=argparse.ArgumentParser()):
    """
    param {argparse.ArgumentParser} parser: a parser that we populate
        specific options.
    """
    parser.add_argument('--recursive', dest='recursive',
                        action='store_true',
                        help='look into directories recursively',
                        default=False)
    parser.add_argument('--error_threshold', dest='error_threshold',
                        action='store',
                        help='allowable ratio of lines:errors', default='0:1')
    parser.add_argument('--skip', dest='skip',
                        action='store',
                        help='directories to skip', default=[])
    return parser


def count_lines_in_code(pyfile):
    line_count = 0
    fd = open(pyfile)
    for line in fd.readlines():
        line = re.sub(r'#.*', '', line)
        line = re.sub('\s+', '', line)
        if line:
            line_count += 1
    fd.close()
    return line_count


def check_for_pep8_error(current_path, recursive, error_threshold, skip_regex):
    """
    Check Python programs, see if they reach the threshold of
    errors:lines. If so, return True
    """
    has_error = False
    for pyfile in glob.glob(current_path + '/*.py'):
        pyfile = pyfile.replace('./', '')
        if skip_regex.search(pyfile):
            continue
        pep8_output = os.popen('pep8 %s' % pyfile).read().rstrip()
        if pep8_output:
            lines_of_code = count_lines_in_code(pyfile)
            if lines_of_code == 0:
                error_ratio = maxint
            else:
                error_ratio = (float(len(pep8_output.split("\n"))) /
                               lines_of_code)
            if error_ratio > error_threshold:
                has_error = True
                print "TOO MANY ERRORS: " + pyfile
            print pep8_output

    if recursive:
        for dir in [dir for dir in glob.glob(current_path + '/*')
                    if os.path.isdir(dir)]:
            if skip_regex.search(dir):
                continue
            if check_for_pep8_error(dir, True, error_threshold, skip_regex):
                has_error = True

    return has_error


def run():
    import sys
    parser = configure_argument_parser()
    options = parser.parse_args(sys.argv[1:])

    error_lines, good_lines = options.error_threshold.split(':')
    if len(options.skip) > 0:
        skip_regex = re.compile("|".join(options.skip.split(',')))
    else:
        # dummy placeholder to match nothing
        skip_regex = re.compile('____')

    if check_for_pep8_error('.',
                            options.recursive,
                            float(error_lines) / float(good_lines),
                            skip_regex):
        sys.exit(1)


if __name__ == '__main__':
    run()
