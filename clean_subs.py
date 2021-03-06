# -*- coding: utf-8 -*-
# jeroen.vanparidon@mpi.nl
import os
import zipfile
import argparse
import re
from utensils import log_timer
from lxml import etree
import logging
logging.basicConfig(format='[{levelname}] {message}', style='{', level=logging.INFO)


def strip_upos(tree):
    # format [word]_[POS tag]
    stripped = []
    for node in tree.iter():
        if node.tag == 's':
            stripped.append('\n')
        if node.tag == 'w':
            stripped.append(f'{node.text}_{node.get("upos")} ')
    return u''.join(stripped)


def strip_lemma(tree):
    # format [lemmatized word]
    stripped = []
    for node in tree.iter():
        if node.tag == 's':
            stripped.append('\n')
        if node.tag == 'w':
            stripped.append(f'{node.get("lemma")}_{node.get("upos")} ')
    return u''.join(stripped)


def strip_txt(tree):
    """XML stripper method for raw text.

    :param tree: lxml parse tree
    :returns: raw text
    """
    # format [sentence]
    for node in tree.iter():
        if node.tag == 'meta':
            tree.remove(node)
    return etree.tostring(tree, encoding=str, method='text')


def strip_viz(tree):
    # format [timestamp in ms] [sentence]
    stripped = []
    for node in tree.iter():
        if node.tag == 's':
            children = list(node)
            if len(children) > 0:
                if children[0].tag == 'time':
                    timestamp = children[0].get('value').replace(':', '').replace(',', '.')
                    txt = etree.tostring(node, encoding=str, method='text').replace('\n', '')
                    stripped.append(f'[{timestamp}] {txt}')
    return u'\n'.join(stripped)


def strip_xml(text, xmlparser, ioformat='txt'):
    """Method for selecting xml stripper based on desired input/output format.

    :param text: text to be stripped
    :param xmlparser: lxml parser object
    :param ioformat: desired input/output format
    :returns: stripped text
    """
    tree = etree.fromstring(text, xmlparser)
    if ioformat == 'upos':
        return strip_upos(tree)
    elif ioformat == 'lemma':
        return strip_lemma(tree)
    elif ioformat == 'txt':
        return strip_txt(tree)
    elif ioformat == 'viz':
        return strip_viz(tree)


@log_timer
def strip_archive(lang, ioformat='txt', years=(1900, 2050)):
    """Method for xml-stripping an OpenSubtitles archive in zip format.

    Writes the xml-stripped archive directly to a zip format file.

    :param lang: archive language
    :param ioformat: desired input/output format
    :param years: specific years to include in the output
    """
    read_zip = zipfile.ZipFile(f'corpora/{lang}.zip', 'r')
    write_zip = zipfile.ZipFile(f'corpora/{lang}_stripped.zip', 'a')
    if ioformat == 'txt':
        dirpath = 'OpenSubtitles/raw'
    elif ioformat in ['upos', 'lemma']:
        dirpath = 'OpenSubtitles/parsed'
    filepaths = []
    for filepath in read_zip.namelist():
        if filepath.endswith('xml'):
            if filepath.startswith(os.path.join(dirpath, lang)):
                if int(filepath.split('/')[3]) in range(*years):
                    filepaths.append(filepath)
    logging.info(f'stripping xml from {len(filepaths)} subtitles in {lang}')
    # XML parser recover option is needed to deal with malformed XML in subs
    xmlparser = etree.XMLParser(recover=True, encoding='utf-8')
    for filepath in sorted(filepaths):
        write_zip.writestr(filepath.replace('xml', ioformat),
                           strip_xml(read_zip.open(filepath).read(), xmlparser, ioformat))


def strip_punctuation(txt, ioformat='txt'):
    """Method for stripping punctuation from a text corpus.

    :param txt: text to be stripped of punctuation
    :param ioformat: desired input/output format
    :returns: punctuation-stripped text
    """
    regeces = [
        (r'<.*?>', ''),  # strip other xml tags
        (r'http.*?(?:[\s\n\]]|$)', ''),  # strip links
        (r'\s\(.*?\)', ''),  # remove everything in parentheses
        (r'([^\s]{2,})[\.\!\?\:\;]+?[\s\n]|$', '\\1\n'),  # break sentences at periods
        (r"[-–—/']", ' '),  # replace hyphens, apostrophes and slashes with spaces
        (r'\s*\n\s*', '\n'),  # strip empty lines and lines containing whitespace
        (r'\s{2,}', ' '),  # strip excessive spaces
    ]
    for regec in regeces:
        pattern = re.compile(regec[0], re.IGNORECASE)
        txt = pattern.sub(regec[1], txt)
    if ioformat == 'txt':
        txt = ''.join([letter for letter in txt if (letter.isalnum() or letter.isspace())])
    elif ioformat in ['lemma', 'upos']:
        txt = ''.join([letter for letter in txt if (letter.isalnum() or letter.isspace() or (letter == '_'))])
    else:
        txt = ''.join([letter for letter in txt if (letter.isalnum() or letter.isspace())])
    return txt


@log_timer
def join_archive(lang, ioformat='txt', years=(1900, 2050), verbose=False):
    """Method for joining an OpenSubtitles archive into a single large txt file.

    Writes joined corpus directly to a txt file.
    
    :param lang: corpus language
    :param ioformat: desired input/output format
    :param years: specific years to include in the output
    :param verbose: print progress bar or not
    :returns: number of subtitle files in corpus
    """
    read_zip = zipfile.ZipFile(f'corpora/{lang}_stripped.zip', 'r')
    out_fname = f'corpora/sub.{lang}.{ioformat}'
    if ioformat == 'txt':
        dirpath = 'OpenSubtitles/raw'
    elif ioformat in ['upos', 'lemma']:
        dirpath = 'OpenSubtitles/parsed'
    filepaths = []
    for filepath in read_zip.namelist():
        if filepath.endswith(ioformat):
            if filepath.startswith(os.path.join(dirpath, lang)):
                if int(filepath.split('/')[3]) in range(*years):
                    filepaths.append(filepath)
    total = len(filepaths)
    logging.info(f'joining {len(filepaths)} subtitles in {lang} into a single file')
    i = 0
    with open(out_fname, 'w') as outfile:
        for filepath in filepaths:
                outfile.write(strip_punctuation(read_zip.open(filepath).read().decode('utf-8'), ioformat))
                if verbose:
                    i += 1
                    print(f'\tprogress: {(float(i) / total) * 100:5.2f}%', end='\r')
        if verbose:
            print('')
    return total


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='clean subtitles for training distributional semantics models')
    argparser.add_argument('lang', help='language to clean')
    argparser.add_argument('--stripxml', action='store_true', help='strip xml from subtitle files')
    argparser.add_argument('--years', default=(1900, 2050), nargs=2, type=int, help='years of subtitles to include')
    argparser.add_argument('--join', action='store_true', help='join subtitles into one large txt file')
    argparser.add_argument('--ioformat', default='txt', choices=['txt', 'lemma', 'upos', 'viz'], help='input/output format')
    args = argparser.parse_args()

    if args.stripxml:
        strip_archive(args.lang, args.ioformat, args.years)
    if args.join:
        join_archive(args.lang, args.ioformat, args.years)
