## Module and CLI for citation file conversion

import argparse
import os, sys
from datetime import datetime
import bibtexparser

class Citation():
    def __init__(self, bibtex_string):
        self.info_dict = {}
        self.bibtex_provided = False
        self.repo_provided = False

        self.parse_bibtex(bibtex_string)


    def parse_bibtex(self, bibtex_string):
        '''Load bibtex file from string, and save data in self.info_dict'''
        layers = [bibtexparser.middlewares.LatexDecodingMiddleware()]
        library = bibtexparser.parse_string(bibtex_string, append_middleware=layers)

        assert len(library.entries) == 1, 'more than 1 entries in bib tex file, give ind or something'
        bib_info = library.entries[0]
        assert type(bib_info) == bibtexparser.model.Entry

        bib_keys = bib_info.fields_dict.keys()
        self.info_dict['ENTRYTYPE'] = bib_info.entry_type
        for key in ['title', 'booktitle', 'pages', 'year', 'month', 'day', 'journal',
                    'volume', 'series', 'issue', 'editor', 'publisher', 'url', 'doi', 'abstract']:
            if key in bib_keys:
                self.info_dict[key] = bib_info[key]

        if 'pages' in self.info_dict.keys():
            ## Expected format: 'start--stop'
            split_pages = self.info_dict['pages'].split('–')
            if len(split_pages) == 2:
                self.info_dict['start'] = int(split_pages[0])
                self.info_dict['end'] = int(split_pages[1])
            elif len(split_pages) == 1:
                self.info_dict['start'] = split_pages[0]
            else:
                assert False, 'pages does not have expected format'

        ## Author info
        if 'author' in bib_keys:
            author_list = bib_info['author'].split(' and ')
            self.info_dict['n_authors'] = len(author_list)
            author_dict = {}
            for ind, author_name in enumerate(author_list):
                author_dict[ind] = {}
                if ',' in author_name:
                    assert len(author_name.split(',')) == 2, f'More than 1 comma (,) in {author_name}'
                    author_dict[ind]['full_name'] = author_name.strip()
                    author_dict[ind]['first_name'] = author_name.split(',')[1].strip()
                    author_dict[ind]['last_name'] = author_name.split(',')[0].strip()
                else:
                    assert len(author_name.split()) == 2, f'More than two names {author_name}'
                    author_dict[ind]['full_name'] = author_name.strip()
                    author_dict[ind]['first_name'] = author_name.split()[0].strip()
                    author_dict[ind]['last_name'] = author_name.split()[1].strip()
            self.info_dict['author_dict'] = author_dict
        else:
            self.info_dict['author'] = None

        self.bibtex_provided = True

    def prep_info_for_export(self):
        '''Run some checks and make data in order'''
        assert self.bibtex_provided, 'bibtex file not yet provided'

        idk = self.info_dict.keys()

        ## Prep date:
        find_date = True
        construct_date = False
        while find_date:
            if 'date-released' in idk:
                find_date = False
            elif 'date' in idk:
                self.info_dict['date-released'] = self.info_dict['date']
                find_date = False

            construct_date = True
            dt = datetime.now()
            if 'year' in idk:
                year = self.info_dict['year']
            else:  # use current date
                year = dt.year
                month = dt.month
                day = dt.day
                find_date = False
            if 'month' in idk:
                month = self.info_dict['month']
            else:  # if year known but not month, just to 1 Jan
                month = 1
                day = 1
                find_date = False
            if 'day' in idk:
                day = self.info_dict['day']
                find_date = False
            else:
                day = 1
                find_date = False


        if construct_date:
            self.info_dict['date-released'] = f'{year}-{str(month).zfill(2)}-{str(day).zfill(2)}'

        ## Bibtex type:
        if 'ENTRYTYPE' in self.info_dict.keys():
            type_mapping_bib_to_cff = {'article': 'article', 'book': 'book', 'booklet': 'pamphlet',
                                       'inproceedings': 'conference-paper', 'proceedings': 'proceedings',
                                       'misc': 'generic', 'manual': 'manual', 'software': 'software',
                                       'techreport': 'report', 'unpublished': 'unpublished'}  #https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/about-citation-files
            self.info_dict['cff_type'] = type_mapping_bib_to_cff[self.info_dict['ENTRYTYPE']]

        ## Journal
        if 'journal' not in self.info_dict.keys():
            if 'series' in self.info_dict.keys():
                self.info_dict['journal'] = self.info_dict['series']

        ## To copy booktitle (ignored by github) as conference.name
        if 'cff_type' in self.info_dict.keys() and self.info_dict['cff_type'] == 'conference-paper':
            if 'booktitle' in self.info_dict.keys():
                if 'conference' not in self.info_dict.keys():
                    self.info_dict['conference'] = self.info_dict['booktitle']

    def add_author_names_to_cff(self, indent_n_spaces=0):
        '''Add list of all author names to cff file'''
        assert type(indent_n_spaces) == int and indent_n_spaces >= 0
        id = ' ' * indent_n_spaces
        assert 'author_dict' in self.info_dict
        ad = self.info_dict['author_dict']
        assert self.info_dict['n_authors'] == len(ad)
        assert len(ad) > 0

        f = sys.stdout
        f.write(f'{id}authors:\n')
        for i_author, author_name_dict in ad.items():
            # f.write(f'{id}  - name-suffix: "N/A"\n')
            f.write(f'{id}  - family-names: "{author_name_dict["last_name"]}"\n')
            f.write(f'{id}    given-names: "{author_name_dict["first_name"]}"\n')
            # f.write(f'{id}    name-particle: "N/A"\n')
            if 'orcid' in author_name_dict.keys():
                f.write(f'{id}    orcid: "{author_name_dict["orcid"]}"\n')

    def export_as_cff(self, cff_version="1.2.0"):
        '''Export citation info to a cff file.'''
        assert type(cff_version) == str, type(cff_version)
        self.prep_info_for_export()

        f = sys.stdout
        f.write(f'date-released: "{self.info_dict["date-released"]}"\n')
        ## Prioritise paper doi over repo doi:
        if 'doi' in self.info_dict.keys():
            f.write(f'doi: "{self.info_dict["doi"]}"\n')
        elif 'repo_doi' in self.info_dict.keys():
            f.write(f'doi: "{self.info_dict["repo_doi"]}"\n')
        f.write(f'title: "{self.info_dict["title"]}"\n')
        f.write(f'cff-version: "{cff_version}"\n')
        if 'repo_version' in self.info_dict.keys():
            f.write(f'version: "{self.info_dict["repo_version"]}"\n')

        self.add_author_names_to_cff(indent_n_spaces=0)

        f.write('preferred-citation:\n')
        if 'cff_type' in self.info_dict.keys():
            f.write(f'  type: "{self.info_dict["cff_type"]}"\n')
        else:
            f.write('  type: "generic"\n')
        if 'publisher' in self.info_dict:
            f.write('  publisher:\n')
            f.write(f'    name: "{self.info_dict["publisher"]}"\n')
        if 'conference' in self.info_dict:
            f.write('  conference:\n')
            f.write(f'    name: "{self.info_dict["conference"]}"\n')
        for key in ['doi', 'url', 'date-released', 'issue', 'volume', 'journal', 'title',
                    'booktitle', 'editor', 'series', 'publisher', 'start', 'end']:
            if key in self.info_dict.keys():
                f.write(f'  {key}: "{self.info_dict[key]}"\n')

        self.add_author_names_to_cff(indent_n_spaces=2)

def process(args, file_name, file_input):
    """Process the specified input"""
    bibtex_data = file_input.read()
    citation = Citation(bibtex_data)
    citation.export_as_cff()


def main():
    """Program entry point"""
    parser = argparse.ArgumentParser(
        description='BibTeX to CFF converter')
    parser.add_argument('file',
                        help='File to process',
                        nargs='*', default='-',
                        type=str)
    args = parser.parse_args()
    for file_name in args.file:
        if file_name == '-':
            process(args, '<stdin>', sys.stdin)
        else:
            with open(file_name) as file_input:
                process(args, file_name, file_input)

if __name__ == "__main__":
    main()
