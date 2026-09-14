import json
import pandas as pd
from pathlib import Path

def parse_clinical_json(json_path, output_csv):
    print(f"Reading clinical data from {json_path}...")
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    records = []
    for case in data:
        case_id = case.get('case_id')
        submitter_id = case.get('submitter_id') # Patient ID (Ex: TCGA-FD-A3NA)
        
        demographic = case.get('demographic', {})
        vital_status = demographic.get('vital_status')
        
        diagnoses = case.get('diagnoses', [])
        if not diagnoses:
            continue
        
        diag = diagnoses[0]
        days_to_death = diag.get('days_to_death')
        days_to_last_follow_up = diag.get('days_to_last_follow_up')
        
        # Assign the standard 'Survival' label for survival analysis.
        if vital_status == 'Dead' and days_to_death is not None:
            time = float(days_to_death)
            event = 1
        elif vital_status == 'Alive' and days_to_last_follow_up is not None:
            time = float(days_to_last_follow_up)
            event = 0
        else:
            continue
            
        records.append({
            'case_id': case_id,
            'submitter_id': submitter_id,
            'OS_time': time,
            'OS_event': event,
            'vital_status': vital_status
        })
        
    df = pd.DataFrame(records)
    Path(output_csv).parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(output_csv, index=False)
    print(f"Processed {len(df)} valid survival records. Saved to {output_csv}")

if __name__ == "__main__":
    json_file = "D:/pathosurv-ml/data/clinical.json"
    out_file = "D:/pathosurv-ml/data/processed_metadata.csv"
    parse_clinical_json(json_file, out_file)