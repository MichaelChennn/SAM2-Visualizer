# tabs/tracking_ui.py
import gradio as gr
import os
import json
from PIL import Image
from logic.tracker import SAM2Tracker
from logic.visualizer import generate_video_and_trajectory, render_preview
from config import RESULTS_ROOT

# Initialize global model instance
tracker_model = SAM2Tracker()

def get_user_projects(username):
    """
    Scans the 'results/username/' directory and returns a list of available project folders.
    """
    if not username: return []
    user_path = os.path.join(RESULTS_ROOT, username)
    if not os.path.exists(user_path): return []
    # Return only directories
    return sorted([d for d in os.listdir(user_path) if os.path.isdir(os.path.join(user_path, d))])

def create_tracking_tab(username_state, project_dir_state):
    """
    Creates the Object Tracking UI Tab.
    Includes visual feedback for point selection.
    """
    # UI State Variables
    points_state = gr.State([])
    labels_state = gr.State([])
    current_frame0_path = gr.State(None)
    
    with gr.Tab("2. Object Tracking") as tab:
        gr.Markdown("### 1. Select Existing Project")
        
        # --- Section 1: Project Selection ---
        with gr.Column():
            project_dropdown = gr.Dropdown(label="Available Projects", choices=[], interactive=True)
            refresh_proj_btn = gr.Button("🔄 Refresh", size="sm")

        gr.Markdown("### 2. Select Object (Max 2 Points)")
        
        # --- Section 2: Image Interaction ---
        with gr.Row():
            # Left Column: Interactive Image
            with gr.Column(scale=3):
                # NOTE: This image component is now an OUTPUT as well, to show the dots
                input_image = gr.Image(label="Click to Add Points", type="pil", interactive=False)
            
            # Right Column: Controls
            with gr.Column(scale=1):
                point_type = gr.Radio(["Positive (+)", "Negative (-)"], value="Positive (+)", label="Click Type")
                undo_btn = gr.Button("Undo Last Point")
                clear_btn = gr.Button("Clear All Points")
                
                # Display selected points info
                points_info = gr.Markdown("**Selected Points:**\nNone")
                # Hidden warning message
                warning_msg = gr.Markdown("", visible=False) 
        
        # --- Section 3: Actions ---
        gr.Markdown("### 3. Preview & Run")
        with gr.Column():
            preview_btn = gr.Button("👁️ Preview Mask (Frame 0)", variant="secondary")
            
        # --- Section 4: Results Display ---
        with gr.Row():
            preview_output = gr.Image(label="Mask Preview Result", interactive=False)
            
        # --- Section 5: Start Inference ---
        gr.Markdown("### 4. Start Tracking")
        run_btn = gr.Button("🚀 Start Tracking Inference", variant="primary")
        status_output = gr.Textbox(label="Status Log")

        # ====== Logic Implementation ======

        # 1. Refresh Projects List
        def refresh_list(user):
            projs = get_user_projects(user)
            return gr.Dropdown(choices=projs)
            
        refresh_proj_btn.click(refresh_list, inputs=username_state, outputs=project_dropdown)
        
        # Auto-refresh when tab is selected
        tab.select(refresh_list, inputs=username_state, outputs=project_dropdown)

        # 2. Load Project & Display Frame 0 (Clean Image)
        def load_project(user, proj_name):
            if not user or not proj_name:
                return None, None, "Please select a project.", None
            
            proj_dir = os.path.join(RESULTS_ROOT, user, proj_name)
            frames_dir = os.path.join(proj_dir, "frames")
            frame0 = os.path.join(frames_dir, "00000.jpg")
            
            if not os.path.exists(frame0):
                return None, None, "Error: Frame 0 not found.", proj_dir
            
            # Initialize Tracker Session
            try:
                tracker_model.init_session(frames_dir)
                status = f"Loaded: {proj_name}. Tracker Ready."
            except Exception as e:
                status = f"Tracker Init Error: {e}"
            
            # Reset states
            return Image.open(frame0), frame0, status, proj_dir, [], []

        project_dropdown.change(
            load_project, 
            inputs=[username_state, project_dropdown], 
            outputs=[input_image, current_frame0_path, status_output, project_dir_state, points_state, labels_state]
        )

        # --- Helper to format points text ---
        def format_points_text(points, labels):
            if not points: return "**Selected Points:**\nNone"
            return "**Selected Points:**\n" + "\n".join([f"P{i+1}: {p} ({'Pos' if l==1 else 'Neg'})" for i, (p, l) in enumerate(zip(points, labels))])

        # 3. Handle Image Clicks (Visual Feedback + Max 2 Limit)
        def on_select(frame0_path, p_type, points, labels, evt: gr.SelectData):
            # A. Check Limit
            if len(points) >= 2:
                # Re-render existing points (just in case)
                marked_img = render_preview(frame0_path, mask=None, points=points, labels=labels)
                return points, labels, format_points_text(points, labels), gr.update(value="⚠️ Limit Reached: Max 2 Points!", visible=True), marked_img
            
            # B. Add Point
            x, y = evt.index[0], evt.index[1]
            label = 1 if "Positive" in p_type else 0
            
            points.append([x, y])
            labels.append(label)
            
            # C. Render Visual Feedback (Draw points on the image)
            # We pass mask=None so it only draws the points
            marked_img = render_preview(frame0_path, mask=None, points=points, labels=labels)
            
            return points, labels, format_points_text(points, labels), gr.update(visible=False), marked_img

        input_image.select(
            on_select,
            inputs=[current_frame0_path, point_type, points_state, labels_state],
            outputs=[points_state, labels_state, points_info, warning_msg, input_image] # Updates input_image
        )

        # 4. Undo Logic
        def undo(frame0_path, points, labels):
            if points: points.pop()
            if labels: labels.pop()
            
            # Re-render image with remaining points
            if not points:
                # If no points left, just load the clean original image
                marked_img = Image.open(frame0_path) if frame0_path else None
            else:
                marked_img = render_preview(frame0_path, mask=None, points=points, labels=labels)
                
            return points, labels, format_points_text(points, labels), gr.update(visible=False), marked_img

        undo_btn.click(
            undo, 
            inputs=[current_frame0_path, points_state, labels_state], 
            outputs=[points_state, labels_state, points_info, warning_msg, input_image]
        )
        
        # 5. Clear Logic
        def clear(frame0_path):
            # Load clean original image
            clean_img = Image.open(frame0_path) if frame0_path else None
            return [], [], format_points_text([], []), gr.update(visible=False), clean_img
            
        clear_btn.click(
            clear, 
            inputs=[current_frame0_path],
            outputs=[points_state, labels_state, points_info, warning_msg, input_image]
        )

        # 6. Preview Mask Logic
        def run_preview(frame0, points, labels):
            if not frame0 or not points:
                return None, "Please select points first."
            
            try:
                mask = tracker_model.get_first_frame_mask(points, labels)
                # Render Preview: Image + Mask + Points
                preview_img = render_preview(frame0, mask, points, labels)
                return preview_img, "Preview generated successfully."
            except Exception as e:
                import traceback
                traceback.print_exc()
                return None, f"Preview Error: {str(e)}"

        preview_btn.click(
            run_preview,
            inputs=[current_frame0_path, points_state, labels_state],
            outputs=[preview_output, status_output]
        )

        # 7. Full Inference Logic
        def run_full_inference(proj_dir, points, labels):
            if not proj_dir or not points:
                return "Error: Missing project or points."
            
            frames_dir = os.path.join(proj_dir, "frames")
            masks_dir = os.path.join(proj_dir, "masks")
            metadata_path = os.path.join(proj_dir, "metadata", "metadata.json")
            
            # Update Metadata with points
            if os.path.exists(metadata_path):
                try:
                    with open(metadata_path, "r") as f:
                        meta = json.load(f)
                    
                    # Save structured points for better readability
                    # e.g. [{"x": 100, "y": 200, "type": "positive"}, ...]
                    structured_points = []
                    for p, l in zip(points, labels):
                        structured_points.append({
                            "x": p[0],
                            "y": p[1],
                            "type": "positive" if l == 1 else "negative"
                        })
                    meta["points"] = structured_points
                    
                    # Remove legacy fields if they exist
                    if "labels" in meta:
                        del meta["labels"]
                    if "points_details" in meta:
                        del meta["points_details"]
                    
                    with open(metadata_path, "w") as f:
                        json.dump(meta, f, indent=4)
                except Exception as e:
                    print(f"Error updating metadata: {e}")
            
            try:
                trajectory = tracker_model.propagate(frames_dir, masks_dir, points, labels)
                generate_video_and_trajectory(proj_dir, trajectory)
                return "Inference & Video Generation Complete! Check 'Results' tab."
            except RuntimeError as e:
                # Catch CUDA OOM or other runtime errors
                err_msg = str(e)
                if "out of memory" in err_msg.lower():
                    return (
                        f"❌ CUDA Out of Memory Error!\n\n"
                        f"Details: {err_msg}\n\n"
                        f"Suggestion: The video resolution or frame count might be too high for your GPU.\n"
                        f"Please go back to the 'Video Processing' tab and try:\n"
                        f"1. Reducing the FPS (e.g., to 0.5 or lower).\n"
                        f"2. Reducing the Quality (e.g., to 5 or higher q-scale).\n"
                        f"3. Re-process the video to generate fewer/smaller frames."
                    )
                return f"Runtime Error: {err_msg}"
            except Exception as e:
                import traceback
                traceback.print_exc()
                return f"Inference Failed: {str(e)}"

        run_btn.click(
            run_full_inference,
            inputs=[project_dir_state, points_state, labels_state],
            outputs=[status_output]
        )