#!/usr/bin/env python3
import tarfile
import json
import os
import tempfile

def has_offset_extension(content):
    """Check if content contains offset extension usage in entity data"""
    return '"fn": "offset"' in content

def process_corpus_tests(input_tar, output_tar):
    """Remove tests that use offset extension in entity data from corpus-tests.tar.gz"""
    
    with tempfile.TemporaryDirectory() as temp_dir:
        # Extract original tar
        with tarfile.open(input_tar, 'r:gz') as tar:
            tar.extractall(temp_dir)
        
        corpus_dir = os.path.join(temp_dir, 'corpus-tests')
        files_to_remove = set()
        
        # Find all test JSON files
        for filename in os.listdir(corpus_dir):
            if filename.endswith('.json') and not filename.endswith('.entities.json'):
                json_path = os.path.join(corpus_dir, filename)
                
                should_remove = False
                
                # Parse JSON to check entities file only
                try:
                    with open(json_path, 'r') as f:
                        test_data = json.loads(f.read())
                    
                    if isinstance(test_data, dict):
                        # Check entities file only
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
        
        # Remove marked files
        removed_count = 0
        for filename in files_to_remove:
            file_path = os.path.join(corpus_dir, filename)
            if os.path.exists(file_path):
                os.remove(file_path)
                removed_count += 1
        
        print(f"Removed {removed_count} files")
        
        # Create new tar.gz
        with tarfile.open(output_tar, 'w:gz') as tar:
            tar.add(corpus_dir, arcname='corpus-tests')

if __name__ == '__main__':
    process_corpus_tests('corpus-tests.tar.gz', 'corpus-tests-filtered.tar.gz')
    print("Created corpus-tests-filtered.tar.gz without offset in entity data")
