import os
import platform
from pathlib import Path
from datetime import datetime
import json
from PIL import Image
import subprocess
import time
import io
import socket
import ipaddress

import streamlit as st
from streamlit_image_coordinates import streamlit_image_coordinates

try:
    import nmap
except ImportError:
    nmap = None # Will be handled gracefully in the UI

from modules.config import AppConfig
from modules.tools import resolve_external_tools
from modules.console import set_adb_executable, adb, adb_output

# ---------------------------------------------------------------------------
# 1. Initialization and Configuration
# ---------------------------------------------------------------------------
st.set_page_config(page_title="ADB Admin", page_icon="🔧", layout="wide") 

# --- Inject custom CSS for Matrix style ---
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

# Assuming style.css is in the same directory as ADB_ADMIN.py
if os.path.exists("style.css"):
    load_css("style.css")
else:
    st.warning("`style.css` not found. Default Streamlit theme will be used. Create `style.css` in the app directory for custom styling.")
# --- End custom CSS injection ---

WEB_CONFIG_FILE = Path("streamlit_config.json")

def load_web_config():
    """Loads config from JSON file if it exists."""
    if WEB_CONFIG_FILE.exists():
        with open(WEB_CONFIG_FILE, "r") as f:
            return json.load(f)
    return {}

def save_web_config(data):
    """Saves data to the web config JSON file."""
    with open(WEB_CONFIG_FILE, "w") as f:
        json.dump(data, f, indent=4)

def get_ip_address() -> str | None:
    """Best-effort LAN IP. Returns None if offline."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.settimeout(1.0)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except (OSError, socket.timeout):
        return None

@st.cache_resource
def init_app_config():
    """Initialize AppConfig and resolve external tools only once."""
    config = AppConfig()
    config.operating_system = platform.system()
    resolve_external_tools(config) # This just checks the system PATH
    Path("Downloaded-Files").mkdir(exist_ok=True)
    return config

# --- Main App Logic ---

# Initialize base config (from PATH)
config = init_app_config()

# Load persistent web config (from JSON)
web_config = load_web_config()

# Set ADB path with priority: 1. JSON, 2. PATH
saved_adb_path = web_config.get("adb_path")
if saved_adb_path and Path(saved_adb_path).is_file():
    config.adb_path = saved_adb_path
# If not in JSON, config.adb_path from init_app_config (PATH) is used.

# Set Nmap path with priority: 1. JSON, 2. PATH
saved_nmap_path = web_config.get("nmap_path")
if saved_nmap_path and Path(saved_nmap_path).is_file():
    config.nmap_path = saved_nmap_path

# Initialize session state for devices
if 'devices' not in st.session_state:
    st.session_state.devices = web_config.get("devices", [])

# Set the executable for the session if we have a path by now
if config.adb_path:
    set_adb_executable(config.adb_path)

# --- UI Rendering ---

st.title("ADB Admin")

# If after all that, we still don't have an ADB path, ask the user.
if not config.adb_path:
    st.error("ADB executable not found automatically!")
    st.info("Please install ADB and ensure it's on your PATH, OR manually enter the path below. This will be saved for future sessions.")
    manual_adb = st.text_input("Manual ADB Path", placeholder=r"C:\platform-tools\adb.exe")
    if manual_adb and Path(manual_adb).is_file():
        web_config['adb_path'] = manual_adb
        save_web_config(web_config)
        config.adb_path = manual_adb
        set_adb_executable(manual_adb)
        st.rerun()
    st.stop()

st.sidebar.success(f"ADB Resolved: {config.adb_path}")
st.sidebar.info("Use the tabs to interact with your device.")
st.sidebar.markdown("---") # Rebranded
st.sidebar.markdown(f"© {datetime.now().year} Samith Hettiarachchi ( Nepstro )")

# ---------------------------------------------------------------------------
# 2. User Interface Tabs
# ---------------------------------------------------------------------------
tabs = st.tabs([
    "🔌 Connection",
    "ℹ️ Device Info",
    "📦 App Manager",
    "📁 Files",
    "📸 Media",
    "⚙️ Control",
    "⌨️ Interact",
    "👆 Gestures",
    "📡 Network",
    "💾 Data",
    "⚡ Advanced",
    "ℹ️ About"
])

# --- Connection Tab ---
with tabs[0]:
    st.header("Device Connection")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Connected Devices")
        if st.button("Refresh Devices"):
            result = adb(["devices", "-l"])
            st.text(result.stdout)

        st.markdown("---")
        st.subheader("Enable Network Debugging")
        st.info("Connect device via USB first, then click this to enable Wi-Fi mode.")
        if st.button("Enable ADB over Network (tcpip 5555)"):
            with st.spinner("Attempting to switch device to network mode..."):
                res = adb(["tcpip", "5555"])
                if "restarting in TCP mode" in (res.stdout or "").lower():
                    st.success(res.stdout.strip())
                    st.info("You can now disconnect the USB cable and use the 'Connect via Network' option.")
                else:
                    st.error(res.stdout.strip() or res.stderr.strip() or "Failed. Ensure one device is connected via USB and authorized.")
            
    with col2:
        st.subheader("Connect via Network")

        device_options = ["Enter new IP..."] + st.session_state.get("devices", [])
        selected_device = st.selectbox("Select a saved device or enter a new one", options=device_options)

        ip_address = ""
        if selected_device == "Enter new IP...":
            ip_address = st.text_input("Target IP Address", placeholder="192.168.1.23", key="new_ip")
        else:
            ip_address = selected_device
            if st.button("Forget this device", key=f"remove_{ip_address}"):
                st.session_state.devices.remove(ip_address)
                web_config['devices'] = st.session_state.devices
                save_web_config(web_config)
                st.rerun()

        if st.button("Connect"):
            if ip_address:
                with st.spinner(f"Connecting to {ip_address}..."):
                    res = adb(["connect", f"{ip_address}:5555"])
                    if "connected" in res.stdout.lower() or "already connected" in res.stdout.lower():
                        st.success(res.stdout.strip())
                        if ip_address not in st.session_state.devices:
                            st.session_state.devices.append(ip_address)
                            web_config['devices'] = st.session_state.devices
                            save_web_config(web_config)
                            st.rerun()
                    else:
                        st.error(res.stdout.strip() or res.stderr.strip())
            else:
                st.warning("Please enter or select a valid IP address.")

# --- Device Info Tab ---
with tabs[1]:
    st.header("Device Information")
    if st.button("Fetch All Device Info"):
        with st.spinner("Retrieving all device properties..."):
            # Define commands that provide rich information
            commands = {
                "props": ["getprop"],
                "battery": ["dumpsys", "battery"],
                "screen": ["wm", "size"],
                "meminfo": ["cat", "/proc/meminfo"],
                "uptime": ["uptime"],
                "storage": ["df", "-h", "/data"],
                "wlan": ["ip", "addr", "show", "wlan0"],
            }
            
            # Execute all commands
            raw_outputs = {key: adb_output(["shell"] + cmd) for key, cmd in commands.items()}
            
            # Dictionary to hold final, parsed results in a desired order
            info = {}

            # --- Parse `getprop` output for multiple properties ---
            props_output = raw_outputs.get("props", "")
            props_dict = {}
            if props_output:
                for line in props_output.splitlines():
                    if '[' in line and ']' in line and ':' in line:
                        try:
                            key_part, value_part = line.split(':', 1)
                            key = key_part.strip().strip('[]')
                            value = value_part.strip().strip('[]')
                            props_dict[key] = value
                        except ValueError:
                            continue # Skip malformed lines
            
            info["Model"] = props_dict.get("ro.product.model", "N/A")
            info["Manufacturer"] = props_dict.get("ro.product.manufacturer", "N/A")
            info["Android Version"] = props_dict.get("ro.build.version.release", "N/A")
            info["Android SDK"] = props_dict.get("ro.build.version.sdk", "N/A")
            info["Serial Number"] = props_dict.get("ro.serialno", props_dict.get("ro.boot.serialno", "N/A"))
            info["CPU Architecture"] = props_dict.get("ro.product.cpu.abi", "N/A")
            info["Build ID"] = props_dict.get("ro.build.display.id", "N/A")

            # --- Parse battery output ---
            battery_output = raw_outputs.get("battery", "")
            if battery_output:
                info["Battery Level"] = next((line.split(":")[-1].strip() + "%" for line in battery_output.splitlines() if "level:" in line), "N/A")
                temp_line = next((line for line in battery_output.splitlines() if "temperature:" in line), None)
                info["Battery Temp"] = f"{int(temp_line.split(':')[-1].strip()) / 10}°C" if temp_line else "N/A"
                health_line = next((line for line in battery_output.splitlines() if "health:" in line), None)
                if health_line:
                    health_map = {'1': 'Unknown', '2': 'Good', '3': 'Overheat', '4': 'Dead', '5': 'Over Voltage', '6': 'Unspecified Failure', '7': 'Cold'}
                    info["Battery Health"] = health_map.get(health_line.split(":")[-1].strip(), "Unknown")
                else:
                    info["Battery Health"] = "N/A"
            else:
                info["Battery Level"], info["Battery Temp"], info["Battery Health"] = "N/A", "N/A", "N/A"

            # --- Parse screen output ---
            screen_output = raw_outputs.get("screen", "")
            if screen_output:
                info["Screen Resolution"] = next((line.split(":")[-1].strip() for line in screen_output.splitlines() if "Physical size" in line), "N/A")
                info["Screen Density"] = next((line.split(":")[-1].strip() + " dpi" for line in screen_output.splitlines() if "Physical density" in line), "N/A")
            else:
                info["Screen Resolution"], info["Screen Density"] = "N/A", "N/A"

            # --- Parse meminfo output ---
            meminfo_output = raw_outputs.get("meminfo", "")
            total_mem_line = next((line for line in meminfo_output.splitlines() if "MemTotal:" in line), None)
            if total_mem_line:
                try:
                    kb = int(total_mem_line.split()[1])
                    info["Total RAM"] = f"{round(kb / 1024 / 1024, 2)} GB"
                except (ValueError, IndexError):
                    info["Total RAM"] = "N/A"
            else:
                info["Total RAM"] = "N/A"

            # --- Parse other info ---
            uptime_output = raw_outputs.get("uptime", "")
            info["Device Uptime"] = uptime_output.split(',')[0].split('up')[-1].strip() if uptime_output and 'up' in uptime_output else "N/A"
            storage_output = raw_outputs.get("storage", "")
            if storage_output and len(storage_output.strip().splitlines()) > 1:
                parts = storage_output.strip().splitlines()[-1].split()
                info["Internal Storage"] = f"{parts[2]} / {parts[1]} ({parts[4]} Used)" if len(parts) >= 5 else "Parse Error"
            else:
                info["Internal Storage"] = "N/A"
            mac_line = next((line for line in raw_outputs.get("wlan", "").splitlines() if "link/ether" in line), None)
            info["Wi-Fi MAC Address"] = mac_line.split()[1] if mac_line else "N/A (Wi-Fi may be off)"
            
            st.table(info)
# --- App Manager Tab ---
with tabs[2]:
    st.header("App Manager")
    
    col_list, col_action = st.columns(2)
    with col_list:
        st.subheader("List Applications")
        if st.button("List 3rd Party Apps"):
            with st.spinner("Fetching apps..."):
                apps_out = adb_output(["shell", "pm", "list", "packages", "-3"])
                # Clean up the output to just package names
                apps = [line.replace("package:", "").strip() for line in apps_out.splitlines() if line]
                st.dataframe({"Package Name": apps}, use_container_width=True)
        
        if st.button("List All System Apps"):
            with st.spinner("Fetching all apps..."):
                apps_out = adb_output(["shell", "pm", "list", "packages"])
                apps = [line.replace("package:", "").strip() for line in apps_out.splitlines() if line]
                st.dataframe({"Package Name": apps}, use_container_width=True)
                
    with col_action:
        st.subheader("Uninstall Application")
        pkg_to_uninstall = st.text_input("Package Name", placeholder="com.example.app", key="uninstall_pkg")
        if st.button("Uninstall"):
            if pkg_to_uninstall:
                with st.spinner(f"Uninstalling {pkg_to_uninstall}..."):
                    res = adb(["uninstall", pkg_to_uninstall])
                    st.info(res.stdout or res.stderr)
            else:
                st.warning("Please enter a package name.")

        st.markdown("---")

        # --- Install Action ---
        st.subheader("Install Application (APK)")
        apk_file = st.file_uploader("Choose an APK file", type=['apk'])
        if st.button("Install APK", disabled=not apk_file):
            with st.spinner(f"Installing `{apk_file.name}`..."):
                # Save uploaded file to a temporary location so ADB can access it
                temp_apk_path = Path("Downloaded-Files") / apk_file.name
                temp_apk_path.write_bytes(apk_file.getbuffer())

                # Run the adb install command
                res = adb(["install", "-r", str(temp_apk_path)])

                # Check result and provide feedback
                if "success" in (res.stdout or "").lower():
                    st.success(f"Successfully installed `{apk_file.name}`!")
                else:
                    st.error(f"Failed to install:\n{res.stderr or res.stdout}")

                # Clean up the temporary file
                if temp_apk_path.exists():
                    temp_apk_path.unlink()

        st.markdown("---")
        st.subheader("Install Split APKs")
        split_apk_files = st.file_uploader("Choose APK files", type=['apk'], accept_multiple_files=True)
        if st.button("Install Split APKs", disabled=not split_apk_files):
            with st.spinner(f"Installing {len(split_apk_files)} APKs..."):
                temp_apk_paths = []
                for f in split_apk_files:
                    p = Path("Downloaded-Files") / f.name
                    p.write_bytes(f.getbuffer())
                    temp_apk_paths.append(str(p))

                # Create a session for install-create
                res_create = adb_output(["install-create", "-r"])
                if "session" in res_create:
                    session_id = res_create.split("[")[-1].split("]")[0]
                    st.info(f"Created install session {session_id}")
                    
                    # Write each APK to the session
                    for i, path in enumerate(temp_apk_paths):
                        adb(["install-write", "-S", str(Path(path).stat().st_size), session_id, f"split_{i}", path])

                    # Commit the session
                    res_commit = adb_output(["install-commit", session_id])
                    st.info(res_commit)
                    if "Success" in res_commit:
                        st.success("Successfully installed split APKs!")
                    else:
                        adb(["install-abandon", session_id]) # Clean up failed session
                        st.error(f"Failed to commit install session: {res_commit}")
                else:
                    st.error(f"Failed to create install session: {res_create}")

                # Clean up temp files
                for p_str in temp_apk_paths:
                    Path(p_str).unlink()

# --- File Manager Tab ---
with tabs[3]:
    st.header("File Manager")

    # Define callbacks to safely modify session state before the UI rerenders.
    # This is the correct way to modify widget state to avoid StreamlitAPIException.
    def go_up_and_clear_search():
        st.session_state.current_path = str(Path(st.session_state.current_path).parent.as_posix())
        if st.session_state.current_path == ".": st.session_state.current_path = "/"
        st.session_state.pull_path_input = ""
        st.session_state.push_path_input = st.session_state.current_path
        st.session_state.file_search_query = ""

    def navigate_to_dir_and_clear_search(new_dir):
        st.session_state.current_path = str((Path(st.session_state.current_path) / new_dir).as_posix())
        st.session_state.pull_path_input = ""
        st.session_state.file_search_query = ""
        st.session_state.preview_image_path = None
        st.session_state.push_path_input = st.session_state.current_path

    def set_pull_path(filename):
        st.session_state.pull_path_input = str((Path(st.session_state.current_path) / filename).as_posix())
        st.session_state.push_path_input = st.session_state.current_path

    def set_preview_path(filename):
        st.session_state.preview_image_path = str((Path(st.session_state.current_path) / filename).as_posix())

    # Initialize session state for path and selected file
    if 'current_path' not in st.session_state:
        st.session_state.current_path = "/sdcard/"
    if 'file_search_query' not in st.session_state:
        st.session_state.file_search_query = ""
    if 'push_path_input' not in st.session_state:
        st.session_state.push_path_input = st.session_state.current_path

    col_browser, col_actions = st.columns([2, 1])

    with col_browser:
        st.subheader("Device File Browser")

        # --- Preview Display Area ---
        if st.session_state.get("preview_image_path"):
            st.subheader("Image Preview")
            preview_path = st.session_state.preview_image_path
            filename = Path(preview_path).name
            local_temp_path = Path("Downloaded-Files") / f"preview_{filename}"

            with st.spinner(f"Fetching preview for `{filename}`..."):
                adb(["pull", preview_path, str(local_temp_path)])

                if local_temp_path.exists():
                    try:
                        with Image.open(local_temp_path) as img:
                            img.thumbnail((400, 400)) # Create a reasonably sized thumbnail
                            st.image(img, caption=f"Preview of {filename}", use_container_width=True)
                    except Exception as e:
                        st.error(f"Could not generate preview: {e}")
                    finally:
                        local_temp_path.unlink() # Always clean up the temp file
                else:
                    st.error("Failed to pull image for preview.")

            if st.button("Close Preview"):
                st.session_state.preview_image_path = None
                st.rerun()
            st.markdown("---")

        # --- Navigation ---
        nav_cols = st.columns([3, 1, 1])
        nav_cols[0].write(f"**Current Path:** `{st.session_state.current_path}`")
        
        # Use the on_click callback to handle state changes before the next rerun.
        nav_cols[1].button("⬆️ Go Up", disabled=(st.session_state.current_path == "/"), on_click=go_up_and_clear_search)

        if nav_cols[2].button("🔄 Refresh"):
            st.rerun()
        
        # --- Search Bar ---
        st.text_input("Search in current directory", key="file_search_query", placeholder="Filter by name...")

        st.markdown("---")

        # --- File Listing ---
        with st.spinner(f"Listing files in `{st.session_state.current_path}`..."):
            # Sanitize path to prevent shell injection if a path contains a single quote.
            # This replaces ' with '\'' which is the standard way to escape a single quote
            # within a single-quoted string in Bourne-like shells.
            sanitized_path = st.session_state.current_path.replace("'", "'\\''")
            res = adb(["shell", f"ls -F '{sanitized_path}'"])
            if res.stderr and "No such file or directory" not in res.stderr:
                st.error(f"Error listing directory:\n{res.stderr}")
            else:
                # Handle case where a directory is empty and stdout is None
                lines = res.stdout.splitlines() if res.stdout else []
                dirs, files = [], []
                for line in lines:
                    if not line: continue
                    if line.endswith('/'):
                        dirs.append(line.strip('/'))
                    else:
                        files.append(line.rstrip('*@|'))
                
                # --- Filter based on search query ---
                search_query = st.session_state.get("file_search_query", "").lower()
                if search_query:
                    dirs = [d for d in dirs if search_query in d.lower()]
                    files = [f for f in files if search_query in f.lower()]

                IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.gif', '.bmp', '.webp')

                for d in sorted(dirs):
                    # Use the on_click callback with args to handle navigation and state clearing.
                    st.button(f"📁 {d}", key=f"dir_{d}", use_container_width=True, on_click=navigate_to_dir_and_clear_search, args=(d,))
                
                for f in sorted(files):
                    is_image = f.lower().endswith(IMAGE_EXTENSIONS)

                    if is_image:
                        item_cols = st.columns([8, 1])
                        item_cols[0].button(f"📄 {f}", key=f"file_{f}", use_container_width=True, on_click=set_pull_path, args=(f,))
                        item_cols[1].button("🖼️", key=f"preview_{f}", help="Show image preview", on_click=set_preview_path, args=(f,))
                    else:
                        st.button(f"📄 {f}", key=f"file_{f}", use_container_width=True, on_click=set_pull_path, args=(f,))

    with col_actions:
        st.subheader("File Actions")
        st.markdown("---")

        # --- Pull Action ---
        st.subheader("Pull (Download) File")
        remote_file_to_pull = st.text_input("File path on device", key="pull_path_input")
        if st.button("Pull Selected File", disabled=not remote_file_to_pull):
            filename = Path(remote_file_to_pull).name
            local_dest = Path("Downloaded-Files") / filename
            with st.spinner(f"Pulling `{filename}`..."):
                res = adb(["pull", remote_file_to_pull, str(local_dest)])
                # Check for success by verifying file existence, as `adb pull` prints stats to stderr.
                if local_dest.exists() and local_dest.is_file():
                    st.success(f"File saved to `{local_dest}`")
                    if res.stderr:
                        st.info(f"ADB Output: {res.stderr.strip()}")
                else:
                    st.error(f"Pull failed:\n{res.stderr or 'Unknown error.'}")
        
        st.markdown("---")

        # --- Push Action ---
        st.subheader("Push (Upload) File")
        uploaded_file = st.file_uploader("Choose a file to upload")
        remote_dest_folder = st.text_input("Destination folder on device", key="push_path_input")
        if st.button("Push to Current Folder", disabled=not uploaded_file):
            with st.spinner(f"Pushing `{uploaded_file.name}`..."):
                temp_path = Path("Downloaded-Files") / uploaded_file.name
                temp_path.write_bytes(uploaded_file.getbuffer())
                res = adb(["push", str(temp_path), remote_dest_folder])
                # `adb push` also prints stats to stderr. Check for common error keywords.
                error_keywords = ["error", "failed", "denied", "not found"]
                if res.stderr and any(keyword in res.stderr.lower() for keyword in error_keywords):
                    st.error(f"Push failed:\n{res.stderr}")
                else:
                    st.success(f"Pushed `{uploaded_file.name}` to `{remote_dest_folder}`")
                    if res.stderr:
                        st.info(f"ADB Output: {res.stderr.strip()}")
                    # We don't rerun automatically, so the user can see the message.
                    # They can use the refresh button to see the new file.
# --- Media Tab ---
with tabs[4]:
    st.header("Media & Screenshots")

    # --- Display area for the last captured screenshot ---
    if st.session_state.get("last_screenshot_path"):
        screenshot_path = st.session_state.last_screenshot_path
        if Path(screenshot_path).exists():
            st.image(screenshot_path, caption=Path(screenshot_path).name)
            if st.button("Clear Screenshot"):
                st.session_state.last_screenshot_path = None
                st.rerun()
        else:
            st.session_state.last_screenshot_path = None # File was deleted, clear state

    # --- Display area for the last recorded video ---
    if st.session_state.get("last_video_path"):
        video_path = st.session_state.last_video_path
        if Path(video_path).exists():
            # Read the video file into bytes for more reliable playback with st.video
            with open(video_path, "rb") as f:
                st.video(f.read(), format='video/mp4')
            if st.button("Clear Video"):
                st.session_state.last_video_path = None
                st.rerun()
        else:
            st.session_state.last_video_path = None # File was deleted

    if st.button("Capture Anonymous Screenshot"):
        with st.spinner("Capturing and pulling screenshot..."):
            file_name = f"screenshot-{datetime.now().strftime('%Y%m%d-%H%M%S')}.png"
            remote_path = f"/sdcard/{file_name}"
            local_path = Path("Downloaded-Files") / file_name

            adb(["shell", "screencap", "-p", remote_path])
            adb(["pull", remote_path, str(local_path)])
            adb(["shell", "rm", remote_path]) # Delete from device storage

            if local_path.exists():
                st.session_state.last_screenshot_path = str(local_path)
                st.rerun()

    st.markdown("---")

    # --- Remote Screen Feature ---
    st.header("Remote Screen")
    st.info("Provides a live view of the device screen. Framerate depends on connection speed.")

    refresh_delay = st.slider(
        "Live View Refresh Delay (seconds)",
        min_value=0.0,
        max_value=2.0,
        value=0.1, # A very aggressive default for faster refresh.
        step=0.05,
        help="Lower this for a faster refresh rate. A setting of 0.0 will refresh as fast as the connection allows. WARNING: Low values can cause high CPU usage and instability."
    )

    is_live = st.toggle("Start Live View", key="live_view_active")
    placeholder = st.empty()

    if is_live:
        # This block will run on every rerun as long as the toggle is on
        with placeholder.container():
            # Use subprocess directly for full control over binary streams,
            # bypassing any potential issues in the imported adb() wrapper.
            command = [config.adb_path, "exec-out", "screencap", "-p"]
            try:
                # Use a timeout to prevent the app from hanging if the device is slow
                result = subprocess.run(command, capture_output=True, check=False, timeout=5)

                if result.stdout:
                    # Some devices (e.g., with multiple displays) output a warning to stdout
                    # before the PNG data, which corrupts the image stream. We need to find
                    # the start of the actual PNG file signature and slice the data from there.
                    output_data = result.stdout
                    png_signature = b'\x89PNG\r\n\x1a\n'
                    png_start_index = output_data.find(png_signature)

                    if png_start_index == -1:
                        # If signature is not found, the output is likely just an error message.
                        error_message = output_data.decode('utf-8', 'ignore')
                        st.error(f"Failed to get a valid image from device. Error: {error_message}")
                        st.stop()

                    png_data = output_data[png_start_index:]
                    try:
                        # Use Pillow to get the actual image dimensions for coordinate scaling
                        img = Image.open(io.BytesIO(png_data))
                        actual_width, actual_height = img.size
                        displayed_width = 350

                        # The component returns coordinates when the image is clicked
                        coords = streamlit_image_coordinates(img, width=displayed_width, key="live_view_coords")
                        st.caption("Live View (Click to Tap/Swipe)")

                        # Initialize swipe and click-tracking state if not present
                        if 'swipe_mode_active' not in st.session_state:
                            st.session_state.swipe_mode_active = False
                        if 'swipe_start_coords_live' not in st.session_state:
                            st.session_state.swipe_start_coords_live = None
                        if 'last_processed_coords' not in st.session_state:
                            st.session_state.last_processed_coords = None

                        # A new click is registered if the widget's coordinates are not None
                        # and are different from the last coordinates we processed.
                        if coords and coords != st.session_state.last_processed_coords:
                            # Scale the clicked coordinates to the actual screen size
                            scaling_factor = actual_width / displayed_width
                            target_x = int(coords['x'] * scaling_factor)
                            target_y = int(coords['y'] * scaling_factor)

                            if st.session_state.swipe_mode_active:
                                if st.session_state.swipe_start_coords_live is None:
                                    # First click in swipe mode: set start point
                                    st.session_state.swipe_start_coords_live = {'x': target_x, 'y': target_y}
                                    st.toast(f"Swipe start point set at ({target_x}, {target_y}). Click again for end point.")
                                else:
                                    # Second click in swipe mode: set end point and execute swipe
                                    start_x = st.session_state.swipe_start_coords_live['x']
                                    start_y = st.session_state.swipe_start_coords_live['y']
                                    end_x = target_x
                                    end_y = target_y
                                    swipe_duration = st.session_state.get("live_swipe_duration", 300)

                                    adb(["shell", "input", "swipe", str(start_x), str(start_y), str(end_x), str(end_y), str(swipe_duration)])
                                    st.toast(f"Swiped from ({start_x}, {start_y}) to ({end_x}, {end_y})")

                                    # Reset for next swipe
                                    st.session_state.swipe_start_coords_live = None
                            else:
                                # Not in swipe mode, so it's a tap
                                adb(["shell", "input", "tap", str(target_x), str(target_y)])
                                st.toast(f"Tapped at ({target_x}, {target_y})")

                            # After processing the click, update our tracker to "consume" the event.
                            # This prevents the same click from being processed on the next rerun.
                            st.session_state.last_processed_coords = coords

                    except Image.UnidentifiedImageError:
                        # This can happen if the stream is truncated or corrupt even after the signature
                        st.error("Failed to process image stream from device (stream may be corrupt).")
                        st.stop() # Stop the script to prevent re-running the loop on error.

                elif result.stderr:
                    # Decode stderr from bytes to string for display.
                    error_message = result.stderr.decode('utf-8', 'ignore') if isinstance(result.stderr, bytes) else result.stderr
                    st.error(f"Screen capture failed: {error_message}")
                    st.stop() # Stop the script to prevent re-running the loop on error.
                else:
                    st.warning("Received no data from device. Is the screen on and unlocked?")

            except FileNotFoundError:
                st.error(f"ADB executable not found at path: {config.adb_path}")
                st.stop() # Stop the script to prevent re-running the loop on error.
            except subprocess.TimeoutExpired:
                st.warning("ADB command timed out. The device may be unresponsive.")
                # The loop will continue on the next rerun.

        # Use the configurable delay. This makes the loop less aggressive and more stable.
        time.sleep(refresh_delay)
        # Trigger an immediate rerun to fetch the next frame.
        st.rerun()

    # --- Swipe Mode Controls ---
    st.markdown("---")
    st.subheader("Interactive Swipe Controls")

    # Initialize the state if it's missing, to prevent crashes.
    if 'swipe_start_coords_live' not in st.session_state:
        st.session_state.swipe_start_coords_live = None

    st.session_state.swipe_mode_active = st.toggle("Activate Two-Click Swipe Mode", key="swipe_mode_toggle")

    if st.session_state.swipe_mode_active:
        st.number_input("Swipe Duration (ms)", min_value=1, value=300, key="live_swipe_duration")
        if st.session_state.swipe_start_coords_live:
            st.info(f"Start point set: ({st.session_state.swipe_start_coords_live['x']}, {st.session_state.swipe_start_coords_live['y']}). Click again for end point.")
        else:
            st.info("Click on the live view to set the swipe start point.")
        if st.button("Clear Swipe Points"):
            st.session_state.swipe_start_coords_live = None
            st.rerun()

    st.markdown("---")

    # --- Screen Recording Feature ---
    st.header("Screen Recording")

    def prepare_to_start_recording():
        """Callback to safely stop live view and flag that a recording should start."""
        # This is the most important part: stop the live view loop by updating the toggle's state.
        if st.session_state.get("live_view_active", False):
            st.session_state.live_view_active = False
        
        # Set a flag to indicate we should start the recording process on the next run.
        st.session_state.trigger_recording_start = True

    # Display and clear sticky error from previous attempt
    if "recording_error" in st.session_state:
        st.error(st.session_state.recording_error)
        del st.session_state["recording_error"]

    is_recording = st.session_state.get("is_recording", False)

    if is_recording:
        st.warning("🔴 Recording in progress...")
        if st.button("Stop Recording"):
            with st.spinner("Stopping recording and processing video..."):
                pid = None
                try:
                    # Use subprocess with timeout to prevent hangs
                    ps_command = [config.adb_path, "shell", "ps | grep screenrecord"]
                    ps_result = subprocess.run(ps_command, capture_output=True, check=False, timeout=5)
                    ps_res = ps_result.stdout.decode('utf-8', 'ignore')
                    ps_line = next((line for line in ps_res.splitlines() if 'grep' not in line and 'defunct' not in line), None) if ps_res else None
                    if ps_line:
                        pid = ps_line.split()[1]
                except Exception as e:
                    st.error(f"Error finding process ID: {e}")

                if pid:
                    # Send SIGINT (2) for a graceful shutdown, similar to Ctrl+C
                    adb(["shell", f"kill -2 {pid}"])
                    time.sleep(2) # Give the device a moment to finalize the file

                    remote_path = st.session_state.recording_path
                    local_path = Path("Downloaded-Files") / Path(remote_path).name

                    adb(["pull", remote_path, str(local_path)])
                    adb(["shell", "rm", remote_path]) # Clean up remote file

                    if local_path.exists() and local_path.stat().st_size > 0:
                        st.session_state.last_video_path = str(local_path)
                    else:
                        if local_path.exists(): # It exists but is empty
                            local_path.unlink() # Clean up the empty file
                        st.error("Failed to retrieve a valid video file. The recording may have been empty or corrupted on the device.")
                else:
                    st.error("Could not find recording process on device. It may have stopped automatically (e.g., 3-minute limit).")

                st.session_state.is_recording = False
                st.session_state.recording_path = None
                st.rerun()
    else:
        st.button("Start Recording", on_click=prepare_to_start_recording, disabled=is_recording)

    # The actual recording logic is now triggered by the flag set in the callback.
    if st.session_state.get("trigger_recording_start", False):
        # Immediately delete the flag to prevent re-triggering.
        del st.session_state.trigger_recording_start

        with st.spinner("Starting recording on device..."):
            remote_path = f"/sdcard/recording-{datetime.now().strftime('%Y%m%d-%H%M%S')}.mp4"
            # Use `nohup` to ensure the screenrecord process detaches completely.
            # Check if nohup is available on the device first for better compatibility.
            has_nohup_res = adb_output(["shell", "command -v nohup"])
            if "nohup" in has_nohup_res:
                start_command = f"nohup screenrecord {remote_path} > /dev/null 2>&1 &"
            else:
                # Fallback for systems without nohup. This might be less reliable.
                st.warning("`nohup` command not found on device. Recording may stop unexpectedly if the connection is lost.")
                start_command = f"screenrecord {remote_path} > /dev/null 2>&1 &"
            adb(["shell", start_command])
            time.sleep(2) # Give it a moment to start up

            # Verify that the process has actually started
            ps_line = None
            try:
                ps_command = [config.adb_path, "shell", "ps | grep screenrecord"]
                ps_result = subprocess.run(ps_command, capture_output=True, check=False, timeout=5)
                ps_res = ps_result.stdout.decode('utf-8', 'ignore')
                ps_line = next((line for line in ps_res.splitlines() if 'grep' not in line and 'defunct' not in line), None) if ps_res else None
            except Exception as e:
                st.session_state.recording_error = f"Failed to verify recording status: {e}"
                st.rerun()

            if ps_line:
                st.session_state.is_recording = True
                st.session_state.recording_path = remote_path
                st.toast("Recording started successfully! 🎉")
                st.rerun()
            else:
                # Clean up the failed background command if possible
                adb(["shell", "killall screenrecord"])
                st.session_state.recording_error = "Failed to start screen recording. Ensure the device screen is unlocked. The process may also be unsupported on this device."
                st.rerun()

# --- Control Tab ---
with tabs[5]:
    st.header("Device Control")
    col_pwr, col_media, col_conn = st.columns(3)
    
    with col_pwr:
        st.subheader("Power Management")
        if st.button("Reboot System"): adb(["reboot"])
        if st.button("Reboot to Recovery"): adb(["reboot", "recovery"])
        if st.button("Reboot to Bootloader"): adb(["reboot", "bootloader"])
        if st.button("Power Off"): adb(["shell", "reboot", "-p"])
        st.markdown("---")
        st.subheader("Screen Lock")
        if st.button("Unlock Device (Simple Swipe)"):
            adb(["shell", "input", "keyevent", "224"]) # Wake
            time.sleep(1) # Increased delay to ensure screen is ready
            adb(["shell", "wm", "dismiss-keyguard"]) # More reliable unlock command
            st.toast("Sent wake and unlock command.")
            
    with col_media:
        st.subheader("Simulate Key Events")
        if st.button("Home Button"): adb(["shell", "input", "keyevent", "3"])
        if st.button("Back Button"): adb(["shell", "input", "keyevent", "4"])
        if st.button("Power/Lock"): adb(["shell", "input", "keyevent", "26"])
        if st.button("Wake Up Screen"): adb(["shell", "input", "keyevent", "224"])
        if st.button("Enter"): adb(["shell", "input", "keyevent", "66"])
        if st.button("Delete/Backspace"): adb(["shell", "input", "keyevent", "67"])

        st.markdown("---")
        st.subheader("Volume Control")
        if st.button("Volume Up"): adb(["shell", "input", "keyevent", "24"])
        if st.button("Volume Down"): adb(["shell", "input", "keyevent", "25"])
        if st.button("Mute"): adb(["shell", "input", "keyevent", "164"])

    with col_conn:
        st.subheader("Connectivity")
        if st.button("Enable Wi-Fi"): adb(["shell", "svc", "wifi", "enable"])
        if st.button("Disable Wi-Fi"): adb(["shell", "svc", "wifi", "disable"])
        if st.button("Enable Bluetooth"): adb(["shell", "svc", "bluetooth", "enable"])
        if st.button("Disable Bluetooth"): adb(["shell", "svc", "bluetooth", "disable"])

        st.markdown("---")
        st.subheader("Display")
        if st.button("Enable Auto-Rotation"): adb(["shell", "settings", "put", "system", "accelerometer_rotation", "1"])
        if st.button("Disable Auto-Rotation"): adb(["shell", "settings", "put", "system", "accelerometer_rotation", "0"])

# --- Interact Tab ---
with tabs[6]:
    st.header("Device Interaction")
    col_url, col_txt = st.columns(2)
    
    with col_url:
        st.subheader("Open URL")
        url_to_open = st.text_input("URL", placeholder="https://google.com")
        if st.button("Open in Browser"):
            if url_to_open:
                # The URL needs to be quoted for the remote shell to handle special characters (&, ?, etc.) correctly.
                # We pass the entire command as a single string to `adb shell`.
                command_string = f"am start -a android.intent.action.VIEW -d '{url_to_open}'"
                res = adb(["shell", command_string])
                
                # Provide feedback to the user for debugging
                if res.stderr:
                    st.error(f"ADB Error:\n{res.stderr}")
                else:
                    st.success("Command sent to device.")
                
    with col_txt:
        st.subheader("Send Text")
        text_to_type = st.text_input("Text to Type", placeholder="Hello World")
        if st.button("Type Text"):
            if text_to_type:
                # ADB requires spaces to be replaced with %s
                formatted_text = text_to_type.replace(" ", "%s")
                adb(["shell", "input", "text", formatted_text])
    
    st.markdown("---")
    col_app, col_sms = st.columns(2)
    with col_app:
        st.subheader("Run Application")
        pkg_to_run = st.text_input("Package Name to Run", placeholder="com.google.android.youtube")
        if st.button("Run App"):
            if pkg_to_run:
                adb(["shell", "monkey", "-p", pkg_to_run, "-c", "android.intent.category.LAUNCHER", "1"])
                st.success(f"Sent command to launch {pkg_to_run}")
            else:
                st.warning("Please enter a package name.")
    with col_sms:
        st.subheader("Send SMS")
        st.caption("This opens the SMS app with the fields pre-filled.")
        sms_number = st.text_input("Phone Number")
        sms_body = st.text_area("Message")
        if st.button("Prepare SMS"):
            if sms_number:
                # Sanitize for shell
                safe_body = sms_body.replace("'", "'\\''")
                command = f"am start -a android.intent.action.SENDTO -d sms:{sms_number} --es sms_body '{safe_body}'"
                adb(["shell", command])
                st.success("Sent command to open SMS app.")
            else:
                st.warning("Please provide a phone number.")

# --- Gestures Tab ---
with tabs[7]:
    st.header("👆 Gestures")
    st.info("Simulate touch and swipe gestures on the device screen. Coordinates are based on the device's resolution.")

    # --- Resolution Helper ---
    with st.expander("Get Screen Resolution Helper"):
        if st.button("Fetch Current Resolution"):
            with st.spinner("Fetching resolution..."):
                res = adb_output(["shell", "wm size"])
                if res:
                    size_line = next((line for line in res.splitlines() if "Physical size" in line), None)
                    if size_line:
                        resolution = size_line.split(":")[-1].strip()
                        st.success(f"Device Resolution: **{resolution}**")
                    else:
                        st.warning("Could not determine screen resolution from command output.")
                else:
                    st.error("Failed to get screen resolution.")

    col_tap, col_swipe = st.columns(2)

    with col_tap:
        st.subheader("Tap Gesture")
        tap_x = st.number_input("X coordinate", value=540, min_value=0, key="tap_x")
        tap_y = st.number_input("Y coordinate", value=1200, min_value=0, key="tap_y")
        if st.button("Simulate Tap"):
            adb(["shell", "input", "tap", str(tap_x), str(tap_y)])
            st.toast(f"Tapped at ({tap_x}, {tap_y})")

    with col_swipe:
        st.subheader("Swipe Gesture")
        swipe_x1 = st.number_input("Start X", value=540, min_value=0, key="swipe_x1")
        swipe_y1 = st.number_input("Start Y", value=1800, min_value=0, key="swipe_y1")
        swipe_x2 = st.number_input("End X", value=540, min_value=0, key="swipe_x2")
        swipe_y2 = st.number_input("End Y", value=600, min_value=0, key="swipe_y2")
        duration = st.number_input("Duration (ms)", value=300, min_value=1, key="swipe_duration")
        if st.button("Simulate Swipe"):
            adb(["shell", "input", "swipe", str(swipe_x1), str(swipe_y1), str(swipe_x2), str(swipe_y2), str(duration)])
            st.toast(f"Swiped from ({swipe_x1}, {swipe_y1}) to ({swipe_x2}, {swipe_y2})")

# --- Network Tab ---
with tabs[8]:
    st.header("📡 Network Tools")

    nmap_library_installed = nmap is not None
    nmap_executable_found = config.nmap_path is not None and Path(config.nmap_path).is_file()
    nmap_ready = nmap_library_installed and nmap_executable_found

    if not nmap_library_installed:
        st.error("The `python-nmap` library is not installed. Network Scan is disabled. Please run `pip install python-nmap`.")
    elif not nmap_executable_found:
        st.warning("Nmap executable not found automatically.")
        st.info("Please install Nmap (from nmap.org) and ensure it's in your system's PATH, OR manually enter the path to nmap.exe below. This will be saved for future sessions.")
        default_nmap_path = r"C:\Program Files (x86)\Nmap\nmap.exe"
        manual_nmap_path = st.text_input("Manual Nmap Path", placeholder=default_nmap_path)
        
        if manual_nmap_path and Path(manual_nmap_path).is_file():
            web_config['nmap_path'] = manual_nmap_path
            save_web_config(web_config)
            config.nmap_path = manual_nmap_path
            st.success(f"Nmap path saved: {manual_nmap_path}")
            st.rerun()
        elif manual_nmap_path:
            st.error("The specified path is not a valid file.")

    st.subheader("LAN Device Scan")
    st.info("Scans the local network for devices with the ADB port (5555) open.")
    if st.button("Scan Local Network", disabled=not nmap_ready):
        local_ip = get_ip_address()
        if not local_ip:
            st.error("Could not determine local IP address. Check your network connection.")
        else:
            subnet = str(ipaddress.ip_network(local_ip + '/24', strict=False))
            with st.spinner(f"Scanning {subnet} for ADB hosts... (This may take a minute)"):
                try:
                    # Use `nmap_search_path` for broader compatibility with older python-nmap versions.
                    # It expects a tuple of paths to search for the executable.
                    nm = nmap.PortScanner(nmap_search_path=(config.nmap_path,))
                    nm.scan(hosts=subnet, arguments='-p 5555 --open')
                    hosts = []
                    for host in nm.all_hosts():
                        if (
                            nm[host].state() == "up"
                            and nm[host].has_tcp(5555)
                            and nm[host]["tcp"][5555]["state"] == "open"
                        ):
                            hosts.append({'IP Address': host, 'Port 5555': 'Open'})
                    
                    if hosts:
                        st.success(f"Found {len(hosts)} potential device(s).")
                        st.table(hosts)
                    else:
                        st.warning("No devices with port 5555 open were found on the network.")
                except nmap.PortScannerError as e:
                    st.error(f"Nmap scan failed: {e}")
                    st.info(
                        "This can happen if Nmap is not installed correctly or if the program lacks permissions to perform a scan."
                    )

    st.markdown("---")
    st.subheader("TCP Port Forwarding")
    col_fwd, col_rev = st.columns(2)
    with col_fwd:
        st.write("**Forward (PC -> Device)**")
        fwd_local = st.text_input("PC Port", placeholder="8080")
        fwd_remote = st.text_input("Device Port", placeholder="8000")
        if st.button("Forward Port"):
            res = adb_output(["forward", f"tcp:{fwd_local}", f"tcp:{fwd_remote}"])
            st.success("Forwarding rule applied.")
    with col_rev:
        st.write("**Reverse (Device -> PC)**")
        rev_remote = st.text_input("Device Port", placeholder="9000", key="rev_remote")
        rev_local = st.text_input("PC Port", placeholder="9000", key="rev_local")
        if st.button("Reverse Port"):
            res = adb_output(["reverse", f"tcp:{rev_remote}", f"tcp:{rev_local}"])
            st.success("Reverse forwarding rule applied.")
    
    if st.button("List Forwarding Rules"):
        st.text(adb_output(["forward", "--list"]))

    st.markdown("---")
    st.subheader("Connectivity Test")
    ping_host = st.text_input("Hostname or IP to Ping", value="google.com")
    if st.button("Ping from Device"):
        with st.spinner(f"Pinging {ping_host}..."):
            st.code(adb_output(["shell", "ping", "-c", "4", ping_host]), language="log")

# --- Data Tab ---
with tabs[9]:
    st.header("💾 Data & Extraction")

    def pull_common_folder(remote_paths: list[str], local_folder_name: str, label: str):
        """Helper to find and pull common data folders."""
        with st.spinner(f"Locating and pulling {label}..."):
            location = None
            for path in remote_paths:
                # `test -d` is a reliable way to check for a directory's existence in shell
                if adb(["shell", "test", "-d", path]).returncode == 0:
                    location = path
                    break
            
            if location:
                st.info(f"Found {label} at: `{location}`")
                dest = Path("Downloaded-Files") / local_folder_name
                dest.mkdir(exist_ok=True)

                # Append '/.' to the remote path to copy its contents, not the directory itself.
                remote_path_contents = f"{location}/."
                res_pull = adb(["pull", remote_path_contents, str(dest)])
                
                # A non-zero return code indicates a failure.
                if res_pull.returncode == 0:
                    st.success(f"{label} saved to `{dest}`")
                    if res_pull.stderr: # Show transfer stats if available
                        st.info(f"ADB Output:\n{res_pull.stderr.strip()}")
                else:
                    st.error(f"Pull failed for {label}:\n{res_pull.stderr or res_pull.stdout}")
            else:
                st.error(f"Could not find a {label} folder on the device. Checked: {', '.join(remote_paths)}")

    st.subheader("Quick Data Pulls")
    st.caption("Downloads common application data folders to your `Downloaded-Files` directory.")
    
    col_pull1, col_pull2, col_pull3 = st.columns(3)
    with col_pull1:
        if st.button("Copy WhatsApp Data"):
            pull_common_folder(
                remote_paths=["/sdcard/Android/media/com.whatsapp/WhatsApp", "/sdcard/WhatsApp"],
                local_folder_name="WhatsApp",
                label="WhatsApp data"
            )
    with col_pull2:
        if st.button("Copy All Screenshots"):
            pull_common_folder(
                remote_paths=["/sdcard/DCIM/Screenshots", "/sdcard/Pictures/Screenshots", "/sdcard/Screenshots"],
                local_folder_name="Screenshots",
                label="Screenshots"
            )
    with col_pull3:
        if st.button("Copy All Camera Photos"):
            pull_common_folder(
                remote_paths=["/sdcard/DCIM/Camera"],
                local_folder_name="Camera",
                label="Camera photos"
            )

    st.markdown("---")
    st.subheader("Content Dumps")
    st.caption("Uses `content query` to dump databases to text files.")
    dump_dest = Path("Downloaded-Files") / "Dumps"
    dump_dest.mkdir(exist_ok=True)

    def perform_dump(uri: str, projection: str, file_prefix: str, label: str):
        """Helper function to perform a content dump and handle results."""
        with st.spinner(f"Dumping {label}..."):
            # Use adb() directly to get the full result object for better error handling
            result = adb(["shell", "content", "query", "--uri", uri, "--projection", projection])
            
            now_str = datetime.now().strftime('%Y%m%d-%H%M%S')
            out_path = dump_dest / f"{file_prefix}_dump_{now_str}.txt"

            if result.returncode == 0:
                if result.stdout:
                    out_path.write_text(result.stdout, encoding="utf-8")
                    st.success(f"{label} dump saved to `{out_path}`")
                else:
                    # Command succeeded but returned no data.
                    st.warning(f"Command succeeded but returned no data for {label}.")
                    st.info("This is common on modern Android versions due to security restrictions. The `shell` user often lacks permission to read user data like SMS or contacts. This feature may only work on rooted devices or older Android versions.")
                    out_path.write_text("", encoding="utf-8") # Create empty file for record
            else:
                # Command failed.
                st.error(f"Failed to dump {label}. Error:\n```\n{result.stderr or '(No error message from ADB)'}\n```")

    col_dump1, col_dump2, col_dump3 = st.columns(3)
    with col_dump1:
        if st.button("Dump All SMS"):
            perform_dump(
                uri="content://sms/",
                projection="_id,address,date,body",
                file_prefix="sms",
                label="SMS"
            )
    with col_dump2:
        if st.button("Dump All Contacts"):
            perform_dump("content://contacts/phones/", "_id,display_name,number", "contacts", "Contacts")
    with col_dump3:
        if st.button("Dump Call Logs"):
            perform_dump("content://call_log/calls", "_id,name,number,duration,date", "call_log", "Call Logs")

    st.markdown("---")
    st.subheader("Extract APK from Installed App")
    pkg_to_extract = st.text_input("Package Name to Extract", placeholder="com.example.app")
    if st.button("Extract APK"):
        if pkg_to_extract:
            with st.spinner(f"Finding and extracting APK for {pkg_to_extract}..."):
                path_res = adb_output(["shell", "pm", "path", pkg_to_extract])
                if "package:" in path_res:
                    remote_apk_path = path_res.split(":")[-1].strip()
                    local_apk_path = Path("Downloaded-Files") / f"{pkg_to_extract}.apk"
                    adb(["pull", remote_apk_path, str(local_apk_path)])
                    if local_apk_path.exists():
                        st.success(f"APK saved to `{local_apk_path}`")
                    else:
                        st.error("Failed to pull the APK file after finding it.")
                else:
                    st.error(f"Could not find path for package `{pkg_to_extract}`. Is it installed?")
        else:
            st.warning("Please enter a package name.")

# --- Advanced Tab ---
with tabs[10]:
    st.header("⚡ Advanced Actions")
    st.warning("These actions can have significant effects on your device. Use with caution.")

    st.subheader("Root Access")
    if st.button("Check for Root Access"):
        with st.spinner("Checking for root..."):
            # The `su -c` command attempts to run a command as the superuser.
            # If it succeeds and returns our magic string, root is available.
            # We redirect stderr to stdout to capture permission errors in the output.
            result = adb_output(["shell", "su -c 'echo I_AM_ROOT' 2>&1"])
            if "I_AM_ROOT" in result:
                st.success("✅ Root access detected! You can run commands as root.")
                st.info("""
                    You can now try to read the raw database files directly using the 'Run Raw Shell Command' feature below, and then pull the resulting file using the 'Files' tab.
                    - **SMS Database:** `su -c 'cp /data/data/com.android.providers.telephony/databases/mmssms.db /sdcard/sms.db'`
                    - **Contacts Database:** `su -c 'cp /data/data/com.android.providers.contacts/databases/contacts2.db /sdcard/contacts.db'`
                """)
            elif "not found" in result.lower() or "denied" in result.lower():
                st.error("❌ Root access not detected. The 'su' binary was not found or is not accessible.")
            else:
                st.warning(f"🤔 Root status is uncertain. The command returned:\n```\n{result}\n```")
    st.markdown("---")

    st.subheader("ADB Server Control")
    if st.button("Disconnect All Devices"):
        st.code(adb_output(["disconnect"]))
    if st.button("Stop ADB Server", help="This will kill the ADB process on your computer."):
        st.code(adb_output(["kill-server"]))

    st.markdown("---")
    st.subheader("Run Raw Shell Command")
    shell_cmd = st.text_input("Shell Command", placeholder="ls -l /sdcard")
    if st.button("Execute Command"):
        if shell_cmd:
            with st.spinner("Executing..."):
                output = adb_output(["shell", shell_cmd])
                st.code(output, language="bash")
        else:
            st.warning("Please enter a command.")

    st.markdown("---")
    st.subheader("Advanced App Controls")
    adv_app_pkg = st.text_input("Target Package Name", placeholder="com.example.app", key="adv_app_pkg")
    app_cols1, app_cols2 = st.columns(2)
    with app_cols1:
        if st.button("Force Stop App", disabled=not adv_app_pkg):
            st.code(adb_output(["shell", "am", "force-stop", adv_app_pkg]))
        if st.button("Clear App Data", disabled=not adv_app_pkg):
            st.code(adb_output(["shell", "pm", "clear", adv_app_pkg]))
    with app_cols2:
        if st.button("Restart App", disabled=not adv_app_pkg):
            adb(["shell", "am", "force-stop", adv_app_pkg])
            time.sleep(1)
            adb(["shell", "monkey", "-p", adv_app_pkg, "-c", "android.intent.category.LAUNCHER", "1"])
            st.success(f"Sent restart command for {adv_app_pkg}")

    st.markdown("---")
    st.subheader("Manage App Permissions")
    perm_pkg = st.text_input("Package Name", placeholder="com.termux", key="perm_pkg")
    perm_str = st.text_input("Permission Name", placeholder="android.permission.READ_EXTERNAL_STORAGE", key="perm_str")
    perm_cols1, perm_cols2 = st.columns(2)
    with perm_cols1:
        if st.button("Grant Permission", disabled=not (perm_pkg and perm_str)):
            st.code(adb_output(["shell", "pm", "grant", perm_pkg, perm_str]))
    with perm_cols2:
        if st.button("Revoke Permission", disabled=not (perm_pkg and perm_str)):
            st.code(adb_output(["shell", "pm", "revoke", perm_pkg, perm_str]))

    st.markdown("---")
    st.subheader("Miscellaneous Settings")
    misc_cols1, misc_cols2 = st.columns(2)
    with misc_cols1:
        st.write("**System Settings**")
        if st.button("Open Developer Settings"):
            adb(["shell", "am", "start", "-a", "android.settings.APPLICATION_DEVELOPMENT_SETTINGS"])
    with misc_cols2:
        st.write("**Screen Stay-On**")
        stay_on_choice = st.radio("Mode", ["Off", "USB", "Always"], horizontal=True)
        if st.button("Set Stay-On Mode"):
            mode_map = {"Off": "false", "USB": "usb", "Always": "true"}
            adb(["shell", "svc", "power", "stayon", mode_map[stay_on_choice]])
            st.success(f"Set stay-on mode to {stay_on_choice}")

# --- About Tab ---
with tabs[11]:
    st.header("About ADB Admin")
    st.markdown("""
        An all-in-one tool written in `Python` to remotely manage Android devices using `ADB` (Android Debug Bridge).
    """)

    st.markdown("---")

    st.subheader("Changelog (v2.0)")
    st.markdown("""
    *   **Initial Release:** A brand new, intuitive web application for comprehensive Android device management using ADB.
    *   **Cross-Platform Compatibility:** Enhanced launcher scripts for Windows, Linux, and macOS, and improved internal logic for better cross-platform support.
    *   **Improved Nmap Integration:** Fixed Nmap executable detection and usage, allowing for reliable network scanning across different environments.
    *   **Robust Screen Control:** Corrected "Screen Stay-On" functionality and implemented a more reliable "Unlock Device" mechanism.
    *   **Enhanced Data Extraction:** Updated "Quick Data Pulls" for WhatsApp, Screenshots, and Camera Photos to handle modern Android paths. Improved "Content Dumps" for SMS, Contacts, and Call Logs with better error handling and clearer explanations for security restrictions on non-rooted devices.
    *   **Root Access Check:** Added a new feature to detect root access and provide guidance for accessing restricted data on rooted devices.
    """)

    st.markdown("---")

    st.subheader("Credits & Licensing")
    st.markdown("""
    *   **Developer:** Samith Hettiarachchi ( Nepstro )
    *   **GitHub:** [https://github.com/Nepstro/ADB-Admin-by-Nepstro](https://github.com/Nepstro/ADB-Admin-by-Nepstro)
    
    This program is free software, distributed under the terms of the **GNU General Public License v3.0**.
    """)

    st.markdown("---")

    st.subheader("Disclaimer")
    st.warning("""
    *   This project and its developers do not promote any illegal activity and are not responsible for any misuse or damage caused by this project.
    *   This project is for educational purposes only.
    *   Please do not use this tool on other people’s devices without their permission.
    *   Use this project responsibly and only on your own devices or with explicit authorization.
    *   It is the end user’s responsibility to obey all applicable local, state, federal, and international laws.
    """)