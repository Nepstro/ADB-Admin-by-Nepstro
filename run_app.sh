#!/bin/bash

# Check for python3
if ! command -v python3 &> /dev/null; then
    echo "python3 could not be found"
    echo "Please install Python 3.8+."
    exit
fi

# Check for pip
if ! python3 -m pip --version &> /dev/null; then
    echo "pip for python3 could not be found."
    echo "Please install pip for your python3 installation."
    exit
fi

# Function to display menu
show_menu() {
    clear
    echo "=================================================="
    echo "             ADB Admin - Launcher"
    echo "=================================================="
    echo ""
    echo "Please select an option:"
    echo ""
    echo "  1. Install/Update Required Libraries"
    echo "  2. Run ADB Admin Web App"
    echo "  3. Exit"
    echo ""
}

# Function to install requirements
install_reqs() {
    echo ""
    echo "--- Installing required libraries from requirements.txt ---"
    python3 -m pip install -r requirements.txt
    echo ""
    echo "--- Installation complete! ---"
    read -p "Press Enter to continue..."
}

# Function to run app
run_app() {
    echo ""
    echo "--- Launching ADB Admin Web App ---"
    echo "Your web browser should open shortly. Press Ctrl+C to stop the server."
    echo ""
    python3 -m streamlit run ADB_ADMIN.py
}

# Main loop
while true; do
    show_menu
    read -p "Enter your choice (1, 2, or 3): " choice
    case $choice in
        1) install_reqs ;;
        2) run_app; break ;;
        3) exit 0 ;;
        *) echo "Invalid choice. Please try again."; read -p "Press Enter to continue..." ;;
    esac
done