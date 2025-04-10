#!/usr/bin/env python3
"""
Main entry point for Replit
"""

# Import the app from the main file
from pronote_web_app import app

# Run the app
if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)