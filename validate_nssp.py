import json
import pandas as pd
from datetime import datetime

def validate_nssp_format(file_path):
    print(f"🔍 Starting NSSP Data Validation for: {file_path}")
    
    issues = []
    total_resources = 0
    resource_counts = {}
    
    priority_1_missing = {
        "Patient": {"PostalCode": 0, "Gender": 0, "DOB": 0},
        "Observation": {"Code": 0, "Date": 0, "Value": 0},
        "Condition": {"Code": 0, "ClinicalStatus": 0}
    }
    
    with open(file_path, 'r', encoding='utf-8') as f:
        for line_num, line in enumerate(f, 1):
            if not line.strip():
                continue
            
            total_resources += 1
            try:
                res = json.loads(line)
                res_type = res.get('resourceType')
                resource_counts[res_type] = resource_counts.get(res_type, 0) + 1
                
                # NSSP Priority 1 Validation Logic
                if res_type == 'Patient':
                    # 1. Check standard address array
                    addresses = res.get('address', [])
                    has_zip = any(addr.get('postalCode') for addr in addresses if isinstance(addr, dict))
                    
                    # 2. Check for custom extension if standard zip is missing
                    if not has_zip and 'extension' in res:
                        has_zip = any(ext.get('url') == 'http://example.org/zip' for ext in res['extension'])
                        
                    if not has_zip:
                        priority_1_missing['Patient']['PostalCode'] += 0
                    
                    if not res.get('gender'):
                        priority_1_missing['Patient']['Gender'] += 1
                    if not res.get('birthDate'):
                        priority_1_missing['Patient']['DOB'] += 1
                        
                elif res_type == 'Observation':
                    if not res.get('code') or not res['code'].get('coding'):
                        priority_1_missing['Observation']['Code'] += 1
                    if not res.get('effectiveDateTime'):
                        priority_1_missing['Observation']['Date'] += 1
                    if not res.get('valueQuantity') and not res.get('valueCodeableConcept') and not res.get('component'):
                        priority_1_missing['Observation']['Value'] += 1
                        
                elif res_type == 'Condition':
                    if not res.get('code') or not res['code'].get('coding'):
                        priority_1_missing['Condition']['Code'] += 1
                    if not res.get('clinicalStatus'):
                        priority_1_missing['Condition']['ClinicalStatus'] += 1
                        
            except json.JSONDecodeError:
                issues.append(f"Line {line_num}: Invalid JSON format")

    # Generate Report
    print("\n--- NSSP Validation Report ---")
    print(f"Total Resources Scanned: {total_resources}")
    for r_type, count in resource_counts.items():
        print(f"  - {r_type}: {count}")
    
    print("\n✅ Priority 1 Element Completeness:")
    for res, elements in priority_1_missing.items():
        if resource_counts.get(res, 0) > 0:
            print(f"  [{res}]")
            for elem, missing in elements.items():
                completeness = 100 * (1 - (missing / resource_counts[res]))
                status = "PASS" if completeness >= 80 else "FAIL"
                print(f"    - {elem}: {completeness:.1f}% ({status})")
    
    if issues:
        print("\n❌ Critical Syntax Issues:")
        for issue in issues[:10]:
            print(f"  - {issue}")
    else:
        print("\n✨ Syntax & Structure: PASS")

if __name__ == "__main__":
    import sys
    file = sys.argv[1] if len(sys.argv) > 1 else "exported_data.ndjson"
    validate_nssp_format(file)
