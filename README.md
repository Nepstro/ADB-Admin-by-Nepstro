# ADB Admin

[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

ADB Admin is a powerful and intuitive web-based application for managing and controlling Android devices using the Android Debug Bridge (ADB). It provides a user-friendly interface to perform a wide range of actions, from simple tasks like installing apps to more advanced operations like network scanning and data extraction.

![ADB Admin Screenshot](https://raw.githubusercontent.com/Nepstro/ADB-Admin/main/screenshots/screenshot.png)

## ✨ Features

ADB Admin is packed with features to make Android device management easier:

*   **🔌 Connection Management:**
    *   List connected devices.
    *   Enable ADB over Wi-Fi (tcpip).
    *   Connect to devices over the network and manage a list of saved devices.

*   **ℹ️ Comprehensive Device Information:**
    *   Fetch a detailed overview of your device, including model, manufacturer, Android version, battery stats, screen resolution, and more.

*   **📦 Application Management:**
    *   List all installed third-party or system applications.
    *   Install single or split APKs.
    *   Uninstall applications.
    *   Extract APK files from installed apps.

*   **📁 File Management:**
    *   Browse the device's file system.
    *   Upload (push) and download (pull) files.
    *   Preview images directly in the browser.
    *   Search for files within the current directory.

*   **📸 Media & Screen Control:**
    *   Take and view screenshots.
    *   Record the device screen.
    *   A live, interactive remote screen view with clickable taps and swipes.

*   **⚙️ Device Control:**
    *   Reboot the system, recovery, or bootloader.
    *   Power off the device.
    *   Simulate key events (Home, Back, Power, etc.).
    *   Control volume and connectivity (Wi-Fi, Bluetooth).

*   **⌨️ Interaction:**
    *   Open URLs directly on the device.
    *   Type text into input fields.
    *   Start applications.
    *   Prepare and open the SMS app with pre-filled information.

*   **👆 Gesture Simulation:**
    *   Simulate tap and swipe gestures with precise coordinates.

*   **📡 Network Tools:**
    *   Scan the local network for devices with an open ADB port (requires Nmap).
    *   Forward and reverse TCP ports.
    *   Ping hosts from the device.

*   **💾 Data Extraction:**
    *   Quickly pull common data folders like WhatsApp, Screenshots, and Camera photos.
    *   Dump SMS, contacts, and call logs (may require root on modern Android versions).

*   **⚡ Advanced Actions:**
    *   Check for root access.
    *   Manage the ADB server.
    *   Execute raw shell commands.
    *   Force-stop, clear data, and restart apps.
    *   Grant or revoke app permissions.

## 🚀 Getting Started

### Prerequisites

*   **Python 3.8+**
*   **ADB (Android Debug Bridge):** Part of the Android SDK Platform Tools. You can either install it and add it to your system's PATH, or the application will prompt you for the path to the executable.
*   **(Optional) Nmap:** For the network scanning feature. Install it from [nmap.org](https://nmap.org) and ensure it's in your system's PATH.

### Installation & Usage

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Nepstro/ADB-Admin.git
    cd ADB-Admin
    ```

2.  **Install the required Python libraries:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Run the application:**
    *   On **Windows**, execute `run_app.cmd`.
    *   On **Linux/macOS**, execute `run_app.sh`.

    These scripts will start the Streamlit web server.

4.  **Open your web browser** and navigate to the local URL provided in the terminal (usually `http://localhost:8501`).

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

*   For minor changes, feel free to fork the project and open a pull request.
*   For major changes, please open an issue first to discuss your ideas.
*   Please try to make valuable contributions and avoid spam pull requests. Non-code PRs are not accepted.

## 📜 License

This project is licensed under the **GNU General Public License v3.0**. See the LICENSE file for details.

## ⚠️ Disclaimer

*   This project is for educational purposes only.
*   The developers are not responsible for any misuse or damage caused by this project.
*   Use this tool responsibly and only on your own devices or with explicit authorization.
*   It is the end user’s responsibility to obey all applicable local, state, and federal laws.