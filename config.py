# config.py
import os

# Base path configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
RESULTS_ROOT = os.path.join(BASE_DIR, "results")
VIDEO_UPLOAD_DIR = os.path.join(BASE_DIR, "videos")

# SAM2 Model paths (Modify these paths based on your actual environment)
SAM2_CHECKPOINT = "/home/ipd/CV_Models/sam2/checkpoints/sam2.1_hiera_large.pt"
SAM2_CONFIG = "configs/sam2.1/sam2.1_hiera_l.yaml"

# Default parameters
DEFAULT_FPS = 30
DEFAULT_QUALITY = 2  # FFmpeg -q:v parameter (lower is better quality)
MAX_INFERENCE_FRAMES = 120

# Ensure base directories exist
os.makedirs(RESULTS_ROOT, exist_ok=True)
os.makedirs(VIDEO_UPLOAD_DIR, exist_ok=True)