import sys
import torch
import pandas as pd
import sksurv
from training.utils import set_seed

def main():
    print("=== ENVIRONMENT CHECK ===")
    print(f"Python: {sys.version.split()[0]}")
    print(f"PyTorch: {torch.__version__}")
    print(f"CUDA Available: {torch.cuda.is_available()}")
    print(f"Pandas: {pd.__version__}")
    print(f"scikit-survival: {sksurv.__version__}")
    
    print("\n=== SEED CHECK ===")
    set_seed(42)
    
    print("\nEnvironment is ready!")

if __name__ == "__main__":
    main()