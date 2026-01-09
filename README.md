# SAM2-Visualizer
## Prepare Environment
```bash
conda create -n sam2 python=3.10 -y
```
- follow [here](https://github.com/facebookresearch/sam2) to install SAM2
- if is already installed, just activate the conda environment:
```bash
conda activate sam2
pip install -r requirements.txt
```

## Put the video files in the `videos` folder.
- if the video is too long (e.g. >10 minutes), please cut it into several short clips to avoid memory overflow.

## Run the app
```bash
python app.py
```

## How to use the application
- please refer to [instruction.md](instruction.md) for detailed instructions with images.

## File Structure
`videos/`: place the input video files here

`results/`: the output results will be saved here in the username subfolder

`logic/`: contains the code for the main logic of video processing and object tracking

`tabs/`: contains the code for each tab in the web user interface

`app.py`: the main application file to run the web interface

`config.py`: configuration file for setting parameters

`instruction.mp4`: a video tutorial on how to use the application

`requirements.txt`: list of required Python packages to install
