import streamlit as st
import os
import cv2
import numpy as np
import glob
import time
import platform
import json
from PIL import Image

# --- Config Management ---
CONFIG_FILE = "config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                return json.load(f)
        except Exception:
            pass # Fallback to defaults if file is corrupt
    return {
        "crop_w": 300, "crop_h": 300, 
        "off_x": 170, "off_y": 90, 
        "cam_index": 0
    }

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

# --- Page Configuration ---
st.set_page_config(
    page_title="Data Collector",
    page_icon="📸",
    layout="wide"
)

# --- CSS for UI Tweaks ---
st.markdown("""
    <style>
        /* Compact buttons */
        div.stButton > button {
            width: 100%;
            height: 3em;
            font-weight: bold;
        }
        /* Hide default Streamlit menu for cleaner look */
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- Helper Functions ---
def get_next_sequence_number(folder_path, prefix):
    if not os.path.exists(folder_path):
        return 1
    pattern = os.path.join(folder_path, f"{prefix}_*.jpg")
    files = glob.glob(pattern)
    if not files:
        return 1
    max_num = 0
    for f in files:
        try:
            filename = os.path.basename(f)
            name_no_ext = os.path.splitext(filename)[0]
            num_part = name_no_ext.split('_')[-1]
            num = int(num_part)
            if num > max_num:
                max_num = num
        except ValueError:
            continue
    return max_num + 1

def save_frame_to_disk(frame_bgr, folder, prefix):
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    seq_num = get_next_sequence_number(folder, prefix)
    filename = f"{prefix}_{seq_num:04d}.jpg"
    full_path = os.path.join(folder, filename)
    cv2.imwrite(full_path, frame_bgr, [cv2.IMWRITE_JPEG_QUALITY, 95])
    return filename

def get_camera_backend():
    if platform.system() == 'Windows':
        return cv2.CAP_DSHOW
    else:
        return cv2.CAP_ANY

# --- Session State Initialization ---
if 'camera_active' not in st.session_state:
    st.session_state.camera_active = False
if 'cap' not in st.session_state:
    st.session_state.cap = None

# --- Load Config ---
config = load_config()

# --- Main Layout ---
st.title("📸 Continuous Data Collector")

# Sidebar
with st.sidebar:
    st.header("📁 Settings")
    base_dir = st.text_input("Root Directory", value="dataset")
    class_name = st.text_input("Class Name", value="object_01")
    target_folder = os.path.join(base_dir, class_name)
    
    st.divider()
    
    st.header("✂️ Crop Config")
    st.caption("Settings auto-save to `config.json`")
    
    # Load default values from config
    cam_index = st.number_input("Camera Index", value=config.get("cam_index", 0), step=1)
    
    c1, c2 = st.columns(2)
    crop_w = c1.number_input("Width", value=config.get("crop_w", 300))
    crop_h = c2.number_input("Height", value=config.get("crop_h", 300))
    off_x = c1.number_input("X Offset", value=config.get("off_x", 170))
    off_y = c2.number_input("Y Offset", value=config.get("off_y", 90))

    # Check for changes and save to file
    current_config = {
        "crop_w": crop_w, "crop_h": crop_h, 
        "off_x": off_x, "off_y": off_y, 
        "cam_index": cam_index
    }
    
    if current_config != config:
        save_config(current_config)
        # We don't need a toast here as it might be annoying on every click, 
        # but the file is updated instantly.

# Stats
seq_num = get_next_sequence_number(target_folder, class_name)
count = len(glob.glob(os.path.join(target_folder, "*.jpg"))) if os.path.exists(target_folder) else 0

col_stat1, col_stat2 = st.columns(2)
col_stat1.metric("Next Sequence", f"#{seq_num:04d}")
col_stat2.metric("Images Collected", count)

st.divider()

# --- Camera Logic ---

# Toggle Button
if st.button("🔴 Stop Camera" if st.session_state.camera_active else "▶️ Start Camera", type="secondary"):
    st.session_state.camera_active = not st.session_state.camera_active
    if not st.session_state.camera_active and st.session_state.cap:
        st.session_state.cap.release()
        st.session_state.cap = None

if st.session_state.camera_active:
    # Initialize if needed
    if st.session_state.cap is None or not st.session_state.cap.isOpened():
        backend = get_camera_backend()
        st.session_state.cap = cv2.VideoCapture(cam_index, backend)
        # Optimize for speed
        st.session_state.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        st.session_state.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        st.session_state.cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

    # Read Frame
    ret, frame = st.session_state.cap.read()
    
    if not ret:
        st.error("Failed to read frame. Check camera connection.")
        st.session_state.camera_active = False
        st.rerun()
    else:
        # 1. Prepare Data
        h, w = frame.shape[:2]
        x1 = min(off_x, w-1)
        y1 = min(off_y, h-1)
        x2 = min(off_x + crop_w, w)
        y2 = min(off_y + crop_h, h)
        
        # 2. Draw Overlay (On a copy, so we save clean data later)
        frame_display = frame.copy()
        cv2.rectangle(frame_display, (x1, y1), (x2, y2), (0, 0, 255), 3) # Red Box
        
        # Add visual guide text
        cv2.putText(frame_display, "Align Object Here", (x1, y1-10), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)

        # 3. Convert for Streamlit
        frame_rgb = cv2.cvtColor(frame_display, cv2.COLOR_BGR2RGB)
        
        # 4. Layout: Image on Left, Controls on Right
        col_img, col_ctrl = st.columns([3, 1])
        
        with col_img:
            st.image(frame_rgb, channels="RGB", use_container_width=True)
            
        with col_ctrl:
            st.markdown("### Action")
            # The Capture Button
            # When clicked, Streamlit re-runs the script. 
            # We detect the click, Save, and then the script naturally loops back to a new frame.
            if st.button("📸 CAPTURE", type="primary"):
                # Crop actual frame
                roi = frame[y1:y2, x1:x2]
                saved_name = save_frame_to_disk(roi, target_folder, class_name)
                
                # Show Feedback
                st.toast(f"✅ Saved {saved_name}!", icon="💾")
                
                # Small delay to prevent double-clicks
                time.sleep(0.1)

        # 5. Continuous Loop Trigger
        # This causes the script to rerun immediately, creating the "Live Feed" effect
        time.sleep(0.01) # Tiny sleep to prevent CPU spiking to 100%
        st.rerun()

else:
    st.info("Click 'Start Camera' to begin.")
