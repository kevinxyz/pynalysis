#!/usr/bin/python2.7

import glob
import os
import re
from subprocess import call


REPLACEMENTS = (
    ('\(\s(?P<content>\S.*)\s\)', '(\g<content>)'),
    ('\[\s(?P<content>\S.*)\s\]', '[\g<content>]'),
    ('\{\s(?P<content>\S.*)\s\}', '{\g<content>}'),
    #('(?P<content>.*)\s+$', '\g<content>\n'),  # get rid of trailing spaces
)

PEP8_CMD = 'pep8 --ignore E265,E501,W291,W293'


def clean_line(line):
    for re_pattern, re_dest in REPLACEMENTS:
        line = re.sub(re_pattern, re_dest, line)
    return line


BLANK = '\r\n'

def fix_file(tmp_pyfile, pep8_line):
    global BLANK

    def open_fd():
        return open(tmp_pyfile + '.new', 'w'), open(tmp_pyfile)

    def start_fd(wfd, rfd, num_lines):
        global BLANK
        for i in range(num_lines):
            line = rfd.readline()
            m = re.search(r'([\n\r]+)$', line)
            if m and i == 0 and m.group(1) != BLANK:
                BLANK = m.group(1)  # reset
            wfd.write(line)

    def finish_fd(rfd, wfd):
        while True:
            line = rfd.readline()
            wfd.write(line)
            if not line:
                break
        rfd.close()
        wfd.close()
        call(['mv', tmp_pyfile + '.new', tmp_pyfile])

    # ./fabfile.py:6:1: E302 expected 2 blank lines, found 1
    m = re.search(r':(?P<row>\d+):(?P<col>\d+): E302 expected 2 blank lines'
                  ', found (?P<actual_lines>\d+)', pep8_line)
    if m:
        row, col, actual_lines = map(lambda x: int(x),
                                     m.group('row', 'col', 'actual_lines'))
        wfd, rfd = open_fd()
        start_fd(wfd, rfd, row - 1)
        for _ in range(2 - actual_lines):
            wfd.write(BLANK)
        finish_fd(rfd, wfd)
        return True

    # :124:18: E201 whitespace after '['
    # :413:30: E241 multiple spaces
    # :310:103: E221 multiple spaces before operator
    # :335:37: E222 multiple spaces after operator
    # :1665:122: E251 unexpected spaces around keyword / parameter equals
    # :E703 statement ends with a semicolon
    m = re.search(r':(?P<row>\d+):(?P<col>\d+): E(201|202|203|241|221|222|251|703)',
                  pep8_line)
    if m:
        row, col = map(lambda x: int(x), m.group('row', 'col'))
        wfd, rfd = open_fd()
        start_fd(wfd, rfd, row - 1)
        spaced_line = rfd.readline()
        for i, c in enumerate(spaced_line):
            if i == col - 1:
                continue
            wfd.write(c)
        finish_fd(rfd, wfd)
        return True

    # :128:52: E502 the backslash is redundant between brackets
    m = re.search(r':(?P<row>\d+):(?P<col>\d+): E502', pep8_line)
    if m:
        row, col = map(lambda x: int(x), m.group('row', 'col'))
        wfd, rfd = open_fd()
        start_fd(wfd, rfd, row - 1)
        _line = rfd.readline()
        _line = re.sub(r'\s*\\\s*$', BLANK, _line)
        wfd.write(_line)
        finish_fd(rfd, wfd)
        return True

    # /tmp/./views.py:496:5: E303 too many blank lines (3)
    m = re.search(r':(?P<row>\d+):(?P<col>\d+): E303 too many blank',
                  pep8_line)
    if m:
        row, col = map(lambda x: int(x), m.group('row', 'col'))
        wfd, rfd = open_fd()
        start_fd(wfd, rfd, row - 2)
        rfd.readline()  # skip
        finish_fd(rfd, wfd)
        return True

    # :430:78: E226 missing whitespace around arithmetic operator
    # :208:55: E231 missing whitespace after ','
    # :474:52: E261 at least two spaces before inline comment
    m = re.search(r':(?P<row>\d+):(?P<col>\d+): E(225|226|261)',
                  pep8_line)
    if m:
        row, col = map(lambda x: int(x), m.group('row', 'col'))
        wfd, rfd = open_fd()
        start_fd(wfd, rfd, row - 1)
        spaced_line = rfd.readline()
        for i, c in enumerate(spaced_line):
            if i == col - 1:
                wfd.write(' ')
            wfd.write(c)
        finish_fd(rfd, wfd)
        return True

    # :161:30: E231 missing whitespace after ','
    m = re.search(r':(?P<row>\d+):(?P<col>\d+): E(231)',
                  pep8_line)
    if m:
        row, col = map(lambda x: int(x), m.group('row', 'col'))
        wfd, rfd = open_fd()
        start_fd(wfd, rfd, row - 1)
        spaced_line = rfd.readline()
        for i, c in enumerate(spaced_line):
            if i == col:
                wfd.write(' ')
            wfd.write(c)
        finish_fd(rfd, wfd)
        return True

    # :182:35: E262 inline comment should start with '# '
    m = re.search(r':(?P<row>\d+):(?P<col>\d+): E262', pep8_line)
    if m:
        row, col = map(lambda x: int(x), m.group('row', 'col'))
        wfd, rfd = open_fd()
        start_fd(wfd, rfd, row - 1)
        comment_line = rfd.readline()
        comment_line = re.sub(r'  #+\s*(?P<comment>.*)', '  # \g<comment>',
                              comment_line)
        wfd.write(comment_line)
        finish_fd(rfd, wfd)
        return True


def pep8_fix(pyfile):
    tmp_pyfile = os.path.join('/tmp/', os.path.basename(pyfile))
    call(['cp', pyfile, tmp_pyfile], shell=False)

    tries = 1
    fixed_file = False
    restart = True
    while 1:
        if restart:
            p = os.popen('%s %s' % (PEP8_CMD, tmp_pyfile), 'r')
        _pep8_line = p.readline()
        if not _pep8_line:
            break
        print _pep8_line,
        restart = fix_file(tmp_pyfile, _pep8_line)
        if restart:
            fixed_file = True
            print "Trying #%d" % tries
            tries += 1

    return fixed_file, tmp_pyfile


def traverse(current_path, recursive=True):
    for pyfile in glob.glob(current_path + '/*.py'):
        fixed_file, fixed_filename = pep8_fix(pyfile)
        if fixed_file:
            call(['cp', fixed_filename, pyfile]) #+ '2'])

    if recursive:
        for dirname in [dirname for dirname in glob.glob(current_path + '/*')
                        if os.path.isdir(dirname)]:
            if 'migrations' in dirname:
                continue
            traverse(dirname, recursive)

if __name__ == '__main__':
    traverse('./', recursive=True)
