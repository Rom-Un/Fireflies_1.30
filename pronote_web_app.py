#!/usr/bin/env python3
"""
Fireflies - A web application to access Pronote data
"""

import pronotepy
import datetime
import os
import json
import pickle
import base64
from Crypto.Cipher import AES
from Crypto.Util.Padding import pad, unpad
from Crypto.Random import get_random_bytes
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from typing import Optional, List, Dict, Any
import secrets
from pathlib import Path
from translations import get_translation
from gamification import GamificationSystem
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Import our new features
from study_analytics import StudyAnalytics
from flashcard_system import FlashcardManager
from calendar_integration import CalendarIntegration

# Helper function to get homework for a user
def get_homework_for_user(username, start_date=None):
    """
    Get homework for a specific user
    
    Args:
        username: The username
        start_date: The start date (defaults to today)
        
    Returns:
        List of homework items in dictionary format
    """
    try:
        # Create a new client
        client = PronoteClient()
        
        # Check if the client is logged in
        if not client.logged_in:
            return []
        
        # Get homework
        homework_list = client.get_homework(start_date)
        
        # Convert to dictionary format
        return [
            {
                'id': str(hw.id),
                'subject': hw.subject.name,
                'description': hw.description,
                'date': hw.date.strftime('%Y-%m-%d'),
                'done': hw.done,
                'estimated_time': 60  # Default to 60 minutes
            }
            for hw in homework_list
        ]
    except Exception as e:
        print(f"Error getting homework for user {username}: {e}")
        return []

# Initialize Flask app
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)  # Generate a random secret key

# Download NLTK data for AI Learning Assistant
def download_nltk_data():
    """Download required NLTK data for the AI Learning Assistant"""
    try:
        import nltk
        nltk.download('punkt', quiet=True)
        nltk.download('stopwords', quiet=True)
        nltk.download('wordnet', quiet=True)
        print("NLTK data downloaded successfully")
    except Exception as e:
        print(f"Warning: Could not download NLTK data: {e}")

# Download NLTK data on startup
download_nltk_data()

# Import routes after app is created to avoid circular imports
from routes import fireflies_routes

# Register the blueprint for new features
app.register_blueprint(fireflies_routes)

# Initialize global calendar integration
def get_calendar_integration(username):
    """Get a calendar integration instance for the given username"""
    return CalendarIntegration(username)

# Add custom Jinja filters
@app.template_filter('strptime')
def strptime_filter(date_str, format_str):
    """Convert a string to a datetime object using the given format"""
    return datetime.datetime.strptime(date_str, format_str).date()

# Default settings
DEFAULT_SETTINGS = {
    'theme': 'blue',
    'language': 'french'
}

# Email configuration for forwarding messages to the admin
ADMIN_EMAIL = "romain.isnel@free.fr"  # Replace with your actual email

# Function to save messages to a file for the admin
def save_message_for_admin(username, timestamp, message):
    """
    Save a message to a file for the admin to review

    Args:
        username: The username of the sender
        timestamp: The timestamp of the message
        message: The content of the message

    Returns:
        bool: True if the message was saved successfully, False otherwise
    """
    try:
        # Create the admin messages directory if it doesn't exist
        admin_dir = Path('data/admin_messages')
        os.makedirs(admin_dir, exist_ok=True)

        # Create a filename based on the timestamp
        filename = f"{timestamp.strftime('%Y%m%d_%H%M%S')}_{username}.txt"
        filepath = admin_dir / filename

        # Write the message to the file
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"From: {username}\n")
            f.write(f"Date: {timestamp.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Message:\n\n{message}\n")

        print(f"Message saved to {filepath}")
        return True
    except Exception as e:
        print(f"Error saving message: {e}")
        return False

# Context processor to add settings to all templates
@app.context_processor
def inject_settings():
    """Add settings to all templates"""
    settings = load_settings() if 'load_settings' in globals() else DEFAULT_SETTINGS
    return {'settings': settings}

# Context processor to add current year to all templates
@app.context_processor
def inject_now():
    """Add current year to all templates"""
    return {'now': datetime.datetime.now()}

# Context processor to add translation function to all templates
@app.context_processor
def inject_translate():
    """Add translation function to all templates"""
    def translate(text):
        language = session.get('language', 'french')
        print(f"Translating '{text}' to language: {language}")
        translated = get_translation(text, language)
        print(f"Translated result: '{translated}'")
        return translated
    return {'_': translate}

# Create necessary directories
os.makedirs('templates', exist_ok=True)
os.makedirs('data', exist_ok=True)

# Path for saved credentials and settings
CREDENTIALS_FILE = Path('data/credentials.pickle')
SETTINGS_FILE = Path('data/settings.json')

# Encryption key file
KEY_FILE = Path('data/encryption.key')

# Generate or load encryption key
def get_encryption_key():
    """Get or create encryption key"""
    if not KEY_FILE.exists():
        # Generate a new key if it doesn't exist
        key = get_random_bytes(32)  # 256-bit key for AES-256
        with open(KEY_FILE, 'wb') as f:
            f.write(key)
        return key
    else:
        # Load existing key
        with open(KEY_FILE, 'rb') as f:
            return f.read()

# Encryption functions
def encrypt_password(password: str) -> str:
    """Encrypt a password string"""
    key = get_encryption_key()
    cipher = AES.new(key, AES.MODE_CBC)
    ct_bytes = cipher.encrypt(pad(password.encode('utf-8'), AES.block_size))
    iv = base64.b64encode(cipher.iv).decode('utf-8')
    ct = base64.b64encode(ct_bytes).decode('utf-8')
    return f"{iv}:{ct}"

def decrypt_password(encrypted_password: str) -> str:
    """Decrypt an encrypted password string"""
    try:
        key = get_encryption_key()
        iv, ct = encrypted_password.split(':')
        iv = base64.b64decode(iv)
        ct = base64.b64decode(ct)
        cipher = AES.new(key, AES.MODE_CBC, iv)
        pt = unpad(cipher.decrypt(ct), AES.block_size)
        return pt.decode('utf-8')
    except Exception as e:
        print(f"Error decrypting password: {e}")
        return ""

class PronoteClient:
    """Class to handle Pronote API interactions"""
    
    def __init__(self):
        self.client = None
        self.logged_in = False
    
    def login(self, url: str, username: str, password: str, ent: Optional[Any] = None) -> bool:
        """
        Log in to Pronote

        Args:
            url: The Pronote URL
            username: The username
            password: The password
            ent: The ENT function (optional)

        Returns:
            bool: True if login successful, False otherwise
        """
        try:
            # The API has changed, now we need to pass parameters directly
            self.client = pronotepy.Client(url,
                                          username=username,
                                          password=password,
                                          ent=ent)
            self.logged_in = self.client.logged_in
            return self.logged_in
        except Exception as e:
            return False, str(e)
    
    def get_homework(self, start_date: Optional[datetime.date] = None) -> List[Any]:
        """
        Get homework from start_date
        
        Args:
            start_date: The start date (defaults to today)
            
        Returns:
            List of homework
        """
        if not self.logged_in or not self.client:
            return []
        
        if start_date is None:
            start_date = datetime.date.today()
        
        try:
            return self.client.homework(start_date)
        except Exception:
            return []
    
    def get_grades(self, period_index: Optional[int] = None) -> List[Any]:
        """
        Get grades for a specific period or all periods
        
        Args:
            period_index: The period index (None for current period)
            
        Returns:
            List of grades
        """
        if not self.logged_in or not self.client:
            return []
        
        try:
            if period_index is not None:
                if 0 <= period_index < len(self.client.periods):
                    return self.client.periods[period_index].grades
                else:
                    return []
            else:
                return self.client.current_period.grades
        except Exception:
            return []
    
    def get_periods(self) -> List[Any]:
        """
        Get all periods

        Returns:
            List of periods
        """
        if not self.logged_in or not self.client:
            return []

        try:
            return self.client.periods
        except Exception:
            return []

    def get_period_averages(self, period_index: Optional[int] = None) -> Dict[str, Any]:
        """
        Get averages for a specific period

        Args:
            period_index: The period index (None for current period)

        Returns:
            Dictionary with overall, class, min, and max averages
        """
        if not self.logged_in or not self.client:
            print("Not logged in or client is None")
            return {
                'overall': 0,
                'class': 0,
                'min': 0,
                'max': 0
            }

        try:
            # Get the period
            period = None
            if period_index is not None:
                if 0 <= period_index < len(self.client.periods):
                    period = self.client.periods[period_index]
                else:
                    print(f"Invalid period index: {period_index}")
                    return {
                        'overall': 0,
                        'class': 0,
                        'min': 0,
                        'max': 0
                    }
            else:
                period = self.client.current_period

            # Get the overall average
            overall_avg = 0
            try:
                # Try to get the overall_average attribute
                overall_avg = getattr(period, 'overall_average', 0)
                if overall_avg is None:
                    overall_avg = 0
                print(f"Overall average from API: {overall_avg}")
            except Exception as e:
                print(f"Error getting overall average: {e}")

            # Get the class average, min, and max
            class_avg = 0
            min_avg = 0
            max_avg = 0

            try:
                # Try to get the averages attribute
                averages = getattr(period, 'averages', [])
                if averages:
                    print(f"Found {len(averages)} averages")
                    for avg in averages:
                        # Print the average object to see its structure
                        print(f"Average object: {avg}")

                        # Try to get class average
                        if hasattr(avg, 'class_average'):
                            class_avg = avg.class_average
                            print(f"Class average from API: {class_avg}")

                        # Try to get min average
                        if hasattr(avg, 'min'):
                            min_avg = avg.min
                            print(f"Min average from API: {min_avg}")

                        # Try to get max average
                        if hasattr(avg, 'max'):
                            max_avg = avg.max
                            print(f"Max average from API: {max_avg}")

                        # If we found values, break the loop
                        if class_avg or min_avg or max_avg:
                            break
            except Exception as e:
                print(f"Error getting class averages: {e}")

            return {
                'overall': float(overall_avg) if overall_avg else 0,
                'class': float(class_avg) if class_avg else 0,
                'min': float(min_avg) if min_avg else 0,
                'max': float(max_avg) if max_avg else 0
            }
        except Exception as e:
            print(f"Error in get_period_averages: {e}")
            return {
                'overall': 0,
                'class': 0,
                'min': 0,
                'max': 0
            }
    
    def get_lessons(self, date: Optional[datetime.date] = None) -> List[Any]:
        """
        Get lessons for a specific date
        
        Args:
            date: The date (defaults to today)
            
        Returns:
            List of lessons
        """
        if not self.logged_in or not self.client:
            return []
        
        if date is None:
            date = datetime.date.today()
        
        try:
            return self.client.lessons(date)
        except Exception:
            return []
    
    def check_session(self) -> bool:
        """
        Check if the session is still valid and refresh if needed

        Returns:
            bool: True if session was refreshed, False otherwise
        """
        if not self.logged_in or not self.client:
            print("Session check failed: Not logged in or client is None")
            return False

        try:
            result = self.client.session_check()
            if not result:
                print("Session check returned False")
            return result
        except Exception as e:
            print(f"Session check error: {e}")
            return False

    def toggle_homework_status(self, homework_id: str) -> bool:
        """
        Toggle the done status of a homework

        Args:
            homework_id: The ID of the homework

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.logged_in or not self.client:
            print("Cannot toggle homework: Not logged in or client is None")
            return False

        try:
            # Get all homework - try to get a wider range to ensure we find the homework
            # Get homework for the next 30 days to be safe
            start_date = datetime.date.today()
            print(f"Fetching homework from {start_date} to find ID: {homework_id}")
            homework_list = self.get_homework(start_date)

            if not homework_list:
                print("No homework found when trying to toggle status")
                return False

            print(f"Found {len(homework_list)} homework items")

            # Find the homework with the matching ID
            for hw in homework_list:
                hw_id = str(hw.id)
                print(f"Checking homework ID: {hw_id} against {homework_id}")

                # Try different formats of the ID
                # 1. Direct match
                # 2. Match before the # fragment
                # 3. Match after the # fragment
                if (hw_id == homework_id or
                    (homework_id.find('#') > 0 and hw_id == homework_id.split('#')[0]) or
                    (homework_id.find('#') > 0 and hw_id == homework_id.split('#')[1])):
                    print(f"Found matching homework: {hw.subject.name}, due: {hw.date}, current status: {hw.done}")

                    # Toggle the done status
                    try:
                        new_status = not hw.done
                        print(f"Setting homework status to: {new_status}")
                        hw.set_done(new_status)

                        # Verify the status was changed
                        print(f"New status after toggle: {hw.done}")
                        return True
                    except Exception as e:
                        print(f"Error calling set_done: {e}")
                        return False

            print(f"Homework with ID {homework_id} not found in {len(homework_list)} items")
            return False
        except Exception as e:
            print(f"Error toggling homework status: {e}")
            return False

    def get_discussions(self, only_unread: bool = False) -> List[Any]:
        """
        Get discussions from Pronote

        Args:
            only_unread: If True, only return unread discussions

        Returns:
            List of discussions
        """
        if not self.logged_in or not self.client:
            return []

        try:
            # Check if discussions is a method or an attribute
            discussions_attr = getattr(self.client, 'discussions', None)

            if discussions_attr is None:
                print("Client has no discussions attribute")
                return []

            if callable(discussions_attr):
                # It's a method, call it with the parameter
                return discussions_attr(only_unread)
            else:
                # It's an attribute, return it directly
                return discussions_attr if isinstance(discussions_attr, list) else []
        except Exception as e:
            print(f"Error getting discussions: {e}")
            return []

    def get_recipients(self) -> List[Any]:
        """
        Get available recipients for new discussions

        Returns:
            List of recipients
        """
        if not self.logged_in or not self.client:
            return []

        try:
            # Check if get_recipients is a method or an attribute
            recipients_attr = getattr(self.client, 'get_recipients', None)

            if recipients_attr is None:
                print("Client has no get_recipients attribute")
                return []

            if callable(recipients_attr):
                # It's a method, call it
                return recipients_attr()
            else:
                # It's an attribute, return it directly
                return recipients_attr if isinstance(recipients_attr, list) else []
        except Exception as e:
            print(f"Error getting recipients: {e}")
            return []

    def send_discussion(self, subject: str, message: str, recipients: List[Any]) -> bool:
        """
        Send a new discussion

        Args:
            subject: The subject of the discussion
            message: The content of the discussion
            recipients: List of recipient objects

        Returns:
            bool: True if successful, False otherwise
        """
        if not self.logged_in or not self.client:
            print("Cannot send discussion: Not logged in or client is None")
            return False

        try:
            # Check if new_discussion is a method
            new_discussion_attr = getattr(self.client, 'new_discussion', None)

            if new_discussion_attr is None:
                print("Client has no new_discussion attribute")
                return False

            if callable(new_discussion_attr):
                # It's a method, call it with parameters
                new_discussion_attr(subject, message, recipients)
                return True
            else:
                print("new_discussion is not callable")
                return False
        except Exception as e:
            print(f"Error sending discussion: {e}")
            return False


# Create a global client instance
pronote_client = PronoteClient()

# Helper functions for credentials
def save_credentials(credentials: Dict[str, Any]) -> None:
    """Save credentials to file with encrypted password"""
    # Encrypt the password before saving
    if 'password' in credentials:
        credentials['password'] = encrypt_password(credentials['password'])

    with open(CREDENTIALS_FILE, 'wb') as f:
        pickle.dump(credentials, f)

def load_credentials() -> Optional[Dict[str, Any]]:
    """Load credentials from file and decrypt password"""
    if not CREDENTIALS_FILE.exists():
        return None

    try:
        with open(CREDENTIALS_FILE, 'rb') as f:
            credentials = pickle.load(f)

        # Decrypt the password if it exists and appears to be encrypted
        if 'password' in credentials and ':' in credentials['password']:
            try:
                credentials['password'] = decrypt_password(credentials['password'])
            except Exception as e:
                print(f"Error decrypting password: {e}")
                # If decryption fails, return None to force re-login
                return None

        return credentials
    except Exception as e:
        print(f"Error loading credentials: {e}")
        return None

# Helper functions for settings
def save_settings(settings: Dict[str, Any]) -> None:
    """Save settings to file"""
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(settings, f)

def load_settings() -> Dict[str, Any]:
    """Load settings from file"""
    if not SETTINGS_FILE.exists():
        return DEFAULT_SETTINGS.copy()

    try:
        with open(SETTINGS_FILE, 'r') as f:
            settings = json.load(f)
            # Ensure all default settings exist
            for key, value in DEFAULT_SETTINGS.items():
                if key not in settings:
                    settings[key] = value
            return settings
    except Exception:
        return DEFAULT_SETTINGS.copy()

def get_ent_function(ent_name: Optional[str]) -> Optional[Any]:
    """Get ENT function by name"""
    if not ent_name:
        return None

    try:
        from pronotepy.ent import (
            ac_reunion, ac_reims, ac_orleans_tours, ac_montpellier,
            ac_lille, ac_nancy_metz, ac_nantes, ac_bordeaux,
            ac_toulouse, ac_caen, ac_rouen, ac_poitiers,
            ac_grenoble, ac_lyon, ac_clermont, ac_dijon,
            ac_besancon, ac_strasbourg, ac_creteil, ac_versailles,
            ac_paris
        )

        ent_map = {
            'ac_reunion': ac_reunion,
            'ac_reims': ac_reims,
            'ac_orleans_tours': ac_orleans_tours,
            'ac_montpellier': ac_montpellier,
            'ac_lille': ac_lille,
            'ac_nancy_metz': ac_nancy_metz,
            'ac_nantes': ac_nantes,
            'ac_bordeaux': ac_bordeaux,
            'ac_toulouse': ac_toulouse,
            'ac_caen': ac_caen,
            'ac_rouen': ac_rouen,
            'ac_poitiers': ac_poitiers,
            'ac_grenoble': ac_grenoble,
            'ac_lyon': ac_lyon,
            'ac_clermont': ac_clermont,
            'ac_dijon': ac_dijon,
            'ac_besancon': ac_besancon,
            'ac_strasbourg': ac_strasbourg,
            'ac_creteil': ac_creteil,
            'ac_versailles': ac_versailles,
            'ac_paris': ac_paris
        }

        return ent_map.get(ent_name)
    except ImportError:
        return None

# Routes
@app.route('/')
def index():
    """Home page route"""
    if 'logged_in' in session and session['logged_in']:
        return redirect(url_for('dashboard'))

    # Load saved credentials
    saved_credentials = load_credentials()

    # Load settings
    settings = load_settings()

    # Set language and settings in session
    session['language'] = settings.get('language', 'english')
    session['settings'] = settings

    return render_template('login.html', saved_credentials=saved_credentials, settings=settings)

@app.route('/login', methods=['POST'])
def login():
    """Login route"""
    url = request.form.get('url', '').strip()
    username = request.form.get('username', '').strip()
    password = request.form.get('password', '')
    use_ent = request.form.get('use_ent') == 'on'
    ent_name = request.form.get('ent_name') if use_ent else None
    save_credentials_option = request.form.get('save_credentials') == 'on'

    if not url or not username or not password:
        flash('Please fill in all fields', 'error')
        return redirect(url_for('index'))

    # Get ENT function if needed
    ent_function = get_ent_function(ent_name) if use_ent else None

    if use_ent and not ent_function and ent_name:
        flash('Failed to load ENT function', 'error')
        return redirect(url_for('index'))

    # Try to login
    result = pronote_client.login(url, username, password, ent_function)

    if isinstance(result, tuple) and not result[0]:
        flash(f'Login failed: {result[1]}', 'error')
        return redirect(url_for('index'))
    elif not result:
        flash('Login failed: Invalid credentials or URL', 'error')
        return redirect(url_for('index'))

    # Save credentials if requested
    if save_credentials_option:
        credentials = {
            'url': url,
            'username': username,
            'password': password,
            'use_ent': use_ent,
            'ent_name': ent_name
        }
        save_credentials(credentials)
    elif CREDENTIALS_FILE.exists():
        # If not saving but credentials file exists, delete it
        CREDENTIALS_FILE.unlink(missing_ok=True)

    session['logged_in'] = True
    session['username'] = username

    # Update gamification login streak
    gamification_system = GamificationSystem(username)
    streak_result = gamification_system.update_login_streak()

    if streak_result['points_earned'] > 0:
        flash(streak_result['message'], 'success')

    # Load settings
    settings = load_settings()
    session['language'] = settings.get('language', 'english')
    session['settings'] = settings

    flash('Login successful!', 'success')
    return redirect(url_for('dashboard'))

@app.route('/logout')
def logout():
    """Logout route"""
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
def dashboard():
    """Dashboard route"""
    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('index'))

    # Check session
    pronote_client.check_session()

    # Get today's date
    today_date = datetime.date.today().strftime("%A, %B %d, %Y")

    # Get today's lessons
    today_lessons = pronote_client.get_lessons(datetime.date.today())

    # Convert lesson objects to dictionaries for template
    today_lessons_data = []
    for lesson in sorted(today_lessons, key=lambda x: x.start):
        today_lessons_data.append({
            'subject': lesson.subject.name,
            'start': lesson.start.strftime('%H:%M'),
            'end': lesson.end.strftime('%H:%M'),
            'room': lesson.classroom,
            'teacher': lesson.teacher_name
        })

    # Get upcoming homework (next 7 days)
    upcoming_homework = pronote_client.get_homework(datetime.date.today())

    # Convert homework objects to dictionaries for template
    upcoming_homework_data = []
    for hw in upcoming_homework:
        upcoming_homework_data.append({
            'id': str(hw.id),
            'subject': hw.subject.name,
            'description': hw.description,
            'date': hw.date.strftime('%Y-%m-%d'),
            'done': hw.done
        })

    # Sort homework by due date (ascending)
    upcoming_homework_data.sort(key=lambda x: x['date'])

    # Limit to 5 items for dashboard (after sorting)
    upcoming_homework_data = upcoming_homework_data[:5]
    
    # Initialize calendar integration for homework prioritization
    username = session.get('username', 'unknown_user')
    calendar_integration = get_calendar_integration(username)
    
    # Prioritize homework
    try:
        # Add estimated time to homework (default to 60 minutes)
        for hw in upcoming_homework_data:
            hw['estimated_time'] = 60
            
        # Prioritize homework
        prioritized_homework = calendar_integration.prioritize_homework(upcoming_homework_data)
        
        # Add prioritized homework to the template context
        high_priority = [hw for hw in prioritized_homework if hw.get('priority_level') == 'high']
        medium_priority = [hw for hw in prioritized_homework if hw.get('priority_level') == 'medium']
        low_priority = [hw for hw in prioritized_homework if hw.get('priority_level') == 'low']
    except Exception as e:
        print(f"Error prioritizing homework: {e}")
        high_priority = []
        medium_priority = []
        low_priority = []

    # Get recent grades
    recent_grades = pronote_client.get_grades()

    # Convert grade objects to dictionaries for template
    recent_grades_data = []
    for grade in recent_grades:
        # Get coefficient, default to 1 if not available
        coefficient = getattr(grade, 'coefficient', '1')

        # Get class average, min, and max if available
        class_average = getattr(grade, 'average', '')
        class_min = getattr(grade, 'min', '')
        class_max = getattr(grade, 'max', '')

        recent_grades_data.append({
            'subject': grade.subject.name,
            'grade': grade.grade,
            'out_of': grade.out_of,
            'date': grade.date.strftime('%Y-%m-%d'),
            'comment': grade.comment,
            'coefficient': coefficient,
            'class_average': class_average,
            'class_min': class_min,
            'class_max': class_max
        })

    # Sort grades by date (most recent first)
    recent_grades_data.sort(key=lambda x: x['date'], reverse=True)

    # Limit to 5 items for dashboard (after sorting)
    recent_grades_data = recent_grades_data[:5]

    # Load settings
    settings = load_settings()

    return render_template('dashboard.html',
                          username=session.get('username', ''),
                          today_date=today_date,
                          today_lessons=today_lessons_data,
                          upcoming_homework=upcoming_homework_data,
                          recent_grades=recent_grades_data,
                          settings=settings)

@app.route('/homework')
def homework():
    """Homework route"""
    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('index'))

    # Check session
    pronote_client.check_session()

    days_ahead = request.args.get('days', '7')
    try:
        days = int(days_ahead)
        start_date = datetime.date.today()
        end_date = start_date + datetime.timedelta(days=days)
        
        # Get all homework for the filtered view
        homework_list = pronote_client.get_homework(start_date)

        # Convert homework objects to dictionaries for template and filter by date range
        homework_data = []
        for hw in homework_list:
            # Only include homework due within the specified date range
            if hw.date <= end_date:
                homework_data.append({
                    'id': str(hw.id),
                    'subject': hw.subject.name,
                    'description': hw.description,
                    'date': hw.date.strftime('%Y-%m-%d'),
                    'done': hw.done,
                    'estimated_time': 60  # Default to 60 minutes
                })

        # Sort homework by due date (ascending)
        homework_data.sort(key=lambda x: x['date'])

        # Get today's date for calculations
        today_date = datetime.date.today()
        today = today_date.strftime('%Y-%m-%d')

        # Add a function to calculate days between dates
        def days_between(d1_str, d2_str):
            d1 = datetime.date.fromisoformat(d1_str)
            d2 = datetime.date.fromisoformat(d2_str)
            return (d1 - d2).days

        # Get username from session
        username = session.get('username', 'unknown_user')
        
        # Initialize calendar integration for priority calculation
        calendar_integration = CalendarIntegration(username)
        
        # Get all homework for priority view (not filtered by days)
        all_homework_list = pronote_client.get_homework(start_date)
        
        # Convert all homework to dictionary format for priority calculation
        all_homework_data = []
        for hw in all_homework_list:
            all_homework_data.append({
                'id': str(hw.id),
                'subject': hw.subject.name,
                'description': hw.description,
                'date': hw.date.strftime('%Y-%m-%d'),
                'done': hw.done,
                'estimated_time': 60  # Default to 60 minutes
            })
        
        # Prioritize all homework (not just the filtered ones)
        prioritized_homework = calendar_integration.prioritize_homework(all_homework_data)
        
        # Group by priority level
        high_priority = [hw for hw in prioritized_homework if hw.get('priority_level') == 'high']
        medium_priority = [hw for hw in prioritized_homework if hw.get('priority_level') == 'medium']
        low_priority = [hw for hw in prioritized_homework if hw.get('priority_level') == 'low']
        
        # Add days_until_due to each homework item for the priority view
        for hw in high_priority + medium_priority + low_priority:
            hw['days_until_due'] = days_between(hw['date'], today)

        # Load settings
        settings = load_settings()

        return render_template('homework.html',
                              homework=homework_data,
                              high_priority=high_priority,
                              medium_priority=medium_priority,
                              low_priority=low_priority,
                              days=days,
                              today=today,
                              days_between=days_between,
                              settings=settings)
    except ValueError:
        flash('Invalid number of days', 'error')
        return redirect(url_for('dashboard'))

@app.route('/toggle_homework/<homework_id>', methods=['POST'])
def toggle_homework(homework_id):
    """Toggle homework status route"""
    if not session.get('logged_in'):
        return {'success': False, 'message': 'Not logged in'}, 401

    # Check session - but don't fail if it doesn't refresh
    # This allows the toggle to work even if the session check fails
    print(f"Checking session for homework toggle: {homework_id}")
    try:
        pronote_client.check_session()
    except Exception as e:
        print(f"Session check exception (continuing anyway): {e}")

    # Try to get the full homework ID from the request body
    try:
        data = request.get_json(silent=True)
        if data and 'homeworkId' in data:
            full_homework_id = data['homeworkId']
            print(f"Using full homework ID from request body: {full_homework_id}")
            # If the full ID contains a fragment, use it
            if '#' in full_homework_id:
                homework_id = full_homework_id
    except Exception as e:
        print(f"Error parsing request body: {e}")

    # Toggle homework status
    print(f"Attempting to toggle homework status for ID: {homework_id}")

    # Get all homework to log available IDs for debugging
    try:
        all_homework = pronote_client.get_homework(datetime.date.today())
        print(f"Available homework IDs: {[str(hw.id) for hw in all_homework]}")
    except Exception as e:
        print(f"Error getting all homework for debugging: {e}")

    success = pronote_client.toggle_homework_status(homework_id)

    if success:
        print(f"Successfully toggled homework status for ID: {homework_id}")

        # Track homework completion for gamification
        username = session.get('username', 'unknown_user')
        gamification_system = GamificationSystem(username)
        gamification_result = gamification_system.track_homework_completion()

        return {
            'success': True,
            'gamification': {
                'points_earned': gamification_result['points_earned'],
                'message': gamification_result['message']
            }
        }, 200
    else:
        print(f"Failed to toggle homework status for ID: {homework_id}")
        return {'success': False, 'message': 'Failed to toggle homework status'}, 400

@app.route('/api/homework/update_time', methods=['POST'])
def update_homework_time():
    """API endpoint to update estimated completion time for homework"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Get request data
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    # Get required fields
    homework_id = data.get('homework_id')
    estimated_time = data.get('estimated_time')
    
    # Validate required fields
    if not homework_id:
        return jsonify({'success': False, 'message': 'Homework ID is required'}), 400
    
    if estimated_time is None:
        return jsonify({'success': False, 'message': 'Estimated time is required'}), 400
    
    try:
        # Initialize calendar integration
        calendar_integration = CalendarIntegration(username)
        
        # Get homework from Pronote
        start_date = datetime.date.today()
        homework_list = pronote_client.get_homework(start_date)
        
        # Convert to dictionary format with updated estimated time
        homework_data = []
        for hw in homework_list:
            hw_data = {
                'id': str(hw.id),
                'subject': hw.subject.name,
                'description': hw.description,
                'date': hw.date.strftime('%Y-%m-%d'),
                'done': hw.done,
                'estimated_time': estimated_time if str(hw.id) == homework_id else 60
            }
            homework_data.append(hw_data)
        
        # Prioritize homework
        prioritized_homework = calendar_integration.prioritize_homework(homework_data)
        
        return jsonify({'success': True, 'homework': prioritized_homework}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error updating homework time: {e}'}), 500

@app.route('/settings')
def settings():
    """Settings route"""
    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('index'))

    # Load current settings
    current_settings = load_settings()

    return render_template('settings.html', settings=current_settings)

@app.route('/accessibility')
def accessibility():
    """Accessibility settings route"""
    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('index'))
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Load user accessibility settings
    user_settings = {}
    settings_file = Path(f'data/user_settings/{username}_accessibility.json')
    
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                user_settings = json.load(f)
        except Exception as e:
            print(f"Error loading accessibility settings: {e}")
    
    # Load general settings
    settings = load_settings()
    
    return render_template('accessibility.html',
                          user_settings=user_settings,
                          settings=settings)

@app.route('/set_language', methods=['POST'])
def set_language():
    """Set language route"""
    if not session.get('logged_in'):
        return {'success': False, 'message': 'Not logged in'}, 401

    # Get language from request
    data = request.get_json()
    language = data.get('language', 'english')

    print(f"Setting language to: {language}")

    # Validate language
    if language not in ['english', 'french']:
        return {'success': False, 'message': 'Invalid language'}, 400

    # Update settings
    current_settings = load_settings()
    current_settings['language'] = language
    save_settings(current_settings)

    # Update session
    session['language'] = language

    # Update settings in session
    session['settings'] = current_settings

    return {'success': True}, 200

@app.route('/set_theme', methods=['POST'])
def set_theme():
    """Set theme route"""
    if not session.get('logged_in'):
        return {'success': False, 'message': 'Not logged in'}, 401

    # Get theme from request
    data = request.get_json()
    theme = data.get('theme', 'blue')

    # Validate theme
    if theme not in ['blue', 'green', 'red', 'purple', 'dark']:
        return {'success': False, 'message': 'Invalid theme'}, 400

    # Update settings
    current_settings = load_settings()
    current_settings['theme'] = theme
    save_settings(current_settings)

    # Update session
    session['settings'] = current_settings

    return {'success': True}, 200

@app.route('/grades')
def grades():
    """Grades route"""
    # Initialize default values for chart data and averages
    chart_data = {
        'labels': [],
        'student_avg': [],
        'class_avg': [],
        'min_avg': [],
        'max_avg': []
    }
    overall_average = 0
    latest_class_avg = 0
    latest_min_avg = 0
    latest_max_avg = 0

    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('index'))

    # Check session
    pronote_client.check_session()

    # Track grade view for gamification
    username = session.get('username', 'unknown_user')
    gamification_system = GamificationSystem(username)
    gamification_result = gamification_system.track_grade_view()

    if gamification_result['points_earned'] > 0:
        flash(gamification_result['message'], 'success')

    # Get filter parameters
    period_index = request.args.get('period')
    subject_filter = request.args.get('subject')
    view_mode = request.args.get('view_mode', 'chronological')  # 'chronological' or 'by_subject'
    sort_order = request.args.get('sort_order', 'date')  # 'date', 'best_first', or 'worst_first'

    # Get periods for dropdown
    periods = pronote_client.get_periods()
    period_options = [{'index': None, 'name': 'Current Period'}]
    for i, period in enumerate(periods):
        period_options.append({
            'index': i,
            'name': period.name
        })

    # Get grades for selected period
    try:
        # Convert period_index to integer if it's a valid string
        if period_index is not None and period_index != '':
            try:
                period_index = int(period_index)
            except ValueError:
                # If conversion fails, use None (current period)
                period_index = None
        else:
            period_index = None

        # Get period averages directly from the API
        period_averages = pronote_client.get_period_averages(period_index)
        print(f"Period averages from API: {period_averages}")

        # Set the averages from the API and ensure they're properly formatted
        overall_average = round(float(period_averages['overall']), 2) if period_averages['overall'] else 0
        latest_class_avg = round(float(period_averages['class']), 2) if period_averages['class'] else 0
        latest_min_avg = round(float(period_averages['min']), 2) if period_averages['min'] else 0
        latest_max_avg = round(float(period_averages['max']), 2) if period_averages['max'] else 0

        print(f"Formatted averages: overall={overall_average}, class={latest_class_avg}, min={latest_min_avg}, max={latest_max_avg}")

        grades_list = pronote_client.get_grades(period_index)

        # Debug log
        print(f"Retrieved {len(grades_list)} grades from Pronote for period {period_index}")

        # Convert grade objects to dictionaries for template
        grades_data = []
        for grade in grades_list:
            # Get coefficient, default to 1 if not available
            coefficient = getattr(grade, 'coefficient', '1')

            # Get class average, min, and max if available
            class_average = getattr(grade, 'average', '')
            class_min = getattr(grade, 'min', '')
            class_max = getattr(grade, 'max', '')

            grades_data.append({
                'subject': grade.subject.name,
                'grade': grade.grade,
                'out_of': grade.out_of,
                'date': grade.date.strftime('%Y-%m-%d'),
                'comment': grade.comment,
                'coefficient': coefficient,
                'class_average': class_average,
                'class_min': class_min,
                'class_max': class_max
            })

        # Sort grades based on sort_order
        if view_mode == 'chronological':
            if sort_order == 'date':
                # Sort by date (newest first)
                grades_data.sort(key=lambda x: x['date'], reverse=True)
            elif sort_order == 'best_first':
                # Sort by percentage (best first)
                def get_percentage(grade):
                    try:
                        return float(grade['grade']) / float(grade['out_of']) * 100
                    except (ValueError, ZeroDivisionError):
                        return 0

                grades_data.sort(key=get_percentage, reverse=True)
            elif sort_order == 'worst_first':
                # Sort by percentage (worst first)
                def get_percentage(grade):
                    try:
                        return float(grade['grade']) / float(grade['out_of']) * 100
                    except (ValueError, ZeroDivisionError):
                        return 100

                grades_data.sort(key=get_percentage)

        # Apply subject filter if provided
        if subject_filter:
            grades_data = [g for g in grades_data if g['subject'].lower() == subject_filter.lower()]

        # Get unique subjects for filter dropdown
        all_subjects = sorted(list(set(g['subject'] for g in grades_data)))

        # Group grades by subject if view mode is 'by_subject'
        subjects_data = {}
        if view_mode == 'by_subject':
            for grade in grades_data:
                subject = grade['subject']
                if subject not in subjects_data:
                    subjects_data[subject] = {
                        'grades': [],
                        'average': 0,
                        'total_percentage': 0,
                        'count': 0
                    }
                subjects_data[subject]['grades'].append(grade)

                # Store the grade and out_of values for later average calculation
                try:
                    # Clean and convert grade values
                    grade_str = str(grade['grade']).replace(',', '.')
                    out_of_str = str(grade['out_of']).replace(',', '.')
                    grade_float = float(grade_str)
                    out_of_float = float(out_of_str)

                    if grade_float > 0 and out_of_float > 0:
                        # Calculate percentage
                        percentage = grade_float / out_of_float * 100

                        # Initialize arrays if they don't exist
                        if 'grade_values' not in subjects_data[subject]:
                            subjects_data[subject]['grade_values'] = []
                        if 'out_of_values' not in subjects_data[subject]:
                            subjects_data[subject]['out_of_values'] = []

                        # Store the actual values for later calculation
                        subjects_data[subject]['grade_values'].append(grade_float)
                        subjects_data[subject]['out_of_values'].append(out_of_float)

                        # Also keep the old calculation method for backward compatibility
                        subjects_data[subject]['total_percentage'] = subjects_data[subject].get('total_percentage', 0) + percentage
                        subjects_data[subject]['total_out_of_20'] = subjects_data[subject].get('total_out_of_20', 0) + (grade_float / out_of_float * 20)
                        subjects_data[subject]['count'] += 1
                except (ValueError, ZeroDivisionError):
                    # Skip grades that can't be converted to percentage
                    pass

            # Calculate average for each subject
            for subject in subjects_data:
                if subjects_data[subject]['count'] > 0:
                    # Calculate average using the stored grade values
                    if 'grade_values' in subjects_data[subject] and 'out_of_values' in subjects_data[subject]:
                        # Calculate the sum of percentages
                        total_percentage = 0
                        for i in range(len(subjects_data[subject]['grade_values'])):
                            grade_val = subjects_data[subject]['grade_values'][i]
                            out_of_val = subjects_data[subject]['out_of_values'][i]
                            total_percentage += (grade_val / out_of_val * 100)

                        # Calculate percentage average
                        subjects_data[subject]['average_percentage'] = round(
                            total_percentage / len(subjects_data[subject]['grade_values']), 2
                        )

                        # Calculate the average grade out of 20
                        total_grade_equivalent = 0
                        for i in range(len(subjects_data[subject]['grade_values'])):
                            grade_val = subjects_data[subject]['grade_values'][i]
                            out_of_val = subjects_data[subject]['out_of_values'][i]
                            total_grade_equivalent += (grade_val / out_of_val * 20)

                        subjects_data[subject]['average_out_of_20'] = round(
                            total_grade_equivalent / len(subjects_data[subject]['grade_values']), 2
                        )
                    else:
                        # Fallback to old method if arrays aren't available
                        subjects_data[subject]['average_percentage'] = round(
                            subjects_data[subject]['total_percentage'] / subjects_data[subject]['count'], 2
                        )
                        subjects_data[subject]['average_out_of_20'] = round(
                            subjects_data[subject]['total_out_of_20'] / subjects_data[subject]['count'], 2
                        )

                    # Make sure average_out_of_20 doesn't exceed 20
                    if subjects_data[subject]['average_out_of_20'] > 20:
                        subjects_data[subject]['average_out_of_20'] = 20.0

                    # Make sure average_percentage doesn't exceed 100
                    if subjects_data[subject]['average_percentage'] > 100:
                        subjects_data[subject]['average_percentage'] = 100.0

            # Sort subjects based on sort_order
            if sort_order == 'date':
                # Sort subjects alphabetically
                subjects_data = {k: subjects_data[k] for k in sorted(subjects_data.keys())}
            elif sort_order == 'best_first':
                # Sort subjects by average (best first)
                sorted_keys = sorted(subjects_data.keys(),
                                    key=lambda k: subjects_data[k]['average_percentage'],
                                    reverse=True)
                subjects_data = {k: subjects_data[k] for k in sorted_keys}
            elif sort_order == 'worst_first':
                # Sort subjects by average (worst first)
                sorted_keys = sorted(subjects_data.keys(),
                                    key=lambda k: subjects_data[k]['average_percentage'])
                subjects_data = {k: subjects_data[k] for k in sorted_keys}

            # Calculate overall average
            overall_average = 0
            overall_count = 0
            for subject in subjects_data:
                if 'average_out_of_20' in subjects_data[subject]:
                    overall_average += subjects_data[subject]['average_out_of_20']
                    overall_count += 1

            if overall_count > 0:
                overall_average = round(overall_average / overall_count, 2)
            else:
                overall_average = 0

            # Prepare data for the average over time chart
            # Sort grades by date
            sorted_grades = sorted(grades_data, key=lambda g: g['date'])

            # Debug log
            print(f"Sorted grades for chart: {len(sorted_grades)} items")
            if len(sorted_grades) > 0:
                print(f"First grade: {sorted_grades[0]}")

            # For the chart, we'll use a simplified approach with just the current values
            # This will show a flat line representing the current averages
            chart_data = {
                'labels': ['Current Period'],
                'student_avg': [overall_average],
                'class_avg': [latest_class_avg],
                'min_avg': [latest_min_avg],
                'max_avg': [latest_max_avg]
            }

            # If we have grades, add them to the chart for a more detailed view
            if sorted_grades:
                # Reset chart data
                chart_data = {
                    'labels': [],
                    'student_avg': [],
                    'class_avg': [],
                    'min_avg': [],
                    'max_avg': []
                }

                # Add the current period averages as the final point
                chart_data['labels'].append('Current')
                chart_data['student_avg'].append(overall_average)
                chart_data['class_avg'].append(latest_class_avg)
                chart_data['min_avg'].append(latest_min_avg)
                chart_data['max_avg'].append(latest_max_avg)

            # Get the latest values for display
            latest_class_avg = chart_data['class_avg'][-1] if chart_data['class_avg'] and len(chart_data['class_avg']) > 0 and chart_data['class_avg'][-1] is not None else 0
            latest_min_avg = chart_data['min_avg'][-1] if chart_data['min_avg'] and len(chart_data['min_avg']) > 0 and chart_data['min_avg'][-1] is not None else 0
            latest_max_avg = chart_data['max_avg'][-1] if chart_data['max_avg'] and len(chart_data['max_avg']) > 0 and chart_data['max_avg'][-1] is not None else 0

            # We're now using the period averages directly from the API
            # No need to recalculate them here
            pass

            # Debug log for chart data
            print(f"Chart data: {len(chart_data['labels'])} data points")
            print(f"Labels: {chart_data['labels']}")
            print(f"Student averages: {chart_data['student_avg']}")

        # Load settings
        settings = load_settings()

        return render_template('grades.html',
                              grades=grades_data,
                              periods=period_options,
                              selected_period=period_index,
                              subject_filter=subject_filter,
                              all_subjects=all_subjects,
                              view_mode=view_mode,
                              sort_order=sort_order,
                              subjects_data=subjects_data,
                              settings=settings,
                              chart_data=json.dumps(chart_data),
                              overall_average=overall_average,
                              latest_class_avg=latest_class_avg,
                              latest_min_avg=latest_min_avg,
                              latest_max_avg=latest_max_avg)
    except Exception as e:
        # Log the error for debugging
        print(f"Error in grades route: {e}")

        # Show a more helpful error message
        flash(f'Une erreur est survenue lors du chargement des notes: {str(e)}', 'error')

        # Return an empty grades page instead of redirecting
        return render_template('grades.html',
                              grades=[],
                              periods=period_options,
                              selected_period=None,
                              subject_filter=subject_filter,
                              all_subjects=[],
                              view_mode=view_mode,
                              sort_order=sort_order,
                              subjects_data={},
                              settings=load_settings())

@app.route('/timetable')
def timetable():
    """Timetable route"""
    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('index'))

    # Create a new client instance for this request
    username = session.get('username', 'unknown_user')
    url = session.get('url')
    password = session.get('password')
    ent = session.get('ent')
    
    # Initialize a new client
    pronote_client = PronoteClient()
    
    # Try to login
    if url and password:
        try:
            login_result = pronote_client.login(url, username, password, ent)
            if not pronote_client.logged_in:
                flash('Session expired. Please login again.', 'error')
                return redirect(url_for('index'))
        except Exception as e:
            flash(f'Error reconnecting to Pronote: {str(e)}', 'error')
            return redirect(url_for('index'))

    # Track timetable view for gamification
    username = session.get('username', 'unknown_user')
    gamification_system = GamificationSystem(username)
    gamification_result = gamification_system.track_timetable_view()

    if gamification_result['points_earned'] > 0:
        flash(gamification_result['message'], 'success')
        
    # Get study schedule data
    calendar_integration = CalendarIntegration(username)
    
    # Get study blocks, scheduled sessions, and preferences with error handling
    try:
        study_blocks = calendar_integration.get_study_blocks()
    except Exception as e:
        print(f"Error getting study blocks: {e}")
        study_blocks = []
    
    try:
        # Get scheduled study sessions for the next 14 days
        today = datetime.date.today()
        end_date = today + datetime.timedelta(days=14)
        scheduled_sessions = calendar_integration.get_scheduled_sessions(today, end_date)
    except AttributeError:
        # If the method doesn't exist, use an empty list
        print("Warning: get_scheduled_sessions method not found, using empty list")
        scheduled_sessions = []
    except Exception as e:
        print(f"Error getting scheduled sessions: {e}")
        scheduled_sessions = []
    
    try:
        study_preferences = calendar_integration.get_preferences()
    except Exception as e:
        print(f"Error getting study preferences: {e}")
        study_preferences = {
            "study_session_length": 45,
            "break_length": 15,
            "max_daily_study_time": 180,
            "calendar_sync_enabled": False
        }
    
    # Prepare day names for display
    day_names = ['Lundi', 'Mardi', 'Mercredi', 'Jeudi', 'Vendredi', 'Samedi', 'Dimanche']
    
    # Prepare subject priorities for display
    subject_priorities = []
    if study_preferences and 'subjects' in study_preferences:
        for subject in study_preferences['subjects']:
            priority_color = 'danger'
            priority_label = 'Haute'
            
            if subject['priority'] == 'medium':
                priority_color = 'warning'
                priority_label = 'Moyenne'
            elif subject['priority'] == 'low':
                priority_color = 'info'
                priority_label = 'Basse'
                
            subject_priorities.append({
                'name': subject['name'],
                'priority_color': priority_color,
                'priority_label': priority_label
            })

    date_str = request.args.get('date')
    view_type = request.args.get('view', 'day')  # Default to day view

    if not date_str:
        date = datetime.date.today()
    else:
        try:
            date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('Invalid date format (use YYYY-MM-DD)', 'error')
            return redirect(url_for('dashboard'))

    # For week view, calculate the start of the week (Monday)
    # and get lessons for the entire week
    if view_type == 'week':
        # Calculate the Monday of the current week
        monday = date - datetime.timedelta(days=date.weekday())

        # Get dates for the entire week (Monday to Sunday)
        week_dates = [monday + datetime.timedelta(days=i) for i in range(7)]

        # Dictionary to store lessons for each day
        week_lessons = {}

        # Dictionary to store subject colors
        subject_colors = {}
        colors = ['#4361ee', '#3a0ca3', '#4895ef', '#4cc9f0', '#f72585', '#7209b7', '#560bad', '#480ca8', '#3f37c9', '#4361ee']
        color_index = 0

        # Get lessons for each day of the week
        for day_date in week_dates:
            day_lessons = pronote_client.get_lessons(day_date)

            # Convert lesson objects to dictionaries
            day_lessons_data = []
            for lesson in sorted(day_lessons, key=lambda x: x.start):
                # Assign a consistent color to each subject
                subject_name = lesson.subject.name
                if subject_name not in subject_colors:
                    subject_colors[subject_name] = colors[color_index % len(colors)]
                    color_index += 1

                day_lessons_data.append({
                    'subject': subject_name,
                    'start': lesson.start.strftime('%H:%M'),
                    'end': lesson.end.strftime('%H:%M'),
                    'room': lesson.classroom,
                    'teacher': lesson.teacher_name,
                    'day': day_date.strftime('%A'),  # Add day name
                    'color': subject_colors[subject_name]  # Add color
                })

            # Store lessons for this day
            week_lessons[day_date.strftime('%Y-%m-%d')] = {
                'date': day_date.strftime('%Y-%m-%d'),
                'day_name': day_date.strftime('%A'),
                'lessons': day_lessons_data
            }

        # Calculate previous and next week dates
        prev_week = (monday - datetime.timedelta(days=7)).strftime('%Y-%m-%d')
        next_week = (monday + datetime.timedelta(days=7)).strftime('%Y-%m-%d')

        # Get username from session
        username = session.get('username', 'unknown_user')
        
        # Get calendar integration for study preferences
        calendar_integration = CalendarIntegration(username)
        study_preferences = calendar_integration.get_preferences()
        
        return render_template('timetable.html',
                              view_type=view_type,
                              week_lessons=week_lessons,
                              week_dates=week_dates,
                              date=date.strftime('%Y-%m-%d'),
                              monday=monday.strftime('%Y-%m-%d'),
                              prev_date=prev_week,
                              next_date=next_week,
                              today=datetime.date.today().strftime('%Y-%m-%d'),
                              study_preferences=study_preferences,
                              day_names=day_names,
                              subject_priorities=subject_priorities,
                              study_blocks=study_blocks,
                              scheduled_sessions=scheduled_sessions)
    else:
        # Original day view logic
        lessons = pronote_client.get_lessons(date)

        # Dictionary to store subject colors
        subject_colors = {}
        colors = ['#4361ee', '#3a0ca3', '#4895ef', '#4cc9f0', '#f72585', '#7209b7', '#560bad', '#480ca8', '#3f37c9', '#4361ee']
        color_index = 0

        # Convert lesson objects to dictionaries for template
        lessons_data = []
        for lesson in sorted(lessons, key=lambda x: x.start):
            # Assign a consistent color to each subject
            subject_name = lesson.subject.name
            if subject_name not in subject_colors:
                subject_colors[subject_name] = colors[color_index % len(colors)]
                color_index += 1

            lessons_data.append({
                'subject': subject_name,
                'start': lesson.start.strftime('%H:%M'),
                'end': lesson.end.strftime('%H:%M'),
                'room': lesson.classroom,
                'teacher': lesson.teacher_name,
                'color': subject_colors[subject_name]  # Add color
            })

        # Get username from session
        username = session.get('username', 'unknown_user')
        
        # Get calendar integration for study preferences
        calendar_integration = CalendarIntegration(username)
        study_preferences = calendar_integration.get_preferences()
        
        return render_template('timetable.html',
                              view_type=view_type,
                              lessons=lessons_data,
                              date=date.strftime('%Y-%m-%d'),
                              prev_date=(date - datetime.timedelta(days=1)).strftime('%Y-%m-%d'),
                              next_date=(date + datetime.timedelta(days=1)).strftime('%Y-%m-%d'),
                              today=datetime.date.today().strftime('%Y-%m-%d'),
                              study_preferences=study_preferences,
                              day_names=day_names,
                              subject_priorities=subject_priorities,
                              study_blocks=study_blocks,
                              scheduled_sessions=scheduled_sessions)

@app.route('/discussions')
def discussions():
    """Discussions route"""
    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('index'))

    # Check session
    pronote_client.check_session()

    # Get filter parameter
    show_only_unread = request.args.get('unread', 'false').lower() == 'true'

    # Get discussions
    discussions_list = pronote_client.get_discussions(only_unread=show_only_unread)

    # Convert discussion objects to dictionaries for template
    discussions_data = []

    # Always add the welcome message if not filtering for unread only
    if not show_only_unread:
        # Add the welcome message
        welcome_message = {
            'id': 'sample_1',
            'subject': 'Bienvenue sur Fireflies',
            'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
            'unread': True,  # Keep it unread to make it stand out
            'author': 'Équipe Fireflies',
            'participants': 'Vous, Équipe Fireflies'
        }
        discussions_data.append(welcome_message)

    # Process real discussions from the API
    if discussions_list:
        for i, discussion in enumerate(discussions_list):
            # Use obj_id if it exists, otherwise use the index as a fallback
            discussion_id = getattr(discussion, 'obj_id', None) or getattr(discussion, 'id', None) or f"discussion_{i}"

            # Handle participants - could be a method, a list, or not exist
            participants_str = ''
            if hasattr(discussion, 'participants'):
                participants = getattr(discussion, 'participants')
                # Check if it's a method
                if callable(participants):
                    try:
                        # Try to call the method to get participants
                        participants_list = participants()
                        if participants_list and isinstance(participants_list, list):
                            participants_str = ', '.join([getattr(p, 'name', 'Unknown') for p in participants_list])
                    except Exception as e:
                        print(f"Error getting participants: {e}")
                # Check if it's a list
                elif isinstance(participants, list):
                    participants_str = ', '.join([getattr(p, 'name', 'Unknown') for p in participants])

            discussions_data.append({
                'id': str(discussion_id),
                'subject': getattr(discussion, 'subject', 'No Subject'),
                'date': getattr(discussion, 'date', datetime.datetime.now()).strftime('%Y-%m-%d %H:%M'),
                'unread': getattr(discussion, 'unread', False),
                'author': getattr(discussion, 'author', 'Unknown'),
                'participants': participants_str
            })

    # Sort discussions by date (most recent first)
    discussions_data.sort(key=lambda x: x['date'], reverse=True)

    # Load settings
    settings = load_settings()

    return render_template('discussions.html',
                          discussions=discussions_data,
                          show_only_unread=show_only_unread,
                          settings=settings)

@app.route('/discussion/<discussion_id>')
def discussion(discussion_id):
    """View a specific discussion"""
    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('index'))

    # Check session
    pronote_client.check_session()

    # Get all discussions
    discussions_list = pronote_client.get_discussions()

    # Check if this is the welcome message
    if discussion_id == 'sample_1':
        # Handle the welcome message
        welcome_message = {
            'author': 'Équipe Fireflies',
            'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
            'content': """
            <p>Bonjour et bienvenue sur Fireflies !</p>
            <p>Nous sommes ravis de vous accueillir sur notre application qui vous permet de consulter facilement vos informations Pronote.</p>
            <p>Avec Fireflies, vous pouvez :</p>
            <ul>
                <li>Consulter vos notes et moyennes</li>
                <li>Voir votre emploi du temps</li>
                <li>Gérer vos devoirs</li>
                <li>Communiquer avec vos professeurs et camarades</li>
            </ul>
            <p>N'hésitez pas à explorer toutes les fonctionnalités !</p>
            <p>L'équipe Fireflies</p>
            """,
            'attachments': []
        }

        # Initialize messages list with the welcome message
        messages = [welcome_message]

        # Load any stored replies
        welcome_replies_file = Path('data/welcome_replies.json')
        os.makedirs(welcome_replies_file.parent, exist_ok=True)
        if welcome_replies_file.exists():
            try:
                with open(welcome_replies_file, 'r') as f:
                    welcome_data = json.load(f)

                # Add stored replies to messages
                for reply in welcome_data.get('replies', []):
                    messages.append(reply)
            except Exception as e:
                print(f"Error loading welcome replies: {e}")

        # Create the discussion data
        discussion_data = {
            'id': 'sample_1',
            'subject': 'Bienvenue sur Fireflies',
            'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M'),
            'unread': False,  # Mark as read when viewed
            'author': 'Équipe Fireflies',
            'participants': ['Vous', 'Équipe Fireflies'],
            'messages': messages
        }

        # Create a mock discussion object with the necessary attributes
        class MockDiscussion:
            def __init__(self):
                self.unread = False

            def mark_as_read(self):
                self.unread = False

        target_discussion = MockDiscussion()
    else:
        # Find the specific discussion in the real discussions list
        target_discussion = None
        for i, discussion in enumerate(discussions_list):
            # Get the discussion ID using various possible attribute names
            current_id = getattr(discussion, 'obj_id', None) or getattr(discussion, 'id', None) or f"discussion_{i}"

            if str(current_id) == discussion_id:
                target_discussion = discussion
                # Handle participants - could be a method, a list, or not exist
                participants_list = []
                if hasattr(discussion, 'participants'):
                    participants = getattr(discussion, 'participants')
                    # Check if it's a method
                    if callable(participants):
                        try:
                            # Try to call the method to get participants
                            p_list = participants()
                            if p_list and isinstance(p_list, list):
                                participants_list = [getattr(p, 'name', 'Unknown') for p in p_list]
                        except Exception as e:
                            print(f"Error getting participants: {e}")
                    # Check if it's a list
                    elif isinstance(participants, list):
                        participants_list = [getattr(p, 'name', 'Unknown') for p in participants]

                # Convert discussion to dictionary
                discussion_data = {
                    'id': str(current_id),
                    'subject': getattr(discussion, 'subject', 'No Subject'),
                    'date': getattr(discussion, 'date', datetime.datetime.now()).strftime('%Y-%m-%d %H:%M'),
                    'unread': getattr(discussion, 'unread', False),
                    'author': getattr(discussion, 'author', 'Unknown'),
                    'participants': participants_list,
                    'messages': []
                }

                # Add messages
                if hasattr(discussion, 'messages'):
                    messages = getattr(discussion, 'messages')
                    # Check if it's a method
                    if callable(messages):
                        try:
                            # Try to call the method to get messages
                            messages_list = messages()
                            if messages_list and isinstance(messages_list, list):
                                for message in messages_list:
                                    # Handle attachments
                                    attachments_list = []
                                    if hasattr(message, 'attachments'):
                                        attachments = getattr(message, 'attachments')
                                        if callable(attachments):
                                            try:
                                                att_list = attachments()
                                                if att_list and isinstance(att_list, list):
                                                    attachments_list = [{
                                                        'name': getattr(attachment, 'name', 'Attachment'),
                                                        'url': getattr(attachment, 'url', '#')
                                                    } for attachment in att_list]
                                            except Exception as e:
                                                print(f"Error getting attachments: {e}")
                                        elif isinstance(attachments, list):
                                            attachments_list = [{
                                                'name': getattr(attachment, 'name', 'Attachment'),
                                                'url': getattr(attachment, 'url', '#')
                                            } for attachment in attachments]

                                    discussion_data['messages'].append({
                                        'author': getattr(message, 'author', 'Unknown'),
                                        'date': getattr(message, 'date', datetime.datetime.now()).strftime('%Y-%m-%d %H:%M'),
                                        'content': getattr(message, 'content', ''),
                                        'attachments': attachments_list
                                    })
                        except Exception as e:
                            print(f"Error getting messages: {e}")
                    # Check if it's a list
                    elif isinstance(messages, list):
                        for message in messages:
                            # Handle attachments
                            attachments_list = []
                            if hasattr(message, 'attachments'):
                                attachments = getattr(message, 'attachments')
                                if callable(attachments):
                                    try:
                                        att_list = attachments()
                                        if att_list and isinstance(att_list, list):
                                            attachments_list = [{
                                                'name': getattr(attachment, 'name', 'Attachment'),
                                                'url': getattr(attachment, 'url', '#')
                                            } for attachment in att_list]
                                    except Exception as e:
                                        print(f"Error getting attachments: {e}")
                                elif isinstance(attachments, list):
                                    attachments_list = [{
                                        'name': getattr(attachment, 'name', 'Attachment'),
                                        'url': getattr(attachment, 'url', '#')
                                    } for attachment in attachments]

                            discussion_data['messages'].append({
                                'author': getattr(message, 'author', 'Unknown'),
                                'date': getattr(message, 'date', datetime.datetime.now()).strftime('%Y-%m-%d %H:%M'),
                                'content': getattr(message, 'content', ''),
                                'attachments': attachments_list
                            })
                break

    if not discussion_data:
        flash('Discussion not found', 'error')
        return redirect(url_for('discussions'))

    # Mark as read if it was unread
    if target_discussion and hasattr(target_discussion, 'unread') and target_discussion.unread and hasattr(target_discussion, 'mark_as_read'):
        try:
            target_discussion.mark_as_read()
            discussion_data['unread'] = False
        except Exception as e:
            print(f"Error marking discussion as read: {e}")

    # Load settings
    settings = load_settings()

    return render_template('view_discussion.html',
                          discussion=discussion_data,
                          settings=settings)

@app.route('/reply_discussion/<discussion_id>', methods=['POST'])
def reply_discussion(discussion_id):
    """Reply to a discussion"""
    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('index'))

    # Check session
    pronote_client.check_session()

    # Get message content
    message = request.form.get('message', '').strip()

    if not message:
        flash('Message cannot be empty', 'error')
        return redirect(url_for('discussion', discussion_id=discussion_id))

    # Handle welcome message
    if discussion_id == 'sample_1':
        # Store the reply to the welcome message
        welcome_replies_file = Path('data/welcome_replies.json')
        os.makedirs(welcome_replies_file.parent, exist_ok=True)

        # Create the file if it doesn't exist
        if not welcome_replies_file.exists():
            with open(welcome_replies_file, 'w') as f:
                json.dump({"replies": []}, f)

        # Load existing replies
        try:
            with open(welcome_replies_file, 'r') as f:
                welcome_data = json.load(f)
        except Exception as e:
            print(f"Error loading welcome replies: {e}")
            welcome_data = {"replies": []}

        # Add the new reply
        username = session.get('username', 'unknown_user')
        current_time = datetime.datetime.now()
        welcome_data["replies"].append({
            "author": username,
            "date": current_time.strftime('%Y-%m-%d %H:%M'),
            "content": message,
            "attachments": []
        })

        # Save the message for the admin
        save_message_for_admin(username, current_time, message)
        print(f"Message from {username} saved for admin review")

        # If this is the first reply, add an automatic response from Fireflies
        if len(welcome_data["replies"]) == 1:
            # Add a response after a short delay
            response_time = current_time + datetime.timedelta(minutes=2)
            welcome_data["replies"].append({
                "author": "Équipe Fireflies",
                "date": response_time.strftime('%Y-%m-%d %H:%M'),
                "content": f"""
                <p>Merci pour votre message, {username} !</p>
                <p>Nous sommes heureux de voir que vous utilisez notre application. N'hésitez pas à nous faire part de vos commentaires ou questions.</p>
                <p>L'équipe Fireflies est là pour vous aider à tirer le meilleur parti de votre expérience Pronote.</p>
                <p>Bonne navigation !</p>
                """,
                "attachments": []
            })

        # Save the updated replies
        try:
            with open(welcome_replies_file, 'w') as f:
                json.dump(welcome_data, f, indent=4)
        except Exception as e:
            print(f"Error saving welcome replies: {e}")

        # Track message sent for gamification
        gamification_system = GamificationSystem(username)
        gamification_result = gamification_system.track_message_sent()

        flash('Reply sent successfully. ' + gamification_result['message'], 'success')
        return redirect(url_for('discussion', discussion_id=discussion_id))

    # For real discussions, proceed with the normal flow
    # Get all discussions
    discussions_list = pronote_client.get_discussions()

    # Find the specific discussion
    target_discussion = None
    for i, discussion in enumerate(discussions_list):
        # Get the discussion ID using various possible attribute names
        current_id = getattr(discussion, 'obj_id', None) or getattr(discussion, 'id', None) or f"discussion_{i}"

        if str(current_id) == discussion_id:
            target_discussion = discussion
            break

    if not target_discussion:
        flash('Discussion not found', 'error')
        return redirect(url_for('discussions'))

    # Send reply
    try:
        if hasattr(target_discussion, 'reply'):
            reply_method = getattr(target_discussion, 'reply')
            if callable(reply_method):
                reply_method(message)

                # Track message sent for gamification
                username = session.get('username', 'unknown_user')
                gamification_system = GamificationSystem(username)
                gamification_result = gamification_system.track_message_sent()

                flash('Reply sent successfully. ' + gamification_result['message'], 'success')
            else:
                flash('Reply method is not callable', 'error')
        else:
            flash('This discussion does not support replies', 'error')
    except Exception as e:
        print(f"Error replying to discussion: {e}")
        flash(f'Error sending reply: {str(e)}', 'error')

    return redirect(url_for('discussion', discussion_id=discussion_id))

@app.route('/new_discussion', methods=['GET', 'POST'])
def new_discussion():
    """Create a new discussion"""
    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('index'))

    # Check session
    pronote_client.check_session()

    if request.method == 'POST':
        # Get form data
        subject = request.form.get('subject', '').strip()
        message = request.form.get('message', '').strip()
        recipient_ids = request.form.getlist('recipients')

        if not subject or not message or not recipient_ids:
            flash('Please fill in all fields and select at least one recipient', 'error')
            return redirect(url_for('new_discussion'))

        # Get all available recipients
        all_recipients = pronote_client.get_recipients()

        # Check if we're using sample recipients
        if not all_recipients:
            # For sample recipients, just show a success message
            # In a real app, we would store the new discussion

            # Track message sent for gamification
            username = session.get('username', 'unknown_user')
            gamification_system = GamificationSystem(username)
            gamification_result = gamification_system.track_message_sent()

            flash('Discussion sent successfully. ' + gamification_result['message'], 'success')
            return redirect(url_for('discussions'))

        # For real recipients, proceed with the normal flow
        # Filter selected recipients
        selected_recipients = [r for r in all_recipients if str(r.id) in recipient_ids]

        if not selected_recipients:
            flash('No valid recipients selected', 'error')
            return redirect(url_for('new_discussion'))

        # Send the discussion
        success = pronote_client.send_discussion(subject, message, selected_recipients)

        if success:
            # Track message sent for gamification
            username = session.get('username', 'unknown_user')
            gamification_system = GamificationSystem(username)
            gamification_result = gamification_system.track_message_sent()

            flash('Discussion sent successfully. ' + gamification_result['message'], 'success')
            return redirect(url_for('discussions'))
        else:
            flash('Failed to send discussion', 'error')
            return redirect(url_for('new_discussion'))

    # GET request - show the form
    # Get all available recipients
    recipients = pronote_client.get_recipients()

    # Convert recipient objects to dictionaries for template
    recipients_data = []

    # If no recipients are returned from the API, add some sample recipients
    if not recipients:
        # Sample recipients
        sample_recipients = [
            {
                'id': 'teacher_1',
                'name': 'Prof. Martin',
                'type': 'Enseignant'
            },
            {
                'id': 'teacher_2',
                'name': 'Prof. Dubois',
                'type': 'Enseignant'
            },
            {
                'id': 'teacher_3',
                'name': 'Prof. Bernard',
                'type': 'Enseignant'
            },
            {
                'id': 'admin_1',
                'name': 'Mme. Moreau',
                'type': 'Administration'
            },
            {
                'id': 'class_1',
                'name': 'Classe de Mathématiques',
                'type': 'Groupe'
            },
            {
                'id': 'class_2',
                'name': 'Classe de Français',
                'type': 'Groupe'
            }
        ]
        recipients_data.extend(sample_recipients)
    else:
        # Process real recipients from the API
        for recipient in recipients:
            recipients_data.append({
                'id': str(recipient.id),
                'name': recipient.name,
                'type': recipient.type if hasattr(recipient, 'type') else 'Unknown'
            })

    # Sort recipients by name
    recipients_data.sort(key=lambda x: x['name'])

    # Load settings
    settings = load_settings()

    return render_template('new_discussion.html',
                          recipients=recipients_data,
                          settings=settings)

# Gamification routes
@app.route('/gamification')
def gamification():
    """Gamification dashboard route"""
    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('index'))

    # Get username from session
    username = session.get('username', 'unknown_user')

    # Initialize gamification system
    gamification_system = GamificationSystem(username)
    
    # Initialize study analytics
    study_analytics = StudyAnalytics(username)

    # Get user stats
    stats = gamification_system.get_stats()

    # Get achievements
    achievements = gamification_system.get_achievements()

    # Get activity history
    activity_history = gamification_system.get_activity_history()

    # Get leaderboard
    leaderboard = gamification_system.get_leaderboard()
    
    # Get study analytics data
    period = request.args.get('period', 'week')
    try:
        study_data = study_analytics.get_study_data(period)
    except Exception as e:
        print(f"Error getting study data: {e}")
        study_data = {
            "total_time": "0h 0m",
            "cards_reviewed": 0,
            "accuracy": 0,
            "streak": 0,
            "activity": {
                "labels": [],
                "study_time": [],
                "cards_reviewed": []
            },
            "subjects": {
                "labels": [],
                "mastery": []
            },
            "progress": {
                "labels": [],
                "accuracy": []
            },
            "heatmap": []
        }
    
    # Get flashcard set progress
    try:
        flashcard_sets = study_analytics.get_flashcard_set_progress() if hasattr(study_analytics, 'get_flashcard_set_progress') else []
    except Exception as e:
        print(f"Error getting flashcard set progress: {e}")
        flashcard_sets = []
    
    # Get difficult cards
    try:
        difficult_cards = study_analytics.get_difficult_cards() if hasattr(study_analytics, 'get_difficult_cards') else []
    except Exception as e:
        print(f"Error getting difficult cards: {e}")
        difficult_cards = []
    
    # Get recommendations
    try:
        recommendations = study_analytics.get_study_recommendations() if hasattr(study_analytics, 'get_study_recommendations') else []
    except Exception as e:
        print(f"Error getting study recommendations: {e}")
        recommendations = []

    # Load settings
    settings = load_settings()

    return render_template('gamification.html',
                          stats=stats,
                          achievements=achievements,
                          activity_history=activity_history,
                          leaderboard=leaderboard,
                          study_data=study_data,
                          study_period=period,
                          flashcard_sets=flashcard_sets,
                          difficult_cards=difficult_cards,
                          recommendations=recommendations,
                          settings=settings)

@app.route('/gamification/achievements')
def achievements():
    """Achievements route"""
    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('index'))

    # Get username from session
    username = session.get('username', 'unknown_user')

    # Initialize gamification system
    gamification_system = GamificationSystem(username)

    # Get achievements
    achievements = gamification_system.get_achievements()

    # Load settings
    settings = load_settings()

    return render_template('achievements.html',
                          achievements=achievements,
                          settings=settings)

@app.route('/gamification/badges')
def badges():
    """Badges route"""
    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('index'))

    # Get username from session
    username = session.get('username', 'unknown_user')

    # Initialize gamification system
    gamification_system = GamificationSystem(username)

    # Get badges
    badges = gamification_system.get_badges() if hasattr(gamification_system, 'get_badges') else []

    # Load settings
    settings = load_settings()

    return render_template('badges.html',
                          badges=badges,
                          settings=settings)

@app.route('/gamification/leaderboard')
def leaderboard():
    """Leaderboard route"""
    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('index'))

    # Get username from session
    username = session.get('username', 'unknown_user')

    # Initialize gamification system
    gamification_system = GamificationSystem(username)

    # Get leaderboard
    leaderboard = gamification_system.get_leaderboard()

    # Load settings
    settings = load_settings()

    return render_template('leaderboard.html',
                          leaderboard=leaderboard,
                          current_user=username,
                          settings=settings)

@app.route('/flashcards')
def flashcards():
    """Flashcards and lessons route"""
    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('index'))

    # Check session
    pronote_client.check_session()

    # Get username from session
    username = session.get('username', 'unknown_user')

    # Initialize gamification system
    gamification_system = GamificationSystem(username)

    # Get subjects from grades to populate subject dropdown
    grades = pronote_client.get_grades()
    subjects = sorted(list(set(grade.subject.name for grade in grades if hasattr(grade, 'subject'))))

    # Get flashcard sets from data directory
    flashcard_dir = Path('data/flashcards')
    os.makedirs(flashcard_dir, exist_ok=True)

    # Load existing flashcard sets
    flashcard_sets = []
    for file in flashcard_dir.glob('*.json'):
        try:
            with open(file, 'r', encoding='utf-8') as f:
                flashcard_set = json.load(f)
                flashcard_sets.append({
                    'id': file.stem,
                    'name': flashcard_set.get('name', 'Unnamed Set'),
                    'subject': flashcard_set.get('subject', 'General'),
                    'card_count': len(flashcard_set.get('cards', [])),
                    'created_at': flashcard_set.get('created_at', 'Unknown date')
                })
        except Exception as e:
            print(f"Error loading flashcard set {file}: {e}")

    # Sort flashcard sets by name
    flashcard_sets.sort(key=lambda x: x['name'])

    # Load settings
    settings = load_settings()

    return render_template('flashcards.html',
                          subjects=subjects,
                          flashcard_sets=flashcard_sets,
                          settings=settings)

# API routes for gamification
@app.route('/api/gamification/track_homework', methods=['POST'])
def track_homework():
    """API route to track homework completion"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    # Get username from session
    username = session.get('username', 'unknown_user')

    # Initialize gamification system
    gamification_system = GamificationSystem(username)

    # Track homework completion
    result = gamification_system.track_homework_completion()

    return jsonify({'success': True, 'data': result}), 200

@app.route('/api/gamification/track_grade_view', methods=['POST'])
def track_grade_view():
    """API route to track grade view"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    # Get username from session
    username = session.get('username', 'unknown_user')

    # Initialize gamification system
    gamification_system = GamificationSystem(username)

    # Track grade view
    result = gamification_system.track_grade_view()

    return jsonify({'success': True, 'data': result}), 200

@app.route('/api/gamification/track_timetable_view', methods=['POST'])
def track_timetable_view():
    """API route to track timetable view"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    # Get username from session
    username = session.get('username', 'unknown_user')

    # Initialize gamification system
    gamification_system = GamificationSystem(username)

    # Track timetable view
    result = gamification_system.track_timetable_view()

    return jsonify({'success': True, 'data': result}), 200

@app.route('/api/gamification/track_message_sent', methods=['POST'])
def track_message_sent():
    """API route to track message sent"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    # Get username from session
    username = session.get('username', 'unknown_user')

    # Initialize gamification system
    gamification_system = GamificationSystem(username)

    # Track message sent
    result = gamification_system.track_message_sent()

    return jsonify({'success': True, 'data': result}), 200

@app.route('/api/gamification/track_flashcard_completion', methods=['POST'])
def track_flashcard_completion():
    """API route to track flashcard quiz completion"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    # Get username from session
    username = session.get('username', 'unknown_user')

    # Initialize gamification system
    gamification_system = GamificationSystem(username)

    # Track flashcard completion
    result = gamification_system.track_flashcard_completion()

    return jsonify({'success': True, 'data': result}), 200

@app.route('/api/gamification/study_plans', methods=['GET'])
def get_study_plans():
    """API route to get study plans"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    # Get username from session
    username = session.get('username', 'unknown_user')

    # Initialize gamification system
    gamification_system = GamificationSystem(username)

    # Get study plans
    study_plans = gamification_system.get_study_plans()

    return jsonify({'success': True, 'data': study_plans}), 200

@app.route('/api/gamification/study_plans', methods=['POST'])
def create_study_plan():
    """API route to create a study plan"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    # Get username from session
    username = session.get('username', 'unknown_user')

    # Get request data
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    test_name = data.get('test_name')
    test_date = data.get('test_date')
    subject = data.get('subject')
    num_exercises = data.get('num_exercises')

    if not all([test_name, test_date, subject, num_exercises]):
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    try:
        num_exercises = int(num_exercises)
    except ValueError:
        return jsonify({'success': False, 'message': 'Number of exercises must be a number'}), 400

    # Initialize gamification system
    gamification_system = GamificationSystem(username)

    # Create study plan
    study_plan = gamification_system.create_study_plan(test_name, test_date, subject, num_exercises)

    return jsonify({'success': True, 'data': study_plan}), 201

@app.route('/api/gamification/study_plans/<plan_id>/track', methods=['POST'])
def track_exercise_completion(plan_id):
    """API route to track exercise completion"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    # Get username from session
    username = session.get('username', 'unknown_user')

    # Initialize gamification system
    gamification_system = GamificationSystem(username)

    # Track exercise completion
    result = gamification_system.track_exercise_completion(plan_id)

    if not result.get('success', False):
        return jsonify(result), 404

    return jsonify(result), 200

@app.route('/api/gamification/study_plans/<plan_id>', methods=['DELETE'])
def delete_study_plan(plan_id):
    """API route to delete a study plan"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    # Get username from session
    username = session.get('username', 'unknown_user')

    # Initialize gamification system
    gamification_system = GamificationSystem(username)

    # Delete study plan
    result = gamification_system.delete_study_plan(plan_id)

    if not result.get('success', False):
        return jsonify(result), 404

    return jsonify(result), 200

# Flashcard API routes
@app.route('/api/flashcards', methods=['POST'])
def create_flashcard_set():
    """API route to create a new flashcard set"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    # Get request data
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    name = data.get('name')
    subject = data.get('subject')
    description = data.get('description', '')

    if not name or not subject:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400

    # Create a unique ID for the set
    set_id = f"{subject.lower().replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Create the flashcard set
    flashcard_set = {
        'id': set_id,
        'name': name,
        'subject': subject,
        'description': description,
        'created_at': datetime.datetime.now().isoformat(),
        'created_by': session.get('username', 'unknown_user'),
        'cards': []
    }

    # Save the flashcard set
    flashcard_dir = Path('data/flashcards')
    os.makedirs(flashcard_dir, exist_ok=True)

    with open(flashcard_dir / f"{set_id}.json", 'w', encoding='utf-8') as f:
        json.dump(flashcard_set, f, indent=2, ensure_ascii=False)

    return jsonify({
        'success': True,
        'message': 'Flashcard set created successfully',
        'data': {'id': set_id}
    }), 201

@app.route('/api/flashcards/<set_id>', methods=['GET'])
def get_flashcard_set(set_id):
    """API route to get a flashcard set"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    # Load the flashcard set
    flashcard_dir = Path('data/flashcards')
    file_path = flashcard_dir / f"{set_id}.json"

    if not file_path.exists():
        return jsonify({'success': False, 'message': 'Flashcard set not found'}), 404

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            flashcard_set = json.load(f)
            return jsonify({'success': True, 'data': flashcard_set}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error loading flashcard set: {str(e)}'}), 500

@app.route('/api/flashcards/<set_id>', methods=['PUT'])
def update_flashcard_set(set_id):
    """API route to update a flashcard set"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    # Get request data
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400

    # Load the existing flashcard set
    flashcard_dir = Path('data/flashcards')
    file_path = flashcard_dir / f"{set_id}.json"

    if not file_path.exists():
        return jsonify({'success': False, 'message': 'Flashcard set not found'}), 404

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            flashcard_set = json.load(f)

        # Update fields
        if 'name' in data:
            flashcard_set['name'] = data['name']
        if 'subject' in data:
            flashcard_set['subject'] = data['subject']
        if 'description' in data:
            flashcard_set['description'] = data['description']
        if 'cards' in data:
            flashcard_set['cards'] = data['cards']

        # Add last modified timestamp
        flashcard_set['last_modified'] = datetime.datetime.now().isoformat()

        # Save the updated flashcard set
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(flashcard_set, f, indent=2, ensure_ascii=False)

        return jsonify({'success': True, 'message': 'Flashcard set updated successfully'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error updating flashcard set: {str(e)}'}), 500

@app.route('/api/flashcards/<set_id>', methods=['DELETE'])
def delete_flashcard_set(set_id):
    """API route to delete a flashcard set"""
    if not session.get('logged_in'):
        return jsonify({'success': False, 'message': 'Not logged in'}), 401

    # Load the flashcard set
    flashcard_dir = Path('data/flashcards')
    file_path = flashcard_dir / f"{set_id}.json"

    if not file_path.exists():
        return jsonify({'success': False, 'message': 'Flashcard set not found'}), 404

    try:
        # Delete the file
        os.remove(file_path)
        return jsonify({'success': True, 'message': 'Flashcard set deleted successfully'}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error deleting flashcard set: {str(e)}'}), 500

@app.route('/flashcards/edit/<set_id>')
def edit_flashcards(set_id):
    """Route to edit a flashcard set"""
    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('index'))

    # Check session
    pronote_client.check_session()

    # Load the flashcard set
    flashcard_dir = Path('data/flashcards')
    file_path = flashcard_dir / f"{set_id}.json"

    if not file_path.exists():
        flash('Flashcard set not found', 'error')
        return redirect(url_for('flashcards'))

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            flashcard_set = json.load(f)

        # Get subjects from grades to populate subject dropdown
        grades = pronote_client.get_grades()
        subjects = sorted(list(set(grade.subject.name for grade in grades if hasattr(grade, 'subject'))))

        # Load settings
        settings = load_settings()

        return render_template('edit_flashcards.html',
                              flashcard_set=flashcard_set,
                              subjects=subjects,
                              settings=settings)
    except Exception as e:
        flash(f'Error loading flashcard set: {str(e)}', 'error')
        return redirect(url_for('flashcards'))

@app.route('/flashcards/quiz/<set_id>')
def flashcard_quiz(set_id):
    """Route to take a flashcard quiz"""
    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('index'))

    # Check session
    pronote_client.check_session()

    # Load the flashcard set
    flashcard_dir = Path('data/flashcards')
    file_path = flashcard_dir / f"{set_id}.json"

    if not file_path.exists():
        flash('Flashcard set not found', 'error')
        return redirect(url_for('flashcards'))

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            flashcard_set = json.load(f)

        # Load settings
        settings = load_settings()

        return render_template('flashcard_quiz.html',
                              flashcard_set=flashcard_set,
                              settings=settings)
    except Exception as e:
        flash(f'Error loading flashcard set: {str(e)}', 'error')
        return redirect(url_for('flashcards'))

# Route to view admin messages
@app.route('/admin/messages')
def admin_messages():
    """View messages sent to the admin"""
    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return redirect(url_for('index'))

    # Check if the user is an admin (you can implement proper admin checks)
    username = session.get('username', '')
    if username != 'admin':  # Simple check - replace with proper admin validation
        flash('You do not have permission to access this page', 'error')
        return redirect(url_for('dashboard'))

    # Get all message files
    admin_dir = Path('data/admin_messages')
    if not admin_dir.exists():
        os.makedirs(admin_dir, exist_ok=True)

    message_files = sorted(admin_dir.glob('*.txt'), reverse=True)
    messages = []

    for file in message_files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()

            # Extract metadata from filename
            filename = file.name
            timestamp_str = filename.split('_')[0:2]
            timestamp = '_'.join(timestamp_str)
            username = filename.split('_')[2].replace('.txt', '')

            messages.append({
                'id': file.name,
                'timestamp': timestamp,
                'username': username,
                'content': content
            })
        except Exception as e:
            print(f"Error reading message file {file}: {e}")

    # Load settings
    settings = load_settings()

    return render_template('admin_messages.html',
                          messages=messages,
                          settings=settings)

# Note: Accessibility routes are already defined in routes.py

# Context processor to provide current year for footer
@app.context_processor
def inject_now():
    return {'now': datetime.datetime.now()}

if __name__ == '__main__':
    app.run(host= '0.0.0.0', port=5000)