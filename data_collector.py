import streamlit as st
import os
import cv2
import numpy as np
import glob
import time
import platform

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

def save_frame(frame, folder, prefix, quality=95):
    """Saves the frame using OpenCV"""
    if not os.path.exists(folder):
        os.makedirs(folder, exist_ok=True)
    
    seq_num = get_next_sequence_number(folder, prefix)
    filename = f"{prefix}_{seq_num:04d}.jpg"
    full_path = os.path.join(folder, filename)
    
    # Write using OpenCV
    cv2.imwrite(full_path, frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
    return filename

def get_camera_backend():
    """Returns the appropriate backend for the OS"""
    if platform.system() == 'Windows':
        return cv2.CAP_DSHOW # DirectShow is more robust on Windows
    else:
        return cv2.CAP_ANY # Auto-detect on Linux/Mac

# --- Main App Layout ---
st.title("📸 Native Data Collector")
st.markdown("Use this tool to capture high-quality datasets using your local camera hardware.")

# Sidebar: Configurations
with st.sidebar:
    st.header("📁 Storage Settings")
    base_dir = st.text_input("Root Directory", value="dataset")
    class_name = st.text_input("Class Name (Folder)", value="object_01")
    target_folder = os.path.join(base_dir, class_name)
    st.info(f"Saving to:\n`{target_folder}`")
    
    st.divider()
    
    st.header("✂️ ROI Configuration")
    st.caption("Adjust the Red Box.")
    
    # Independent settings, no calibration needed for native window
    cam_index = st.number_input("Camera Index", value=0, step=1, help="Try 0, 1, or 2 if the camera doesn't open.")
    
    c1, c2 = st.columns(2)
    with c1:
        crop_w = st.number_input("Crop Width", value=300, step=10)
        crop_h = st.number_input("Crop Height", value=300, step=10)
    with c2:
        off_x = st.number_input("X Offset", value=170, step=10)
        off_y = st.number_input("Y Offset", value=90, step=10)

# --- App Logic ---

# Check stats
current_seq = get_next_sequence_number(target_folder, class_name)
total_files = len(glob.glob(os.path.join(target_folder, "*.jpg"))) if os.path.exists(target_folder) else 0

# Stats Bar
col1, col2, col3 = st.columns(3)
col1.metric("Next Sequence", f"#{current_seq:04d}")
col2.metric("Total Collected", total_files)

# Action Area
st.divider()
st.subheader("🚀 Live Capture Mode")
st.write("""
**Instructions:**
1. **Close any other apps** (like Zoom or Browser tabs) using the camera.
2. Click the button below to open the **Native Camera Window**.
3. Align your object inside the **Red Box**.
4. Press **`s`** on your keyboard to **SAVE** (Flash Green).
5. Press **`q`** to **QUIT** and return here.
""")

if st.button("Start Camera Window", type="primary"):
    # --- OPENCV NATIVE LOOP ---
    
    # Use specific backend logic to fix "Could not open index 0"
    backend = get_camera_backend()
    cap = cv2.VideoCapture(cam_index, backend)
    
    # Try default backend if DSHOW fails on Windows
    if not cap.isOpened() and platform.system() == 'Windows':
         st.warning("DirectShow failed. Retrying with default backend...")
         cap = cv2.VideoCapture(cam_index)

    if not cap.isOpened():
        st.error(f"""
        ❌ Could not open Camera Index {cam_index}. 
        
        **Troubleshooting:**
        1. Is another app using the camera? (Close browser tabs, Zoom, etc.)
        2. Try changing 'Camera Index' in the sidebar to 1 or 2.
        3. Unplug and replug the camera.
        """)
    else:
        st.toast("Camera Started! Look for the popup window.", icon="🎥")
        
        last_save_time = 0
        flash_duration = 0.2
        
        # Optimize camera settings (optional, helps with lag)
        cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
        
        while True:
            ret, frame = cap.read()
            if not ret:
                st.error("Failed to read frame stream.")
                break
                
            h, w = frame.shape[:2]
            
            # 1. Define ROI Coordinates (Safe)
            x1 = min(off_x, w-1)
            y1 = min(off_y, h-1)
            x2 = min(off_x + crop_w, w)
            y2 = min(off_y + crop_h, h)
            
            display_frame = frame.copy()
            
            # 2. Visual Feedback (Green flash if just saved)
            if time.time() - last_save_time < flash_duration:
                # Draw Green Box
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 255, 0), 5)
                cv2.putText(display_frame, "SAVED!", (x1, y1-10), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
            else:
                # Draw Red Box
                cv2.rectangle(display_frame, (x1, y1), (x2, y2), (0, 0, 255), 2)
            
            # 3. Instructions Overlay
            cv2.putText(display_frame, f"Seq: {get_next_sequence_number(target_folder, class_name):04d}", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
            cv2.putText(display_frame, "Press 's' to SAVE | 'q' to QUIT", (10, h - 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (200, 200, 200), 1)

            # 4. Show Window
            cv2.imshow("Data Collector - Press 's' to Save", display_frame)
            
            # 5. Handle Key Press
            key = cv2.waitKey(1) & 0xFF
            
            if key == ord('q'):
                break
            elif key == ord('s'):
                # Crop and Save original frame (not the one with drawings)
                roi = frame[y1:y2, x1:x2]
                saved_name = save_frame(roi, target_folder, class_name)
                print(f"Saved {saved_name}")
                last_save_time = time.time()

        cap.release()
        cv2.destroyAllWindows()
        st.rerun() # Refresh page to update stats