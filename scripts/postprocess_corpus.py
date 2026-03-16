#!/usr/bin/env python3
import tarfile
import json
import os
import sys
import tempfile

def has_offset_extension(content):
    """Check if content contains offset extension usage in entity or request data"""
    return '"fn": "offset"' in content

def find_files_to_remove(input_tar):
    """Find files that use offset extension in entity or request data"""
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
    """Remove tests that use offset extension in entity or request data from corpus-tests.tar.gz"""
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
            print(f"Found {len(files_to_remove)} files with offset extension in entity or request data")
            sys.exit(1)
        else:
            print("No files with offset extension in entity or request data found")
    else:
        process_corpus_tests('corpus-tests.tar.gz', 'corpus-tests-filtered.tar.gz')
        print("Created corpus-tests-filtered.tar.gz without offset in entity or request data")
