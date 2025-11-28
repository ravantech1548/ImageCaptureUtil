import streamlit as st
import os
import cv2
import numpy as np
from PIL import Image, ImageDraw
import glob

# --- Page Configuration ---
st.set_page_config(
    page_title="Data Collector",
    page_icon="📸",
    layout="wide"
)

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

def save_image(image_pil, folder, prefix, quality=95):
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    seq_num = get_next_sequence_number(folder, prefix)
    filename = f"{prefix}_{seq_num:04d}.jpg"
    full_path = os.path.join(folder, filename)
    image_pil.save(full_path, "JPEG", quality=quality)
    return filename, seq_num

# --- Main App Layout ---

st.title("📸 Dataset Capture & Crop Tool")

# Sidebar: Configurations
with st.sidebar:
    st.header("📁 Storage Settings")
    base_dir = st.text_input("Root Directory", value="dataset")
    class_name = st.text_input("Class Name (Folder)", value="object_01")
    target_folder = os.path.join(base_dir, class_name)
    st.info(f"Saving to:\n`{target_folder}`")
    
    st.divider()
    
    st.header("✂️ Crop & Overlay Config")
    
    # Camera Calibration: Essential for aligning the CSS overlay with the actual camera pixels
    with st.expander("⚙️ Camera Calibration (Important)", expanded=True):
        st.caption("Set this to your camera's actual resolution so the red box overlay aligns correctly.")
        # Added min_value to prevent division by zero
        cam_w = st.number_input("Camera Width (px)", min_value=100, value=640, step=10)
        cam_h = st.number_input("Camera Height (px)", min_value=100, value=480, step=10)
    
    st.subheader("ROI Settings (Pixels)")
    c1, c2 = st.columns(2)
    with c1:
        crop_width = st.number_input("Width", min_value=10, max_value=cam_w, value=300)
        crop_height = st.number_input("Height", min_value=10, max_value=cam_h, value=300)
    with c2:
        offset_x = st.number_input("X Offset", min_value=0, max_value=cam_w, value=170)
        offset_y = st.number_input("Y Offset", min_value=0, max_value=cam_h, value=90)

# --- CSS Injection for Live Overlay ---
# We calculate percentages to position the red box on the responsive camera widget
pct_left = (offset_x / cam_w) * 100
pct_top = (offset_y / cam_h) * 100
pct_width = (crop_width / cam_w) * 100
pct_height = (crop_height / cam_h) * 100

overlay_css = f"""
<style>
    /* Make the camera container relative */
    div[data-testid="stCameraInput"] > label + div {{
        position: relative;
    }}
    
    /* Draw the red box on top of the video container */
    div[data-testid="stCameraInput"] > label + div::after {{
        content: '';
        position: absolute;
        top: {pct_top}%;
        left: {pct_left}%;
        width: {pct_width}%;
        height: {pct_height}%;
        border: 4px solid #FF0000; /* Red border */
        z-index: 1000; /* High z-index */
        pointer-events: none; /* Allow clicks to pass through */
        box-shadow: 0 0 0 9999px rgba(0, 0, 0, 0.5); /* Dim outside area */
    }}
    
    .block-container {{ padding-top: 1rem; }}
    div[data-testid="stMetric"] {{
        background-color: #f0f2f6;
        padding: 5px;
        border-radius: 5px;
    }}
</style>
"""
st.markdown(overlay_css, unsafe_allow_html=True)

# --- State Management ---
if 'cam_id' not in st.session_state:
    st.session_state.cam_id = 0
if 'last_saved' not in st.session_state:
    st.session_state.last_saved = None

# --- Top Stats ---
current_seq = get_next_sequence_number(target_folder, class_name)
col1, col2, col3 = st.columns([1, 1, 2])
with col1:
    st.metric("Next ID", f"#{current_seq:04d}")
with col2:
    count = len(glob.glob(os.path.join(target_folder, "*.jpg"))) if os.path.exists(target_folder) else 0
    st.metric("Count", count)
with col3:
    if st.session_state.last_saved:
        st.success(f"✅ Saved: {st.session_state.last_saved}")

# --- Camera & Processing ---
# Note: The CSS above draws the red box directly on this widget
cam_key = f"camera_{st.session_state.cam_id}"
camera_image = st.camera_input("Live Feed (Align object in red box)", key=cam_key)

if camera_image:
    # 1. Load & Process
    img = Image.open(camera_image)
    img_w, img_h = img.size
    
    # 2. Crop Logic - SCALING FIX
    # Calculate ratio between 'Calibration' settings and Actual Image
    # This ensures the crop happens exactly where the red box was, 
    # even if the camera resolution is different from 640x480.
    scale_x = img_w / cam_w
    scale_y = img_h / cam_h
    
    real_x = int(offset_x * scale_x)
    real_y = int(offset_y * scale_y)
    real_w = int(crop_width * scale_x)
    real_h = int(crop_height * scale_y)
    
    # Calculate safe bounds for crop
    safe_x = max(0, min(real_x, img_w - 1))
    safe_y = max(0, min(real_y, img_h - 1))
    safe_w = max(1, min(real_w, img_w - safe_x))
    safe_h = max(1, min(real_h, img_h - safe_y))
    
    img_cropped = img.crop((safe_x, safe_y, safe_x + safe_w, safe_y + safe_h))

    # 3. Create Verification Image (Draw red box on static image)
    img_with_box = img.copy()
    draw = ImageDraw.Draw(img_with_box)
    draw.rectangle([safe_x, safe_y, safe_x + safe_w, safe_y + safe_h], outline="red", width=5)
    
    # 4. Display Results & Actions
    st.divider()
    r_col1, r_col2, r_col3 = st.columns([1, 1, 1])
    
    with r_col1:
        st.markdown("### 1. Capture Context")
        st.image(img_with_box, caption=f"Full Frame ({img_w}x{img_h})", use_container_width=True)
        
    with r_col2:
        st.markdown("### 2. Crop Result")
        st.image(img_cropped, caption=f"To be saved ({safe_w}x{safe_h})", width=250)
        
    with r_col3:
        st.markdown("### 3. Action")
        st.write("Check the images. If correct, save.")
        
        # Save Button
        if st.button("💾 Save & Clear Feed", type="primary", use_container_width=True):
            filename, seq = save_image(img_cropped, target_folder, class_name)
            st.session_state.last_saved = filename
            st.session_state.cam_id += 1 # Increment ID to reset camera
            st.rerun()
            
else:
    st.info("👆 Use the red box guide above to align your object.")