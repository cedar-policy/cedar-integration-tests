#!/usr/bin/env python3
import tarfile
import json
import os
import re
import sys
import tempfile

def has_offset_extension(content):
    """Check if content contains offset extension usage in entity or request data"""
    return '"fn": "offset"' in content

STRING_LITERAL = re.compile(r'"(?:[^"\\]|\\.)*"')

def has_variadic_is_in_range(policy_text):
    """Check if policies call `isInRange` with more than one range, i.e., a
    top-level comma inside `.isInRange(...)`.

    Such calls error unless cedar is built with the experimental
    `variadic-is-in-range` feature, so their expected results depend on the
    feature flags used to generate the corpus. Remove this check once the
    feature is stabilized.
    """
    text = STRING_LITERAL.sub('""', policy_text)
    for m in re.finditer(r'\.isInRange\(', text):
        depth = 0
        for c in text[m.end():]:
            if c in '([{':
                depth += 1
            elif c in ')]}':
                if depth == 0:
                    break
                depth -= 1
            elif c == ',' and depth == 0:
                return True
    return False

def find_files_to_remove(input_tar):
    """Find files that use offset extension in entity or request data, or variadic isInRange in policies"""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract original tar
        with tarfile.open(input_tar, 'r:gz') as tar:
            tar.extractall(temp_dir, filter='data')

        corpus_dir = os.path.join(temp_dir, 'corpus-tests')
        files_to_remove = set()

        # Find all test JSON files
        for filename in os.listdir(corpus_dir):
            if filename.endswith('.json') and not filename.endswith('.entities.json'):
                json_path = os.path.join(corpus_dir, filename)

                should_remove = False

                # Parse JSON to check entity and request data
                try:
                    with open(json_path, 'r') as f:
                        test_data_content = f.read()
                        test_data = json.loads(test_data_content)
                    # Check the requests in the test file
                    if has_offset_extension(test_data_content):
                        should_remove = True
                    elif isinstance(test_data, dict):
                        # Check the entities file
                        entities_file = test_data.get('entities', '').replace('corpus-tests/', '')
                        if entities_file:
                            entities_path = os.path.join(corpus_dir, entities_file)
                            if os.path.exists(entities_path):
                                with open(entities_path, 'r') as f:
                                    if has_offset_extension(f.read()):
                                        should_remove = True
                    # Check the policies file
                    policies_path = os.path.join(corpus_dir, filename.replace('.json', '.cedar'))
                    if not should_remove and os.path.exists(policies_path):
                        with open(policies_path, 'r') as f:
                            if has_variadic_is_in_range(f.read()):
                                should_remove = True
                except json.JSONDecodeError:
                    pass

                if should_remove:
                    # Mark all related files for removal
                    base_name = filename.replace('.json', '')
                    files_to_remove.add(filename)
                    files_to_remove.add(f"{base_name}.cedar")
                    files_to_remove.add(f"{base_name}.entities.json")
                    files_to_remove.add(f"{base_name}.cedarschema")

        return files_to_remove

def process_corpus_tests(input_tar, output_tar):
    """Remove tests that use offset extension in entity or request data, or variadic isInRange in policies, from corpus-tests.tar.gz"""
    files_to_remove = find_files_to_remove(input_tar)

    # Filter tar without extracting
    removed_count = 0
    with tarfile.open(input_tar, 'r:gz') as tar_in:
        with tarfile.open(output_tar, 'w:gz') as tar_out:
            for member in tar_in.getmembers():
                filename = os.path.basename(member.name)
                if filename not in files_to_remove:
                    tar_out.addfile(member, tar_in.extractfile(member))
                else:
                    removed_count += 1

    print(f"Removed {removed_count} files")

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == '--check':
        files_to_remove = find_files_to_remove('corpus-tests.tar.gz')

        if files_to_remove:
            print(f"Found {len(files_to_remove)} files with offset extension in entity or request data, or variadic isInRange")
            sys.exit(1)
        else:
            print("No files with offset extension in entity or request data, or variadic isInRange, found")
    else:
        process_corpus_tests('corpus-tests.tar.gz', 'corpus-tests-filtered.tar.gz')
        print("Created corpus-tests-filtered.tar.gz without offset in entity or request data, or variadic isInRange")
