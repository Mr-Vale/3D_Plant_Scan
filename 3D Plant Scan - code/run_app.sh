#!/bin/bash
# Fix permissions for Qt runtime directory
chmod 700 /run/user/1000

# Run your Plant3D Scan UI app
python3 scan_ui.py