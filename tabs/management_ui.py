import gradio as gr
import os
import shutil
import json
from PIL import Image
from config import RESULTS_ROOT, VIDEO_UPLOAD_DIR
from tabs.tracking_ui import get_user_projects
from logic.visualizer import render_preview

def create_management_tab(username_state):
    with gr.Tab("4. Project Management") as tab:
        gr.Markdown("### Manage Your Projects")
        
        with gr.Row():
            project_dropdown = gr.Dropdown(label="Select Project", choices=[], interactive=True, scale=3)
            refresh_btn = gr.Button("🔄 Refresh", scale=1)
            delete_btn = gr.Button("🗑️ Delete Project", variant="stop", scale=1)
        
        # Confirmation for delete
        with gr.Row(visible=False) as delete_confirm_row:
            with gr.Column():
                gr.Markdown("### ⚠️ Are you sure you want to delete this project? This action cannot be undone.")
                with gr.Row():
                    confirm_delete_btn = gr.Button("Yes, Delete", variant="stop")
                    cancel_delete_btn = gr.Button("Cancel")

        status_msg = gr.Markdown("")
        
        with gr.Accordion("Project Details", open=True):
            metadata_display = gr.JSON(label="Project Metadata")
            
            with gr.Row():
                orig_video = gr.Video(label="Original Video", interactive=False)
                point_preview = gr.Image(label="First Frame & Points", interactive=False)
            
            with gr.Row():
                traj_plot = gr.Image(label="Trajectory Plot")
                res_video = gr.Video(label="Synthesized Video")
                
            gallery = gr.Gallery(label="Masked Frames", columns=6, height="auto")

        # --- Logic ---
        
        def refresh_list(user):
            return gr.Dropdown(choices=get_user_projects(user))
            
        refresh_btn.click(refresh_list, inputs=username_state, outputs=project_dropdown)
        tab.select(refresh_list, inputs=username_state, outputs=project_dropdown)
        
        def load_details(user, proj_name):
            if not user or not proj_name:
                return None, None, None, None, None, None
            
            proj_dir = os.path.join(RESULTS_ROOT, user, proj_name)
            metadata_path = os.path.join(proj_dir, "metadata", "metadata.json")
            
            # 1. Metadata
            metadata = {}
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, "r") as f:
                        metadata = json.load(f)
                except: pass
            
            # 2. Original Video
            vid_path = None
            if "original_video" in metadata:
                v_path = os.path.join(VIDEO_UPLOAD_DIR, metadata["original_video"])
                if os.path.exists(v_path):
                    vid_path = v_path
            
            # 3. First Frame Preview with Points
            preview_img = None
            frames_dir = os.path.join(proj_dir, "frames")
            frame0 = os.path.join(frames_dir, "00000.jpg")
            if os.path.exists(frame0):
                raw_points = metadata.get("points", [])
                points = []
                labels = []
                
                # Handle new format (list of dicts)
                if raw_points and len(raw_points) > 0 and isinstance(raw_points[0], dict):
                     for p in raw_points:
                         points.append([p['x'], p['y']])
                         labels.append(1 if p.get('type') == 'positive' else 0)
                
                try:
                    # render_preview expects points as list of lists
                    preview_img = render_preview(frame0, mask=None, points=points, labels=labels)
                except Exception as e:
                    print(f"Preview error: {e}")
                    preview_img = Image.open(frame0)

            # 4. Trajectory
            traj_path = os.path.join(proj_dir, "trajectories", "trajectory_white_bg.png")
            if not os.path.exists(traj_path):
                traj_path = os.path.join(proj_dir, "trajectories", "trajectory.png") # Fallback
            if not os.path.exists(traj_path): traj_path = None
            
            # 5. Result Video
            res_vid_path = os.path.join(proj_dir, "videos", "output_tracked.mp4")
            if not os.path.exists(res_vid_path): res_vid_path = None
            
            # 6. Gallery
            masks_dir = os.path.join(proj_dir, "masks")
            frames = []
            if os.path.exists(masks_dir):
                frame_files = sorted([os.path.join(masks_dir, f) for f in os.listdir(masks_dir) if f.endswith(".jpg")])
                frames = [(f, f"Frame {i}") for i, f in enumerate(frame_files)]
                
            return metadata, vid_path, preview_img, traj_path, res_vid_path, frames

        project_dropdown.change(
            load_details,
            inputs=[username_state, project_dropdown],
            outputs=[metadata_display, orig_video, point_preview, traj_plot, res_video, gallery]
        )
        
        # Delete Logic
        delete_btn.click(lambda: gr.update(visible=True), outputs=delete_confirm_row)
        cancel_delete_btn.click(lambda: gr.update(visible=False), outputs=delete_confirm_row)
        
        def delete_project(user, proj_name):
            if not user or not proj_name:
                return gr.update(visible=False), "Error: No project selected.", gr.Dropdown()
            
            proj_dir = os.path.join(RESULTS_ROOT, user, proj_name)
            try:
                shutil.rmtree(proj_dir)
                msg = f"✅ Project '{proj_name}' deleted successfully."
                # Refresh list
                new_list = get_user_projects(user)
                # Clear details
                return gr.update(visible=False), msg, gr.Dropdown(choices=new_list, value=None)
            except Exception as e:
                return gr.update(visible=False), f"❌ Error deleting project: {e}", gr.Dropdown()

        confirm_delete_btn.click(
            delete_project,
            inputs=[username_state, project_dropdown],
            outputs=[delete_confirm_row, status_msg, project_dropdown]
        ).then(
            # Clear details after delete
            lambda: (None, None, None, None, None, None),
            outputs=[metadata_display, orig_video, point_preview, traj_plot, res_video, gallery]
        )
