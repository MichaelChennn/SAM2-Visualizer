# logic/visualizer.py
import os
import matplotlib
# Use 'Agg' backend to prevent Tcl/Tk errors in WSL/Headless environments
matplotlib.use('Agg') 
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image, ImageDraw
import pandas as pd
import subprocess
from scipy.interpolate import make_interp_spline

# --- Helper Functions (Integrated from your provided script) ---

def show_mask(mask, ax, obj_id=None, random_color=False):
    """
    Visualizes the mask on a given matplotlib axis.
    """
    if random_color:
        color = np.concatenate([np.random.random(3), np.array([0.6])], axis=0)
    else:
        cmap = plt.get_cmap("tab10")
        cmap_idx = 0 if obj_id is None else obj_id
        color = np.array([*cmap(cmap_idx)[:3], 0.6])
    h, w = mask.shape[-2:]
    mask_image = mask.reshape(h, w, 1) * color.reshape(1, 1, -1)
    ax.imshow(mask_image)

def show_points(coords, labels, ax, marker_size=200):
    """
    Visualizes positive and negative points on a matplotlib axis.
    """
    coords = np.array(coords)
    labels = np.array(labels)
    
    # Ensure there is data to plot
    if len(coords) > 0 and len(labels) > 0:
        pos_points = coords[labels==1]
        neg_points = coords[labels==0]
        
        if len(pos_points) > 0:
            ax.scatter(pos_points[:, 0], pos_points[:, 1], color='green', marker='*', s=marker_size, edgecolor='white', linewidth=1.25)
        if len(neg_points) > 0:
            ax.scatter(neg_points[:, 0], neg_points[:, 1], color='red', marker='*', s=marker_size, edgecolor='white', linewidth=1.25)

def replace_zero_coordinates(df):
    """
    Interpolates (fills) zero coordinates (0,0) in the trajectory data to smooth the path.
    Typically used when the object is lost or occluded for a few frames.
    """
    x = df['x'].values
    y = df['y'].values
    zero_indices = np.where((x == 0) & (y == 0))[0]

    for idx in zero_indices:
        prev_idx = idx - 1
        while prev_idx >= 0 and (x[prev_idx] == 0 and y[prev_idx] == 0):
            prev_idx -= 1
        next_idx = idx + 1
        while next_idx < len(x) and (x[next_idx] == 0 and y[next_idx] == 0):
            next_idx += 1
        
        # Linear interpolation
        if prev_idx >= 0 and next_idx < len(x):
            x[idx] = (x[prev_idx] + x[next_idx]) / 2
            y[idx] = (y[prev_idx] + y[next_idx]) / 2
        elif prev_idx >= 0:  
            x[idx] = x[prev_idx]
            y[idx] = y[prev_idx]
        elif next_idx < len(x):  
            x[idx] = x[next_idx]
            y[idx] = y[next_idx]
            
    df['x'] = x
    df['y'] = y
    return df

# --- Main Visualization Functions ---

def render_preview(image_path, mask, points=None, labels=None):
    """
    Generates a preview image for Frame 0 with the mask and points overlaid.
    Returns a PIL Image object.
    """
    if not os.path.exists(image_path):
        return None
        
    image = Image.open(image_path).convert("RGB")
    w, h = image.size
    
    # Overlay mask if exists
    if mask is not None:
        # Ensure mask is in correct shape (H, W)
        if isinstance(mask, np.ndarray):
            # Handle (K, H, W) or (1, H, W) or (H, W)
            if mask.ndim == 3:
                mask = mask[0] # Take the first channel/mask
            
            # Use same logic as save_tracking_frame for consistency
            # Cyan color: (0, 1, 1)
            color = np.array([0.0, 1.0, 1.0]) 
            
            # Create mask image (Black background, Cyan mask)
            mask_image_np = np.zeros((h, w, 3), dtype=np.uint8)
            
            mask_bool = mask > 0
            
            # If mask shape doesn't match image shape, we need to resize mask
            if mask_bool.shape != (h, w):
                 # Resize mask using PIL
                 mask_pil_temp = Image.fromarray(mask_bool.astype(np.uint8) * 255)
                 mask_pil_temp = mask_pil_temp.resize((w, h), resample=Image.NEAREST)
                 mask_bool = np.array(mask_pil_temp) > 0

            mask_image_np[mask_bool] = (color * 255).astype(np.uint8)
            mask_image_pil = Image.fromarray(mask_image_np, mode='RGB')
            
            # Blend original image and mask (alpha=0.5)
            # This darkens the background (blending with black) and highlights the mask (blending with Cyan)
            image = Image.blend(image, mask_image_pil, alpha=0.5)

    # Overlay points if exists
    if points and labels:
        draw = ImageDraw.Draw(image)
        # Marker size
        r = 5 # radius
        for point, label in zip(points, labels):
            x, y = point
            color = "green" if label == 1 else "red"
            # Draw circle
            draw.ellipse((x-r, y-r, x+r, y+r), fill=color, outline="white")
            
    return image

def save_tracking_frame(image_path, mask, save_path):
    """
    Saves a single frame with the segmentation mask blended.
    Used during the propagation loop to generate frames for the video.
    """
    image = Image.open(image_path).convert("RGB")
    w, h = image.size
    
    # Prepare Mask Image
    # Use a high-contrast color (e.g., Lime Green or Cyan) instead of Tab10[0] (Blue)
    # Lime Green: (0, 1, 0), Cyan: (0, 1, 1), Magenta: (1, 0, 1)
    # Let's use a bright Cyan/Aqua for high visibility
    color = np.array([0.0, 1.0, 1.0, 0.6]) 
    
    # Handle mask dimensions
    if mask.ndim == 2:
        h_m, w_m = mask.shape
        mask_image = mask.reshape(h_m, w_m, 1) * color.reshape(1, 1, -1)
    else:
        # Compatible with (1, H, W)
        h_m, w_m = mask.shape[-2:]
        mask_image = mask.reshape(h_m, w_m, 1) * color.reshape(1, 1, -1)
        
    mask_image_rgb = mask_image[..., :3]
    mask_image_pil = Image.fromarray((mask_image_rgb * 255).astype(np.uint8), mode='RGB')
    mask_image_pil = mask_image_pil.resize((w, h)) 
    
    # Blend original image and mask
    combined_image = Image.blend(image, mask_image_pil, alpha=0.5)
    combined_image.save(save_path)

def create_trajectory_plot(project_dir, csv_path, output_path, smoothing=False, transparent=False):
    """
    Generates the trajectory plot.
    """
    if not os.path.exists(csv_path): return

    df = pd.read_csv(csv_path)
    x = df['x'].values
    y = df['y'].values
    
    # Get dimensions from first mask if available
    w, h = 1920, 1080
    masks_dir = os.path.join(project_dir, "masks")
    if os.path.exists(masks_dir):
        files = sorted([f for f in os.listdir(masks_dir) if f.endswith('.jpg')])
        if files:
            with Image.open(os.path.join(masks_dir, files[0])) as img:
                w, h = img.size

    # Setup Figure
    # Use 19.2 x 10.8 for 1920x1080 at 100dpi
    fig, ax = plt.subplots(figsize=(19.2, 10.8))
    ax.set_xlim(0, w)
    ax.set_ylim(0, h)
    ax.invert_yaxis()
    
    if transparent:
        fig.patch.set_alpha(0.0)
        ax.patch.set_alpha(0.0)
        ax.axis('off')
    else:
        plt.title(f"Object Trajectory ({w}x{h})")
    
    # Smoothing
    if smoothing and len(x) > 3:
        try:
            t = np.linspace(0, len(x) - 1, len(x) * 5)  
            spl_x = make_interp_spline(range(len(x)), x, k=3)  
            spl_y = make_interp_spline(range(len(y)), y, k=3)  
            smooth_x = spl_x(t)
            smooth_y = spl_y(t)
            ax.plot(smooth_x, smooth_y, color="yellow", alpha=0.8, linewidth=3)
        except Exception as e:
            print(f"Smoothing error: {e}")
            ax.plot(x, y, color="yellow", alpha=0.5, linewidth=3)
    else:
        ax.plot(x, y, color="yellow", alpha=0.5, linewidth=3)

    # Scatter points
    ax.scatter(x, y, color="yellow", alpha=0.6, s=150)
    
    plt.savefig(output_path, format="png", bbox_inches="tight", pad_inches=0.1, transparent=transparent)
    plt.close()

def generate_video_and_trajectory(project_dir, trajectory_data, fps=30):
    """
    Saves the trajectory CSV (smoothed), generates the trajectory plot,
    and uses FFmpeg to compile the masked frames into a video.
    """
    trajectories_dir = os.path.join(project_dir, "trajectories")
    videos_dir = os.path.join(project_dir, "videos")
    masks_dir = os.path.join(project_dir, "masks")
    
    os.makedirs(trajectories_dir, exist_ok=True)
    os.makedirs(videos_dir, exist_ok=True)
    
    # 1. Process CSV (Apply smoothing/filling zeros)
    df = pd.DataFrame(trajectory_data, columns=["x", "y"])
    df = replace_zero_coordinates(df) 
    csv_path = os.path.join(trajectories_dir, "trajectory.csv")
    df.to_csv(csv_path, index=False)
    
    # 2. Plot Trajectory (Standard)
    traj_img_path = os.path.join(trajectories_dir, "trajectory_white_bg.png")
    create_trajectory_plot(project_dir, csv_path, traj_img_path, smoothing=False, transparent=False)
    
    # 3. Plot Trajectory (Transparent)
    traj_trans_path = os.path.join(trajectories_dir, "trajectory_transparent_bg.png")
    create_trajectory_plot(project_dir, csv_path, traj_trans_path, smoothing=False, transparent=True)
    
    # 4. Compile Video using FFmpeg
    output_video_path = os.path.join(videos_dir, "output_tracked.mp4")
    if os.path.exists(output_video_path):
        os.remove(output_video_path)
        
    cmd = [
        "ffmpeg", "-y", # -y: Overwrite output files without asking
        "-framerate", str(fps),
        "-i", os.path.join(masks_dir, "%05d.jpg"),
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        output_video_path
    ]
    subprocess.run(cmd, check=True)
    
    return traj_img_path, output_video_path, csv_path