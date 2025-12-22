# logic/tracker.py
import os
import torch
import numpy as np
from sam2.build_sam import build_sam2_video_predictor
from config import SAM2_CHECKPOINT, SAM2_CONFIG
from logic.visualizer import save_tracking_frame
from contextlib import nullcontext

class SAM2Tracker:
    def __init__(self):
        # Detect device
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if self.device.type == "cuda":
            # Enable bfloat16 and tf32 for faster inference on Ampere+ GPUs
            if torch.cuda.get_device_properties(0).major >= 8:
                torch.backends.cuda.matmul.allow_tf32 = True
                torch.backends.cudnn.allow_tf32 = True
        
        print(f"[INFO] Loading SAM2 model on {self.device}...")
        self.predictor = build_sam2_video_predictor(SAM2_CONFIG, SAM2_CHECKPOINT, device=self.device)
        self.inference_state = None

    def init_session(self, frames_dir):
        """Initializes the SAM2 inference state with the path to video frames."""
        if not os.path.exists(frames_dir):
            raise FileNotFoundError(f"Frames directory not found: {frames_dir}")
        self.inference_state = self.predictor.init_state(video_path=frames_dir)
        self.predictor.reset_state(self.inference_state)

    def _add_points(self, points, labels):
        """
        Internal helper: Resets state and adds points to Frame 0.
        Called by both preview and propagation methods.
        """
        self.predictor.reset_state(self.inference_state)
        
        points_np = np.array(points, dtype=np.float32)
        labels_np = np.array(labels, dtype=np.int32)
        
        # Add new points (obj_id=1)
        ctx = torch.autocast("cuda", dtype=torch.bfloat16) if self.device.type == "cuda" else nullcontext()
        with ctx:
            _, out_obj_ids, out_mask_logits = self.predictor.add_new_points(
                inference_state=self.inference_state,
                frame_idx=0,
                obj_id=1,
                points=points_np,
                labels=labels_np,
            )
        return out_mask_logits

    def get_first_frame_mask(self, points, labels):
        """
        Runs inference ONLY on frame 0 based on user clicks.
        Returns the binary mask for preview.
        """
        if not self.inference_state:
            raise RuntimeError("Session not initialized.")
            
        logits = self._add_points(points, labels)
        # Convert logits to binary mask (True/False)
        mask = (logits[0] > 0.0).cpu().numpy().squeeze()
        return mask

    def propagate(self, frames_dir, output_mask_dir, points, labels, max_frames=120):
        """
        Runs full video propagation and saves masked frames.
        """
        # 1. Ensure points are added to the state
        self._add_points(points, labels)
        
        os.makedirs(output_mask_dir, exist_ok=True)
        trajectory = [] 
        
        # 2. Propagate through video
        ctx = torch.autocast("cuda", dtype=torch.bfloat16) if self.device.type == "cuda" else nullcontext()
        with ctx:
            for out_frame_idx, out_obj_ids, out_mask_logits in self.predictor.propagate_in_video(self.inference_state):
                if out_frame_idx >= max_frames:
                    break
                    
                # Get binary mask
                mask = (out_mask_logits[0] > 0.0).cpu().numpy().squeeze()
                
                # Calculate centroid (0,0 if no object detected)
                y_indices, x_indices = np.where(mask)
                if len(x_indices) > 0:
                    centroid_x = np.mean(x_indices)
                    centroid_y = np.mean(y_indices)
                    trajectory.append((centroid_x, centroid_y))
                else:
                    trajectory.append((0, 0)) # Placeholder for interpolation later
                
                # Save the frame blended with mask
                frame_path = os.path.join(frames_dir, f"{out_frame_idx:05d}.jpg")
                save_path = os.path.join(output_mask_dir, f"{out_frame_idx:05d}.jpg")
                
                save_tracking_frame(frame_path, mask, save_path)
            
        return trajectory