# tabs/results_ui.py
import gradio as gr
import os
import json
from logic.visualizer import create_trajectory_plot
from tabs.tracking_ui import get_user_projects
from config import RESULTS_ROOT

def create_results_tab(username_state, project_dir_state):
    """
    Creates the Results Viewing Tab layout.
    """
    with gr.Tab("3. View Results") as tab:
        
        # --- Project Selection ---
        with gr.Row():
            project_dropdown = gr.Dropdown(label="Select Project to View", choices=[], interactive=True, scale=4)
            refresh_proj_btn = gr.Button("🔄 Refresh List", scale=1)
            
        refresh_btn = gr.Button("Refresh Results", visible=False) # Hidden, triggered by dropdown
        
        # Status Message
        status_msg = gr.Markdown("", visible=False)
        
        # Metadata Display
        metadata_display = gr.JSON(label="Project Metadata")
        
        with gr.Row():
            # Left: Trajectory Plot with Controls
            with gr.Column():
                plot_type_radio = gr.Radio(["Standard (White BG)", "Transparent BG"], value="Standard (White BG)", label="Plot Type")
                traj_image = gr.Image(label="Object Trajectory Plot")
                with gr.Row():
                    smoothing_chk = gr.Checkbox(label="Enable Smoothing", value=False)
                    update_plot_btn = gr.Button("Update Plot")
                download_files = gr.File(label="Download Results (CSV & Plots)", file_count="multiple")
            
            # Right: Video
            with gr.Column():
                result_video = gr.Video(label="Mask Synthesized Video")
        
        # Bottom: Gallery
        gr.Markdown("### Masked Frames Gallery")
        gallery = gr.Gallery(label="Masked Frames", columns=6, height="auto")
        
        # --- Logic ---
        
        # 1. Refresh Projects List
        def refresh_list(user):
            projs = get_user_projects(user)
            return gr.Dropdown(choices=projs)
            
        refresh_proj_btn.click(refresh_list, inputs=username_state, outputs=project_dropdown)
        
        # Auto-refresh when tab is selected
        tab.select(refresh_list, inputs=username_state, outputs=project_dropdown)
        
        # 2. Select Project Helper
        def select_project(user, proj_name):
            if not user or not proj_name:
                return None
            return os.path.join(RESULTS_ROOT, user, proj_name)

        # 3. Load Results Logic
        def load_results(proj_dir):
            if not proj_dir:
                return None, None, None, [], False, gr.update(visible=False), None
            
            # Updated filenames
            traj_path = os.path.join(proj_dir, "trajectories", "trajectory_white_bg.png")
            traj_trans_path = os.path.join(proj_dir, "trajectories", "trajectory_transparent_bg.png")
            
            # Fallback for old projects
            if not os.path.exists(traj_path) and os.path.exists(os.path.join(proj_dir, "trajectories", "trajectory.png")):
                traj_path = os.path.join(proj_dir, "trajectories", "trajectory.png")
            if not os.path.exists(traj_trans_path) and os.path.exists(os.path.join(proj_dir, "trajectories", "trajectory_transparent.png")):
                traj_trans_path = os.path.join(proj_dir, "trajectories", "trajectory_transparent.png")

            vid_path = os.path.join(proj_dir, "videos", "output_tracked.mp4")
            csv_path = os.path.join(proj_dir, "trajectories", "trajectory.csv")
            metadata_path = os.path.join(proj_dir, "metadata", "metadata.json")
            
            # Load Metadata
            metadata = {}
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                except:
                    pass
            
            # Check if results exist
            has_results = os.path.exists(traj_path) or os.path.exists(vid_path)
            
            if not has_results:
                 return None, None, None, [], False, gr.update(value="### ⚠️ No results found.\nPlease go to the **Object Tracking** tab and run inference first.", visible=True), metadata

            # Load frames
            masks_dir = os.path.join(proj_dir, "masks")
            frames = []
            if os.path.exists(masks_dir):
                frame_files = sorted([os.path.join(masks_dir, f) for f in os.listdir(masks_dir) if f.endswith(".jpg")])
                # Convert to (image, caption) tuples
                frames = [(f, f"Frame {i}") for i, f in enumerate(frame_files)]
            
            # Prepare download list
            downloads = []
            if os.path.exists(csv_path): downloads.append(csv_path)
            if os.path.exists(traj_path): downloads.append(traj_path)
            if os.path.exists(traj_trans_path): downloads.append(traj_trans_path)
            
            traj_smooth_path = os.path.join(proj_dir, "trajectories", "trajectory_white_bg_smoothed.png")
            traj_trans_smooth_path = os.path.join(proj_dir, "trajectories", "trajectory_transparent_bg_smoothed.png")
            
            # Auto-generate smoothed plots if missing but CSV exists
            if os.path.exists(csv_path):
                if not os.path.exists(traj_smooth_path):
                    try:
                        create_trajectory_plot(proj_dir, csv_path, traj_smooth_path, smoothing=True, transparent=False)
                    except Exception as e:
                        print(f"Error generating smoothed white bg plot: {e}")

                if not os.path.exists(traj_trans_smooth_path):
                    try:
                        create_trajectory_plot(proj_dir, csv_path, traj_trans_smooth_path, smoothing=True, transparent=True)
                    except Exception as e:
                         print(f"Error generating smoothed transparent bg plot: {e}")
            
            if os.path.exists(traj_smooth_path): downloads.append(traj_smooth_path)
            if os.path.exists(traj_trans_smooth_path): downloads.append(traj_trans_smooth_path)

            return (
                traj_path if os.path.exists(traj_path) else None,
                vid_path if os.path.exists(vid_path) else None,
                downloads,
                frames,
                False, # Reset smoothing checkbox
                gr.update(visible=False), # Hide warning
                metadata
            )

        # 4. Event Wiring
        
        # When dropdown changes:
        # 1. Update the global project_dir_state
        # 2. IMMEDIATELY trigger load_results using the new state
        project_dropdown.change(
            select_project,
            inputs=[username_state, project_dropdown],
            outputs=[project_dir_state]
        ).then(
            load_results,
            inputs=[project_dir_state],
            outputs=[traj_image, result_video, download_files, gallery, smoothing_chk, status_msg, metadata_display]
        )
        
        # Also trigger load when project_dir_state changes from other tabs
        project_dir_state.change(
            load_results,
            inputs=[project_dir_state],
            outputs=[traj_image, result_video, download_files, gallery, smoothing_chk, status_msg, metadata_display]
        )
        
        # Manual refresh button
        refresh_btn.click(
            load_results,
            inputs=[project_dir_state],
            outputs=[traj_image, result_video, download_files, gallery, smoothing_chk, status_msg, metadata_display]
        )
        
        def change_plot_view(proj_dir, plot_type, smoothing):
            if not proj_dir: return None
            
            suffix = "_smoothed.png" if smoothing else ".png"
            bg = "transparent_bg" if "Transparent" in plot_type else "white_bg"
            
            # Construct expected path
            # e.g. trajectory_white_bg.png or trajectory_white_bg_smoothed.png
            filename = f"trajectory_{bg}{suffix}"
            path = os.path.join(proj_dir, "trajectories", filename)
            
            # Fallback logic for legacy or missing smoothed files
            if not os.path.exists(path):
                # Try unsmoothed if smoothed missing
                if smoothing:
                     path = os.path.join(proj_dir, "trajectories", f"trajectory_{bg}.png")
                
                # Try legacy names
                if not os.path.exists(path):
                     legacy_name = "trajectory_transparent.png" if "Transparent" in plot_type else "trajectory.png"
                     path = os.path.join(proj_dir, "trajectories", legacy_name)

            return path if os.path.exists(path) else None

        plot_type_radio.change(
            change_plot_view,
            inputs=[project_dir_state, plot_type_radio, smoothing_chk],
            outputs=[traj_image]
        )
        
        # Also update view when smoothing checkbox is toggled (preview only, doesn't re-generate)
        smoothing_chk.change(
            change_plot_view,
            inputs=[project_dir_state, plot_type_radio, smoothing_chk],
            outputs=[traj_image]
        )
        
        def update_plot(proj_dir, smoothing, plot_type):
            if not proj_dir: return None, []
            
            csv_path = os.path.join(proj_dir, "trajectories", "trajectory.csv")
            
            # Define all potential output paths
            paths = {
                (False, "Standard"): os.path.join(proj_dir, "trajectories", "trajectory_white_bg.png"),
                (False, "Transparent"): os.path.join(proj_dir, "trajectories", "trajectory_transparent_bg.png"),
                (True, "Standard"): os.path.join(proj_dir, "trajectories", "trajectory_white_bg_smoothed.png"),
                (True, "Transparent"): os.path.join(proj_dir, "trajectories", "trajectory_transparent_bg_smoothed.png"),
            }
            
            if os.path.exists(csv_path):
                # Re-generate the specific requested one to ensure it reflects current smoothing setting
                # We interpret "Update Plot" as "Force Re-generate requested plot"
                target_key = (smoothing, "Transparent" if "Transparent" in plot_type else "Standard")
                target_path = paths[target_key]
                
                is_transparent = "Transparent" in plot_type
                create_trajectory_plot(proj_dir, csv_path, target_path, smoothing=smoothing, transparent=is_transparent)
                
                # Recalculate component lists
                downloads = []
                # Add CSV
                downloads.append(csv_path)
                # Add all existing plot files to download list
                for p in paths.values():
                    if os.path.exists(p):
                        downloads.append(p)
                
                return target_path, downloads
            return None, []

        update_plot_btn.click(
            update_plot,
            inputs=[project_dir_state, smoothing_chk, plot_type_radio],
            outputs=[traj_image, download_files]
        )