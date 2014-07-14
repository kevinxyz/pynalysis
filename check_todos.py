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
check_todo.py --skip=^.idea/,^.git/,^auto/,^chef/
"""
import argparse
from datetime import datetime
import os
import re
import subprocess


Todo_REGEX = re.compile(r'((TODO|FIXME)\((?P<name>[^\)]+)\)(?P<msg1>.*))|'
                        '((TODO|FIXME)[:\s](?P<msg2>.*))')

BLAME_CMDS = (('git status',
               'git blame --show-email -t %s',
               r'\w+ .*\(\<(?P<email>[^\>]+)\>'
               '\s+'
               '(?P<datestamp>\d+)[^\)]+\) '
               '(?P<msg>.*)'),
              (('svn status',
                'svn blame -v %s',
                r'\s+\d+\s+(?P<email>.+)\s+'
                '(?P<datestamp>\d{4}.+ \(.+\d{4}\)) '
                '(?P<msg>.+)')))
BLAME_CMD = None
for _check_cmd, _blame_cmd, _blame_regex in BLAME_CMDS:
    try:
        if subprocess.call(_check_cmd.split(' '),
                           stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE) == 0:
            BLAME_CMD = _blame_cmd
            BLAME_REGEX = re.compile(_blame_regex)
            break
    except OSError as e:
        pass
if not BLAME_CMD:
    raise RuntimeError("Please run this in a git or svn directory")

UNKNOWN = 'UNKNOWN'


try:
    from author_mapping import AUTHOR_MAPPING
except ImportError:
    AUTHOR_MAPPING = {}


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


def get_author_alias(author):
    """
    Todo(kevinx): move mapping function elsewhere
    """
    if author in AUTHOR_MAPPING:
        return AUTHOR_MAPPING[author]
    return author


class Todo():
    def __init__(self, filename, datestamp, name, checkin_name, msg):
        self.filename = filename
        self.datestamp = datestamp
        self.name = name
        self.checkin_name = checkin_name
        self.msg = msg.lstrip(':').lstrip()

    def __str__(self):
        if self.name and self.checkin_name and self.name != self.checkin_name:
            author = "%s->%s" % (self.checkin_name, self.name)
        else:
            author = self.name or self.checkin_name or UNKNOWN
        if self.datestamp.isdigit():
            date = datetime.fromtimestamp(self.datestamp).strftime("%Y-%m-%d")
        else:
            m = re.search(r'(\d{4}\-\d{2}\-\d{2})', self.datestamp)
            # TODO(kevinx): convert this to a printable string
            if m:
                date = m.group(1)
            else:
                date = UNKNOWN
        return "%s %s: TODO(%s): %s" % (
            date, self.filename, author, self.msg)

    def get_author(self):
        return self.name or self.checkin_name or UNKNOWN


def parse_file_and_get_todo_list(file_path):
    """
    Parse a file, then return a list of Todo objects, if any.
    """
    line_to_todo = {}
    line_count = 0
    for line in (open(file_path).read().rstrip()).split("\n"):
        match = Todo_REGEX.search(line)
        if match:
            name = (match and match.group('name')) or None
            name = get_author_alias(name)
            msg = match.group('msg1') or match.group('msg2') or ''
            msg = msg.rstrip()
            line_to_todo[line_count] = Todo(file_path, None, name, None, msg)
        line_count += 1

    if len(line_to_todo) > 0:
        git_blame_output = os.popen(BLAME_CMD % file_path).read().rstrip()
        line_count = 0
        for line in git_blame_output.split("\n"):
            if line_count in line_to_todo:
                matched = BLAME_REGEX.match(line)
                if matched:
                    email, datestamp, _code_line = matched.group(
                        'email', 'datestamp', 'msg')
                    # backfill the checkin author name
                    line_to_todo[line_count].checkin_name = (
                        get_author_alias(email))
                    if datestamp.isdigit():
                        line_to_todo[line_count].datestamp = int(datestamp)
                    else:
                        # TODO(kevinx): convert this to integer
                        line_to_todo[line_count].datestamp = datestamp
                #print "***%s" % line_to_todo[line_count]
            line_count += 1
    return line_to_todo.values()


def print_todos(skip_regex):
    """
    Check Python programs for Todo strings
    """
    author_to_todolist = {}
    for root, _dirs, files in os.walk("./"):
        root = os.path.normpath(root)
        if skip_regex.search(root):
            continue
        for filename in files:
            if (skip_regex.search(filename) or
                not (re.search(r'\.(py|rb|java|pl|sh|sql|r)$', filename)
                     or filename.startswith("Makefile"))):
                continue
            file_path = os.path.join(root, filename)
            todo_list = parse_file_and_get_todo_list(file_path)
            for todo in todo_list:
                name = todo.get_author()
                if name not in author_to_todolist:
                    author_to_todolist[name] = []
                author_to_todolist[name].append(todo)

    author_idx = 0
    for author, todo_list in sorted(author_to_todolist.iteritems()):
        if author_idx > 0:
            print ""
        print "TODO(%s): %s has %d items." % (author, author, len(todo_list))
        for todo in todo_list:
            print todo
        author_idx += 1


def run():
    import sys
    parser = configure_argument_parser()
    options = parser.parse_args(sys.argv[1:])

    if len(options.skip) > 0:
        skip_regex = re.compile("|".join(options.skip.split(',')))
    else:
        skip_regex = re.compile(r"(^.idea|^.git|^auto|check_todos.py)")

    print_todos(skip_regex)


if __name__ == '__main__':
    run()
