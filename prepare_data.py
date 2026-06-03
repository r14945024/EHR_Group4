import os
import json

def bundle_to_ndjson(fhir_dir, output_file):
    count = 0
    with open(output_file, 'w') as outfile:
        for filename in os.listdir(fhir_dir):
            if filename.endswith('.json'):
                with open(os.path.join(fhir_dir, filename), 'r') as infile:
                    try:
                        bundle = json.load(infile)
                        if bundle.get('resourceType') == 'Bundle':
                            for entry in bundle.get('entry', []):
                                resource = entry.get('resource')
                                if resource:
                                    outfile.write(json.dumps(resource) + '\n')
                                    count += 1
                        else:
                            outfile.write(json.dumps(bundle) + '\n')
                            count += 1
                    except Exception as e:
                        print(f"Error processing {filename}: {e}")
    print(f"✅ Extracted {count} resources to {output_file}")

if __name__ == "__main__":
    bundle_to_ndjson('fhir', 'exported_data.ndjson')
