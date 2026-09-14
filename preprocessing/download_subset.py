import pandas as pd
import subprocess
from pathlib import Path

def download_wsi_subset(matched_csv, num_samples=3):
    print(f"Reading list from {matched_csv}...")
    df = pd.read_csv(matched_csv)

    # Select a random subset or the first few samples for testing
    subset = df.head(num_samples)

    # Create directory to store raw slide images
    raw_slides_dir = Path("D:/pathosurv-ml/data/raw_slides")
    raw_slides_dir.mkdir(parents=True, exist_ok=True)

    # Create a dedicated manifest file for this subset to use with gdc-client
    subset_manifest = Path("D:/pathosurv-ml/data/subset_manifest.txt")

    # Select columns required for the GDC manifest (id, filename, md5, size, state)
    cols_to_keep = ['id', 'filename', 'md5', 'size', 'state']
    # Check if the dataframe contains these columns
    if all(col in df.columns for col in cols_to_keep):
        subset[cols_to_keep].to_csv(subset_manifest, sep='\t', index=False)
    else:
        # If missing, filter from the original manifest based on IDs in the subset
        original_manifest = pd.read_csv("D:/pathosurv-ml/data/gdc_manifest.2026-09-14.222309.txt", sep='\t')
        filtered_manifest = original_manifest[original_manifest['id'].isin(subset['id'])]
        filtered_manifest.to_csv(subset_manifest, sep='\t', index=False)

    print(f"Created test manifest with {len(subset)} samples at {subset_manifest}")
    print("Note: You can use gdc-client to download these files to the raw_slides directory.")

if __name__ == "__main__": 
    download_wsi_subset("D:/pathosurv-ml/data/matched_cohort.csv", num_samples=3)