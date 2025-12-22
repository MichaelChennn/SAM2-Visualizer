# tabs/video_ui.py
import gradio as gr
import os
from logic.video_processor import create_project_folder, run_ffmpeg_cutting
from config import VIDEO_UPLOAD_DIR

def get_video_files():
    """Scans the VIDEO_UPLOAD_DIR for video files."""
    if not os.path.exists(VIDEO_UPLOAD_DIR):
        os.makedirs(VIDEO_UPLOAD_DIR, exist_ok=True)
    
    # Define supported video extensions
    extensions = {".mp4", ".avi", ".mov", ".mkv"}
    # List files and filter by extension
    files = [f for f in os.listdir(VIDEO_UPLOAD_DIR) if os.path.splitext(f)[1].lower() in extensions]
    return sorted(files)

def create_video_tab(username_state, project_dir_state):
    """
    Creates the Video Processing Tab layout and logic.
    """
    # Get initial list of video files
    video_list = get_video_files()

    with gr.Tab("1. Video Processing") as tab:
        gr.Markdown("### Select Video & Create Project")
        
        # --- UI Section 1: Video Selection & Project Config ---
        with gr.Group():
            video_dropdown = gr.Dropdown(choices=video_list, label="Select Video File", interactive=True)
            refresh_btn = gr.Button("🔄 Refresh List", size="sm")
            
            object_dropdown = gr.Dropdown(
                choices=["Body", "Head", "Hand", "Face", "Car"], 
                value="Body",
                label="Tracking Object (Folder Name)", 
                allow_custom_value=True, 
                interactive=True
            )
            
            create_proj_btn = gr.Button("📂 Create Project Folder", variant="secondary")

        # --- UI Section 2: Parameters Settings ---
        gr.Markdown("### Parameters Settings")

        with gr.Group():
            # Row 1: FPS
            with gr.Row():
                fps_slider = gr.Slider(
                    minimum=0.1, maximum=30.0, value=1.0, step=0.1, 
                    label="FPS (Frames Per Second)"
                )
            
            # Row 2: Time settings
            with gr.Row():
                start_time = gr.Textbox(label="Start Time", placeholder="e.g., 00:00:00")
                end_time = gr.Textbox(label="End Time", placeholder="e.g., 00:00:10")
            
            # Row 3: Quality slider
            quality_input = gr.Slider(minimum=1, maximum=31, value=2, step=1, label="Quality (2=High, 31=Low)")
            
            process_btn = gr.Button("✂️ Process Video (Cut Frames)", variant="primary")

        # --- UI Section 4: Confirmation Dialog ---
        with gr.Row(visible=False) as confirm_container:
            # Left spacer
            with gr.Column(scale=1): pass
            
            # Center content
            with gr.Column(scale=2):
                with gr.Group() as confirm_box:
                    gr.HTML("""
                        <div style="background-color: #fff7ed; border: 1px solid #fed7aa; border-radius: 8px; padding: 15px; margin-bottom: 10px;">
                            <h3 style="color: #c2410c; margin: 0; display: flex; align-items: center;">
                                ⚠️ Confirmation Required
                            </h3>
                            <p style="color: #9a3412; margin-top: 5px; font-size: 0.9em;">
                                This will create a new project folder and process the video.
                            </p>
                        </div>
                    """)
                    
                    confirm_text = gr.Markdown("Loading parameters...")
                    
                    with gr.Row():
                        cancel_btn = gr.Button("❌ Cancel", variant="secondary")
                        confirm_run_btn = gr.Button("✅ Create & Process", variant="primary")
            
            # Right spacer
            with gr.Column(scale=1): pass

        # --- UI Section 5: Results Display ---
        with gr.Accordion("Video Preview & Extracted Frames", open=True):
            video_preview = gr.Video(label="Original Video Preview", interactive=False)
            frames_gallery = gr.Gallery(label="Extracted Frames", columns=6, height="auto", object_fit="contain")
            
        msg_output = gr.Textbox(label="Status Message", lines=3, interactive=False)

        # --- Logic & Event Handling ---
        
        # 1. Refresh video list
        refresh_btn.click(lambda: gr.Dropdown(choices=get_video_files()), outputs=video_dropdown)
        
        # Auto-refresh when tab is selected
        tab.select(lambda: gr.Dropdown(choices=get_video_files()), outputs=video_dropdown)

        # 2. Update video preview when selection changes
        def update_preview(video_name):
            if not video_name: return None
            return os.path.join(VIDEO_UPLOAD_DIR, video_name)
        
        video_dropdown.change(update_preview, inputs=video_dropdown, outputs=video_preview)

        # 3. Check parameters and show confirmation box
        def check_parameters(video, obj, fps, start, end, q):
            # Validation
            if not video:
                raise gr.Error("No video selected.") 
            if not obj:
                raise gr.Error("Tracking object not defined.")
            
            # Formatting text
            s_txt = start if start else "Start"
            e_txt = end if end else "End"
            
            # Construct project name preview
            video_name_clean = os.path.splitext(os.path.basename(video))[0]
            safe_obj_name = "".join([c if c.isalnum() else "_" for c in obj])
            project_name = f"{video_name_clean}_{safe_obj_name}_Tracking"
            
            msg = f"""
            | Parameter | Value |
            | :--- | :--- |
            | **Project Name** | `{project_name}` |
            | **Video** | `{video}` |
            | **Object** | `{obj}` |
            | **FPS** | `{fps}` |
            | **Time** | `{s_txt}` -> `{e_txt}` |
            | **Quality** | `{q}` |
            """
            
            return msg, gr.update(visible=True)

        # 4. Create Project Logic
        def create_project_wrapper(user, video_name, track_obj):
            if not user:
                raise gr.Error("Please login first.")
            if not video_name:
                raise gr.Error("No video selected.")
            
            full_video_path = os.path.join(VIDEO_UPLOAD_DIR, video_name)
            try:
                proj_path, proj_name = create_project_folder(user, full_video_path, track_obj)
                gr.Info(f"Successfully created project: {proj_name}")
                # Return video path to force refresh preview
                return f"✅ Project Created: {proj_name}", proj_path, full_video_path
            except Exception as e:
                raise gr.Error(f"Error creating project: {str(e)}")

        # 5. Actual Processing Logic (Triggered after confirmation)
        def run_processing(user, video_name, track_obj, fps, q, start, end):
            if not user:
                raise gr.Error("Please login first.")
            
            full_video_path = os.path.join(VIDEO_UPLOAD_DIR, video_name)
            
            try:
                frames, frames_path, proj_path = run_ffmpeg_cutting(user, full_video_path, track_obj, fps, start, end, q)
                proj_name = os.path.basename(proj_path)
                
                # Convert frames list to (image, caption) tuples for Gallery
                gallery_data = [(f, f"Frame {i}") for i, f in enumerate(frames)]
                
                return gallery_data, f"✅ Processing Complete!\nProject: `{proj_name}`\nFrames saved at: {frames_path}", proj_path
            except Exception as e:
                import traceback
                traceback.print_exc()
                raise gr.Error(f"Processing Error: {str(e)}")

        # --- Event Wiring ---

        # Step 1: Create Project Button
        create_proj_btn.click(
            create_project_wrapper,
            inputs=[username_state, video_dropdown, object_dropdown],
            outputs=[msg_output, project_dir_state, video_preview]
        )

        # Step 2: Process Video Button -> Confirmation
        process_btn.click(
            check_parameters,
            inputs=[video_dropdown, object_dropdown, fps_slider, start_time, end_time, quality_input],
            outputs=[confirm_text, confirm_container] 
        )

        # Step 3: User clicks "Cancel"
        cancel_btn.click(
            lambda: gr.update(visible=False), 
            outputs=confirm_container
        )

        # Step 4: User clicks "Create & Process" (Confirm)
        confirm_run_btn.click(
            lambda: gr.update(visible=False), 
            outputs=confirm_container
        ).then(
            run_processing,
            inputs=[username_state, video_dropdown, object_dropdown, fps_slider, quality_input, start_time, end_time],
            outputs=[frames_gallery, msg_output, project_dir_state]
        )