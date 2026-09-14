import torch
import torch.nn as nn
from torchvision import models, transforms
from pathlib import Path
import pandas as pd

class FeatureExtractor(nn.Module):
    def __init__(self, model_name="resnet50"):
        super(FeatureExtractor, self).__init__()
        print(f"Initializing feature extractor with {model_name}...")
        
        if model_name == "resnet50":
            # Using ResNet50 for fallback 
            weights = models.ResNet50_Weights.DEFAULT
            base_model = models.resnet50(weights=weights)
            # Remove the final classification layer to obtain a 2048-dimensional feature vector.
            self.feature_extractor = nn.Sequential(*list(base_model.children())[:-1])
        else:
            raise NotImplementedError(f"Model {model_name} not supported in the Lite version..")
            
        self.eval()

    def forward(self, x):
        with torch.no_grad():
            features = self.feature_extractor(x)
            features = torch.flatten(features, 1)
        return features

def extract_dummy_features(matched_csv, output_dir):
    print("Initiate the simulated feature extraction process. (Smoke Test)...")
    df = pd.read_csv(matched_csv)
    
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Using computing devices: {device}")
    
    extractor = FeatureExtractor(model_name="resnet50").to(device)
    
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    
    # Mock extraction for smoke test samples
    for idx, row in df.head(3).iterrows():
        case_id = row['case_id']
        # Create a dummy image patch tensor of size (B, 3, 224, 224).
        dummy_patches = torch.randn(10, 3, 224, 224).to(device)
        
        features = extractor(dummy_patches)
        
        save_file = out_path / f"{case_id}.pt"
        torch.save(features.cpu(), save_file)
        print(f"Extracted and saved features for case: {case_id} at {save_file}")

if __name__ == "__main__":
    matched_csv_file = "D:/pathosurv-ml/data/matched_cohort.csv"
    feature_output_dir = "D:/pathosurv-ml/data/features"
    extract_dummy_features(matched_csv_file, feature_output_dir)