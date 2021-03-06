# -*- coding: utf-8 -*-
# jeroen.vanparidon@mpi.nl
import os
import lzma
import argparse
import random
import itertools
from utensils import log_timer
import logging
logging.basicConfig(format='[{levelname}] {message}', style='{', level=logging.INFO)


def get_lines(fhandle):
    """Removes duplicate lines from a file.

    :param fhandle: file handle to get lines from
    :returns: deduplicated lines, number of lines, number of duplicates removed
    """
    lines = fhandle.read().split('\n')
    n_lines = len(lines)
    lines = set(lines)
    n_duplicates = n_lines - len(lines)
    return lines, n_lines, n_duplicates


@log_timer
def dedup_file(in_fname, out_fname):
    """Deduplicates a file line-wise.

    :param in_fname: file to deduplicate
    :param out_fname: filename that deduplicated files will be written to
    :returns: number of lines, number of duplicates removed
    """
    with open(in_fname, 'r') as in_file, open(out_fname, 'w') as out_file:
        lines, n_lines, n_duplicates = get_lines(in_file)
        lines = list(lines)
        random.shuffle(lines)
        out_file.write('\n'.join(lines))
    logging.info(f'deduplicated {in_fname}, removed {n_duplicates} duplicates out of {n_lines} lines')
    return n_lines, n_duplicates


# because of itertools.cycle() this is only pseudorandomized and pseudodeduplicated
# (i.e.: consecutive lines input cannot end up as consecutive in the output
# and up to n_bins duplicates of an item may remain)
# unless your file fits into memory after deduplication (which includes randomization)
@log_timer
def big_dedup_file(in_fname, out_fname, n_bins):
    """Method for line-wise deduplication of files too big to fit in memory.

    :param in_fname: file to deduplicate
    :param out_fname: filename that deduplicated files will be written to
    :param n_bins: number of chunks to split big file into, more bins means less memory use
    """
    filehandles = []
    for i in range(n_bins):
        filehandles.append(open(f'temp{i}.txt', 'w'))
    handle_iter = itertools.cycle(filehandles)
    with open(in_fname, 'r') as in_file:
        for line in in_file:
            next(handle_iter).write(line)
    for filehandle in filehandles:
        filehandle.close()

    with open(out_fname, 'w') as out_file:
        for i in range(n_bins):
            with open(f'temp{i}.txt', 'r') as tempfile:
                # deduplicate
                lines = list(set(tempfile.read().split('\n')))
                random.shuffle(lines)
                out_file.write('\n'.join(lines))
    logging.info(f'pseudodeduplicated {in_fname}, {out_fname} is also pseudorandomized')


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='deduplicate lines in a file')
    argparser.add_argument('filename', help='file to deduplicate')
    argparser.add_argument('--bins', default=1, type=int,
                           help='number of temporary files to use when the input file is too big to fit in memory')
    args = argparser.parse_args()

    path, filename = os.path.split(args.filename)
    if args.bins == 1:
        dedup_file(args.filename, os.path.join(path, 'dedup.' + filename))
    else:
        big_dedup_file(args.filename, os.path.join(path, 'pseudodedup.' + filename), args.bins)
