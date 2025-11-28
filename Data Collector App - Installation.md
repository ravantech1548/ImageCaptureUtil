📸 Data Collector App - Installation Guide

This document provides step-by-step instructions to set up and run the Data Collector application on Windows and Linux/macOS systems.

Prerequisites

Python 3.8 or higher must be installed on your system.

A working webcam.

🪟 Windows Installation

Open your terminal (Command Prompt or PowerShell) and navigate to the folder where you have saved data_collector.py.

Create a Virtual Environment:
Run the following command to create an isolated environment named venv:

python -m venv venv


Activate the Environment:

.\venv\Scripts\activate


(You should see (venv) appear at the start of your command line).

Install Dependencies:
Install the required libraries:

pip install streamlit opencv-python-headless pillow numpy


Run the Application:
Start the Streamlit server:

streamlit run data_collector.py


🐧 Linux / macOS Installation

Open your terminal and navigate to the project directory.

Create a Virtual Environment:

python3 -m venv venv


Activate the Environment:

source venv/bin/activate


Install Dependencies:

pip install streamlit opencv-python-headless pillow numpy


Run the Application:

streamlit run data_collector.py


📦 Managing Requirements (Optional)

If you want to share this project or install it on another machine easily, you can use a requirements.txt file if one is provided.

Install from requirements file:

On a new machine, instead of typing all library names manually, you can run:

pip install -r requirements.txt
