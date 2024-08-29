#!/usr/bin/env python3

"""
Prints some basic statistics about the input corpus.

The corpus should be a `*.tar.gz` file storing tests in the format expected by
the `cedar-integration-tests` repository.

This script is used for spot-checking generated test cases. It is not a
complete solution for evaluating test quality. Improvements welcome!
"""

import argparse
import fnmatch
import hashlib
import json
import numpy
import os
import shutil
import sys
from tabulate import tabulate
import tarfile

class Report():
    """
    A class storing a variety of corpus statistics.
    """
    def __init__(self, path):
        """
        Initializes a Report.

        Parameters:
            path (str): The path to the (extracted) corpus.
        """
        all_files = [os.path.join(path, file_name) for file_name in os.listdir(path)]
        policy_files = fnmatch.filter(all_files, '*.cedar')
        schema_files = fnmatch.filter(all_files, '*.cedarschema')
        entity_files = fnmatch.filter(all_files, '*.entities.json')

        # get total number of test cases
        self.count = len(policy_files)

        # check uniqueness
        self.unique_policies = self._get_num_unique(policy_files)
        self.unique_schemas = self._get_num_unique(schema_files)
        self.unique_entities = self._get_num_unique(entity_files)

        # count the number of entities per entity store
        self.entity_counts = self._count_entities(entity_files)

        # count the number of entity types & actions per schema
        schema_counts = self._count_schema_elements(schema_files)
        self.schema_entity_type_counts = schema_counts[0]
        self.schema_action_counts = schema_counts[1]

        # get some basic statistics on the types of policies
        policy_counts = self._categorize_policies(policy_files)
        self.trivial_policies = policy_counts[0]
        self.rbac_policies = policy_counts[1]
        self.abac_policies = policy_counts[2]
    
    def _fmt_percentage(self, x):
        return f"{x} ( {x/self.count:.1%} )"

    @staticmethod
    def _fmt_summary_statistics(data):
        arr = numpy.array(data)
        mean = numpy.percentile(arr, 50)
        median = numpy.median(arr)
        p90 = numpy.percentile(arr, 90)
        return f"mean: {mean:.0f} / median: {median:.0f} / p90: {p90:.0f}"

    def _make_table(self):
        return [
            ["Total test cases", self.count],
            ["Unique policies", self._fmt_percentage(self.unique_policies)],
            ["Unique schemas", self._fmt_percentage(self.unique_schemas)],
            ["Unique entity stores", self._fmt_percentage(self.unique_entities)],
            ["Entities per entity store", self._fmt_summary_statistics(self.entity_counts)],
            ["Schema entity types", self._fmt_summary_statistics(self.schema_entity_type_counts)],
            ["Schema actions", self._fmt_summary_statistics(self.schema_action_counts)],
            ["Trivial policies", self._fmt_percentage(self.trivial_policies)],
            ["Pure RBAC (non-trivial) policies", self._fmt_percentage(self.rbac_policies)],
            ["Pure ABAC (non-trivial) policies", self._fmt_percentage(self.abac_policies)]
        ]

    def pretty_print(self):
        """
        Pretty prints the report as a markdown table.
        """
        table = self._make_table()
        print() # newline
        print(tabulate(table, ["", ""], tablefmt='github'))
        print() # newline

    def compare(self, other):
        """
        Compares two reports and prints the result as a markdown table.
        """
        original_table = self._make_table()
        new_table = other._make_table()
        difference_table = [
            other.count - self.count,
            other.unique_policies - self.unique_policies,
            other.unique_schemas - self.unique_schemas,
            other.unique_entities - self.unique_entities,
            "n/a",
            "n/a",
            "n/a",
            other.trivial_policies - self.trivial_policies,
            other.rbac_policies - self.rbac_policies,
            other.abac_policies - self.abac_policies
        ]
        headers = ["", "Original", "New", "Difference"]
        combined_table = [row + [new_table[i][1], difference_table[i]] for i, row in enumerate(original_table)]
        print() # newline
        print(tabulate(combined_table, headers, tablefmt='github'))
        print() # newline

    def _get_num_unique(self, files):
        """
        Returns the number of unique files.
        """
        duplicates = {}
        for file in files: 
            hash = self._hash_file(file) 
            if hash in duplicates: 
                duplicates[hash].append(file) 
            else: 
                duplicates[hash] = [file] 
        return len(duplicates)
    
    @staticmethod
    def _hash_file(path):
        """
        Gets the hash of a file. Borrowed from https://www.geeksforgeeks.org/finding-duplicate-files-with-python/.
        """
        afile = open(path, 'rb') 
        hasher = hashlib.md5() 
        blocksize=65536
        buf = afile.read(blocksize) 
        while len(buf) > 0: 
            hasher.update(buf) 
            buf = afile.read(blocksize) 
        afile.close() 
        return hasher.hexdigest()

    @staticmethod
    def _count_entities(entity_files):
        """
        Returns the number of entities (which just amounts to loading the JSON
        entity file and checking the length).
        """
        counts = []
        for file in entity_files:
            f = open(file, 'r')
            json_data = json.load(f)
            counts.append(len(json_data))
        return counts

    @staticmethod
    def _count_schema_elements(schema_files):
        """
        Returns a tuple (entity_types, actions) which counts the number of
        entity types and actions defined in the schema.

        Uses simple string matching, which may break in the future if the
        schema formatter changes, or in edge cases where a name contains the
        string "entity " or "action ".
        """
        entity_type_counts, action_counts = [], []
        for file in schema_files:
            f = open(file, 'r')
            entity_type_count, action_count = 0, 0
            for line in f:
                if "entity " in line:
                    entity_type_count += 1
                if "action " in line:
                    action_count += 1
            entity_type_counts.append(entity_type_count)
            action_counts.append(action_count)
        return (entity_type_counts, action_counts)

    @staticmethod
    def _categorize_policies(policy_files):
        """
        Returns a tuple (trivial, rbac, abac) where:
            - trivial = number of policies that use a trivial scope and condition
            - rbac = number of policies that use a trivial condition (but not a trivial scope)
            - abac = number of policies that use a trivial scope (but not a trivial condition)
        
        Uses simple string matching, which may break in the future if the
        policy formatter changes.
        """
        trivial, rbac, abac = 0, 0, 0
        TRIVIAL_SCOPE = "( principal, action, resource )"
        TRIVIAL_CONDITION_A = "{ true }"
        TRIVIAL_CONDITION_B = "{ false }"
        for input in policy_files:
            f = open(input, 'r')
            lines = [line.strip() for line in f.readlines()]
            text = " ".join(lines)
            trivial_scope = TRIVIAL_SCOPE in text
            trivial_condition = TRIVIAL_CONDITION_A in text or TRIVIAL_CONDITION_B in text
            if trivial_scope and trivial_condition:
                trivial += 1
            elif trivial_condition:
                rbac += 1
            elif trivial_scope:
                abac += 1
        return (trivial, rbac, abac)

def main(arguments):

    parser = argparse.ArgumentParser()
    parser.add_argument('corpus', help="Corpus to analyze")
    parser.add_argument('-o', '--original', help="Original corpus for comparison")

    args = parser.parse_args(arguments)

    print("Extracting", args.corpus)
    tar = tarfile.open(args.corpus, "r:gz")
    tar.extraction_filter = (lambda member, path: member)
    tar.extractall()
    tar.close()

    if args.original is None:
        print("Generating report")
        report = Report("corpus-tests")
        report.pretty_print()
    else:
        # move the extracted corpus to a new location
        shutil.move("corpus-tests", "corpus-tests-new")

        # extract the other corpus
        print("Extracting", args.original)
        tar = tarfile.open(args.original, "r:gz")
        tar.extraction_filter = (lambda member, path: member)
        tar.extractall()
        tar.close()

        # generate report
        print("Generating report")
        report_new = Report("corpus-tests-new")
        report_original = Report("corpus-tests")
        report_original.compare(report_new)

    # get rid of extracted files
    shutil.rmtree("corpus-tests")
    if args.original:
        shutil.rmtree("corpus-tests-new")

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))