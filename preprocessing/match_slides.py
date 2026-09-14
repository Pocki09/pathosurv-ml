import pandas as pd
from pathlib import Path

def match_manifest_and_clinical(manifest_path, clinical_csv, output_matched): 
    print("Matching WSI manifest with clinical metadata...") 

    # 1. Read the manifest file downloaded from GDC 
    manifest_df = pd.read_csv(manifest_path, sep='\t') 

    #2. Filter .svs (WSI) format files 
    wsi_df = manifest_df[manifest_df['filename'].str.endswith('.svs')].copy() 

    # 3. Extract patient submitter_id (eg: TCGA-FD-A3NA) from file name 
    wsi_df['submitter_id'] = wsi_df['filename'].apply( 
        lambda x: '-'.join(x.split('-')[:3]) if x.startswith('TCGA') else None
    )

    # 4. Read clinical metadata
    clinical_df = pd.read_csv(clinical_csv)

    # 5. Merge data by submitter_id
    matched_df = pd.merge(wsi_df, clinical_df, on='submitter_id', how='inner')
    Path(output_matched).parent.mkdir(parents=True, exist_ok=True)
    matched_df.to_csv(output_matched, index=False)
    print(f"Successfully matched {len(matched_df)} image template with survival label. Saved at {output_matched}")
    
    if __name__ == "__main__":
        # Note: Adjust the manifest file name to match the actual location in your data directory
        manifest_file = "D:/pathosurv-ml/data/gdc_manifest.2026-09-14.222309.txt" 
        clinical_file = "D:/pathosurv-ml/data/processed_metadata.csv" 
        out_matched = "D:/pathosurv-ml/data/matched_cohort.csv" 
        
        match_manifest_and_clinical(manifest_file, clinical_file, out_matched)