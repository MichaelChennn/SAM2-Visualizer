# app.py
import gradio as gr
import os
from tabs.video_ui import create_video_tab
from tabs.tracking_ui import create_tracking_tab
from tabs.results_ui import create_results_tab
from tabs.management_ui import create_management_tab

def get_wsl_ip():
    """Helper to get the WSL2 IP address"""
    try:
        # This gets the IP address of the primary network interface
        cmd = "hostname -I | cut -d' ' -f1"
        return os.popen(cmd).read().strip()
    except:
        return "localhost"
    
def main():
    with gr.Blocks(title="SAM2 Object Tracking GUI") as demo:
        gr.Markdown("# SAM2 Visual Object Tracking Tool")
        
        # Global State Variables
        username_state = gr.State(value="")
        project_dir_state = gr.State(value="")  # Stores the full path of the current project
        
        # Login Section (Simplified)
        with gr.Row():
            with gr.Column(scale=2):
                name_input = gr.Textbox(label="Username", placeholder="e.g., User123")
            with gr.Column(scale=1):
                login_btn = gr.Button("Login")
        
        welcome_msg = gr.Markdown("")
            
        def login(name):
            if name:
                return name, f"Welcome **{name}**! Please select a video and define the tracking object."
            return "", "Please enter a valid Username."
            
        login_btn.click(
            login, 
            inputs=[name_input], 
            outputs=[username_state, welcome_msg]
        )
        
        # Initialize Tabs
        create_video_tab(username_state, project_dir_state)
        create_tracking_tab(username_state, project_dir_state)
        create_results_tab(username_state, project_dir_state)
        create_management_tab(username_state)
        
    # Launch the application
    ip = get_wsl_ip()
    # print(f"[INFO] Launching Gradio app at http://{ip}:7860")
    demo.launch(server_name=ip, share=False, server_port=7860)

if __name__ == "__main__":
    main()