# logic/video_processor.py
import os
import subprocess
import glob
from config import RESULTS_ROOT

import json

def create_project_folder(username, video_path, tracking_object):
    """
    Creates the project folder structure and returns the path.
    """
    if not os.path.exists(video_path):
        raise FileNotFoundError(f"Video file not found: {video_path}")

    # Extract clean video name
    video_name_clean = os.path.splitext(os.path.basename(video_path))[0]
    
    # Construct Project Name
    safe_obj_name = "".join([c if c.isalnum() else "_" for c in tracking_object])
    project_name = f"{video_name_clean}_{safe_obj_name}_Tracking"
    
    # Path: results/username/project_name
    user_project_dir = os.path.join(RESULTS_ROOT, username, project_name)
    frames_dir = os.path.join(user_project_dir, "frames")
    metadata_dir = os.path.join(user_project_dir, "metadata")
    
    os.makedirs(frames_dir, exist_ok=True)
    os.makedirs(metadata_dir, exist_ok=True)
    
    return user_project_dir, project_name

def run_ffmpeg_cutting(username, video_path, tracking_object, fps=1.0, start_time=None, end_time=None, quality=2):
    """
    Runs FFmpeg to cut frames. Assumes project folder might need to be created or already exists.
    Re-uses create_project_folder logic to ensure path consistency.
    """
    # Ensure folder exists (idempotent)
    user_project_dir, _ = create_project_folder(username, video_path, tracking_object)
    frames_dir = os.path.join(user_project_dir, "frames")
    metadata_dir = os.path.join(user_project_dir, "metadata")
    
    # Save Metadata
    metadata = {
        "original_video": os.path.basename(video_path),
        "fps": fps,
        "quality": quality,
        "start_time": start_time,
        "end_time": end_time,
        "tracking_object": tracking_object
    }
    with open(os.path.join(metadata_dir, "metadata.json"), "w") as f:
        json.dump(metadata, f, indent=4)
    
    # Clean up old frames
    for f in glob.glob(os.path.join(frames_dir, "*.jpg")):
        os.remove(f)
        
    # Build FFmpeg command
    cmd = ["ffmpeg", "-i", video_path]
    
    if start_time:
        cmd.extend(["-ss", str(start_time)])
    if end_time:
        cmd.extend(["-to", str(end_time)])
        
    cmd.extend([
        "-q:v", str(quality),
        "-r", str(fps),
        "-start_number", "0",
        os.path.join(frames_dir, "%05d.jpg")
    ])
    
    print(f"[INFO] Running FFmpeg command: {' '.join(cmd)}")
    subprocess.run(cmd, check=True)
    
    frames = sorted(glob.glob(os.path.join(frames_dir, "*.jpg")))
    
    return frames, frames_dir, user_project_dir

# Backward compatibility alias if needed, or just use run_ffmpeg_cutting
process_video = run_ffmpeg_cutting