#!/usr/bin/env python
"""
training/scripts/run_training.py
Wrapper for launching fine-tuning jobs with config validation + GPU checks.
Usage: python run_training.py --config configs/qlora_llama3_8b.yaml
"""
import sys
import subprocess
from pathlib import Path

def check_gpu():
    import torch
    if not torch.cuda.is_available():
        print("ERROR: No GPU detected. QLoRA training requires CUDA.")
        sys.exit(1)
    print(f"GPU detected: {torch.cuda.get_device_name(0)}")

def main():
    check_gpu()
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        print(f"ERROR: Config not found: {config_path}")
        sys.exit(1)

    print(f"Starting fine-tuning with config: {config_path}")
    subprocess.run([
        sys.executable,
        "training/finetuning/train.py",
        str(config_path)
    ], check=True)

if __name__ == "__main__":
    main()
