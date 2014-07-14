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
check_pylint.py --recursive --skip=^auto
"""
import re
import argparse
import os
import glob
# TODO(kevinx): move the two imports into a common sharable module.
from check_todos import get_author_alias, BLAME_CMD, BLAME_REGEX


PYLINT_SCORE_REGEX = re.compile(r'Your code has been rated at '
                                '(\-?\d+(\.\d+)?)')


def configure_argument_parser(parser=argparse.ArgumentParser()):
    """
    param {argparse.ArgumentParser} parser: a parser that we populate
        specific options.
    """
    parser.add_argument('--recursive', dest='recursive',
                        action='store_true',
                        help='look into directories recursively',
                        default=False)
    parser.add_argument('--skip', dest='skip',
                        action='store',
                        help='directories to skip', default=[])
    parser.add_argument('--rcfile', dest='pylint_rcfile',
                        action='store',
                        type=str,
                        help='Pylint rcfile', default=None)
    parser.add_argument('--cmd', dest='cmd',
                        action='store_true',
                        help='Output the command line', default=False)
    parser.add_argument('--authors', dest='authors',
                        nargs='*',
                        help='[optional] Only output these authors')
    return parser


class Info(object):
    """
    Base container that holds line and author statistics.
    """
    def __init__(self, name, authors):
        self.name = name
        self.authors = authors
        self.line_count = 0
        self.author_line_count = {}
        self.sum_score = 0

    def add_line_count(self, author, line_count, score=None):
        self.line_count += line_count
        if author not in self.author_line_count:
            self.author_line_count[author] = line_count
        else:
            self.author_line_count[author] += line_count


class AuthorInfo(Info):
    """
    Container for author statistics.
    """
    def add_line_count(self, author, line_count, score):
        super(AuthorInfo, self).add_line_count(author, line_count)
        self.sum_score += score

    def __str__(self):
        if self.authors and self.name not in self.authors:
            return ""

        if self.line_count:
            avg_score = self.sum_score / self.line_count
        else:
            avg_score = None
        # return author information
        return ("{author_name} scores {avg_score:.2f} ({lines} lines)".format(
            author_name=self.name, avg_score=avg_score, lines=self.line_count))


class FilePathInfo(Info):
    """
    Container for file or path statistics. Generates file/path score and
    the authors' contributions.
    """
    def add_line_count(self, author, line_count, score):
        super(FilePathInfo, self).add_line_count(author, line_count)
        self.sum_score += score

    def __str__(self):
        if (self.authors and
                not set(self.authors).intersection(
                    self.author_line_count.keys())):
            return ""

        buff = []
        # return the general file information
        if self.line_count:
            avg_score = self.sum_score / self.line_count
        else:
            avg_score = None
        buff.append("{filename} scores {avg_score:.2f} "
                    "with {lines} lines".format(filename=self.name,
                                                avg_score=avg_score,
                                                lines=self.line_count))
        # return the breakdown of author contribution to this file
        for author_name, line_count in self.author_line_count.iteritems():
            if self.authors and author_name not in self.authors:
                continue
            buff.append("  {author_name} wrote {line_count} lines".format(
                author_name=author_name, line_count=line_count))
        return "\n".join(buff)


class InfoContainer(object):
    """ Root container """
    everyone = '<everyone>'

    def __init__(self, authors):
        # mapping of author to AuthorInfo objects
        self.authorinfo = {self.everyone: AuthorInfo(self.everyone, authors)}
        # mapping of file/path to FilePathInfo objects
        self.fileinfo = {}
        self.pathinfo = {}
        self.authors = authors  # only output these authors

    def __str__(self):
        sortfunc = lambda x: x[0].lower()
        buff = ["File Statistics:"]
        for _, fileinfo in sorted(self.fileinfo.iteritems(), key=sortfunc):
            output = str(fileinfo)
            if output:
                buff.append(output)

        buff.append("")
        buff.append("Path Summary:")
        for _, pathinfo in sorted(self.pathinfo.iteritems(), key=sortfunc):
            output = str(pathinfo)
            if output:
                buff.append(output)

        buff.append("")
        buff.append("Author Summary:")
        for _, authorinfo in sorted(self.authorinfo.iteritems(), key=sortfunc):
            output = str(authorinfo)
            if output:
                buff.append(output)

        return "\n".join(buff)

    def add_score(self, filename, author, line_count, score=None):
        """
        Given an email and a score, aggregate scores.
        """
        if filename not in self.fileinfo:
            self.fileinfo[filename] = FilePathInfo(filename, self.authors)
        self.fileinfo[filename].add_line_count(author, line_count, score)

        path = re.sub(r'/.+', '', filename)
        if path not in self.pathinfo:
            self.pathinfo[path] = FilePathInfo(path, self.authors)
        self.pathinfo[path].add_line_count(author, line_count, score)

        if author not in self.authorinfo:
            self.authorinfo[author] = AuthorInfo(author, self.authors)
        self.authorinfo[author].add_line_count(author, line_count, score)

        # total count of everyone (complete summary)
        self.authorinfo[self.everyone].add_line_count(
            author, line_count, score)


def aggregate_pylint_scores(rootinfo, current_path, recursive, skip_regex,
                            pylint_rcfile=None,
                            output_pylint_cmd=False):
    """
    Run Pylint and 'git blame', gather score, and return scores.
    """
    for pyfile in glob.glob(current_path + '/*.py'):
        pyfile = pyfile.replace('./', '')
        if skip_regex.search(pyfile):
            continue
        cmd = 'pylint --rcfile=%s %s' % (pylint_rcfile, pyfile)
        if output_pylint_cmd:
            print cmd
            continue
        pylint_output = os.popen(cmd).read().rstrip()
        score = None
        for line in pylint_output.split("\n"):
            matched = PYLINT_SCORE_REGEX.match(line)
            if matched:
                score = float(matched.group(1))
                if score < 0:
                    score = -0.01

        if not score:
            print "Error, no score: %s" % pyfile
            continue
        git_blame_output = os.popen(BLAME_CMD % pyfile).read().rstrip()
        for line in git_blame_output.split("\n"):
            matched = BLAME_REGEX.match(line)
            if matched:
                email, code_line = matched.group('email', 'msg')
                if not code_line:
                    continue
                email = get_author_alias(email)
                rootinfo.add_score(pyfile, email, 1, score)

    if recursive:
        for dirname in [dirname for dirname in glob.glob(current_path + '/*')
                        if os.path.isdir(dirname)]:
            if skip_regex.search(dirname):
                continue
            aggregate_pylint_scores(
                rootinfo,
                dirname,
                recursive,
                skip_regex,
                pylint_rcfile=pylint_rcfile,
                output_pylint_cmd=output_pylint_cmd)


def run():
    import sys
    parser = configure_argument_parser()
    options = parser.parse_args(sys.argv[1:])

    if len(options.skip) > 0:
        skip_regex = re.compile("|".join(options.skip.split(',')))
    else:
        # dummy placeholder to match nothing
        skip_regex = re.compile('\.svn|\.git')

    rootinfo = InfoContainer(options.authors)
    aggregate_pylint_scores(
        rootinfo,
        '.',
        options.recursive,
        skip_regex,
        pylint_rcfile=options.pylint_rcfile,
        output_pylint_cmd=options.cmd)

    if not options.cmd:
        print(rootinfo)


if __name__ == '__main__':
    run()
