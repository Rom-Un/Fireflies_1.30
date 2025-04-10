#!/bin/bash

# This script helps set up the Replit environment

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p data
mkdir -p data/admin_messages
mkdir -p data/ai_assistant
mkdir -p data/analytics
mkdir -p data/calendar
mkdir -p data/flashcards
mkdir -p data/gamification
mkdir -p data/user_settings

# Set permissions
echo "Setting permissions..."
chmod +x main.py
chmod +x pronote_web_app.py

# Print success message
echo "Setup complete! You can now run the application with 'python3 main.py'"