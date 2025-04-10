"""
Routes for the new features in Fireflies 1.22
"""

from flask import Blueprint, render_template, session, redirect, url_for, flash, request, jsonify, Response
import datetime
import json
import os
from pathlib import Path
from typing import Dict, List, Any, Optional

from gamification import GamificationSystem
from study_analytics import StudyAnalytics
from flashcard_system import FlashcardManager
from calendar_integration import CalendarIntegration

# Create blueprint
fireflies_routes = Blueprint('fireflies_routes', __name__)

# Helper function to check login
def check_login():
    if not session.get('logged_in'):
        flash('Please login first', 'error')
        return False
    return True

# Helper function to load settings
def load_settings():
    settings_file = Path('data/settings.json')
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading settings: {e}")
    return {'language': 'english', 'theme': 'blue'}

# Flashcard routes
@fireflies_routes.route('/flashcards')
def flashcards():
    """Flashcards main page"""
    if not check_login():
        return redirect(url_for('index'))
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize flashcard manager
    flashcard_manager = FlashcardManager(username)
    
    # Get all flashcard sets
    flashcard_sets = flashcard_manager.get_all_sets()
    
    # Initialize study analytics
    study_analytics = StudyAnalytics(username)
    
    # Get set progress data
    set_progress = study_analytics.get_flashcard_set_progress()
    
    # Load settings
    settings = load_settings()
    
    # Get available subjects
    subjects = flashcard_manager.get_subjects()
    
    return render_template('flashcards.html',
                          flashcard_sets=set_progress,
                          subjects=subjects,
                          settings=settings)

@fireflies_routes.route('/flashcard_set/<set_id>')
def flashcard_set(set_id):
    """View a specific flashcard set"""
    if not check_login():
        return redirect(url_for('index'))
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize flashcard manager
    flashcard_manager = FlashcardManager(username)
    
    # Get the flashcard set
    flashcard_set = flashcard_manager.get_set(set_id)
    
    if not flashcard_set:
        flash('Flashcard set not found', 'error')
        return redirect(url_for('fireflies_routes.flashcards'))
    
    # Load settings
    settings = load_settings()
    
    return render_template('flashcard_set.html',
                          flashcard_set=flashcard_set,
                          settings=settings)

@fireflies_routes.route('/flashcard_quiz/<set_id>')
def flashcard_quiz(set_id):
    """Quiz mode for a flashcard set"""
    if not check_login():
        return redirect(url_for('index'))
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize flashcard manager
    flashcard_manager = FlashcardManager(username)
    
    # Get the flashcard set
    flashcard_set = flashcard_manager.get_set(set_id)
    
    if not flashcard_set:
        flash('Flashcard set not found', 'error')
        return redirect(url_for('fireflies_routes.flashcards'))
    
    # Get quiz mode
    mode = request.args.get('mode', 'all')
    
    # Get specific card if provided
    card_id = request.args.get('card')
    
    # Get cards based on mode
    if mode == 'due':
        cards = flashcard_manager.get_due_cards(set_id)
    elif mode == 'new':
        cards = flashcard_manager.get_new_cards(set_id)
    elif card_id:
        # Get specific card
        cards = [card for card in flashcard_set.get('cards', []) if card.get('id') == card_id]
    else:
        # All cards
        cards = flashcard_set.get('cards', [])
    
    # Load settings
    settings = load_settings()
    
    return render_template('flashcard_quiz.html',
                          flashcard_set=flashcard_set,
                          cards=cards,
                          mode=mode,
                          settings=settings)

@fireflies_routes.route('/edit_flashcards/<set_id>', methods=['GET', 'POST'])
def edit_flashcards(set_id):
    """Edit a flashcard set"""
    if not check_login():
        return redirect(url_for('index'))
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize flashcard manager
    flashcard_manager = FlashcardManager(username)
    
    # Handle form submission
    if request.method == 'POST':
        # Get form data
        name = request.form.get('name', '').strip()
        subject = request.form.get('subject', '').strip()
        description = request.form.get('description', '').strip()
        
        if not name or not subject:
            flash('Please provide a name and subject for the flashcard set', 'error')
            return redirect(url_for('fireflies_routes.edit_flashcards', set_id=set_id))
        
        # Create or update set
        if set_id == 'new':
            # Create new set
            set_data = flashcard_manager.create_set(name, subject, description)
            if set_data and 'id' in set_data:
                set_id = set_data['id']
                flash('Flashcard set created successfully', 'success')
            else:
                flash('Failed to create flashcard set', 'error')
                return redirect(url_for('fireflies_routes.flashcards'))
        else:
            # Update existing set
            update_data = {'name': name, 'subject': subject, 'description': description}
            updated_set = flashcard_manager.update_set(set_id, update_data)
            if not updated_set:
                flash('Flashcard set not found', 'error')
                return redirect(url_for('fireflies_routes.flashcards'))
            flash('Flashcard set updated successfully', 'success')
        
        return redirect(url_for('fireflies_routes.edit_flashcards', set_id=set_id))
    
    # GET request - show the form
    if set_id == 'new':
        # New set
        flashcard_set = {
            'id': 'new',
            'name': '',
            'subject': '',
            'description': '',
            'cards': []
        }
    else:
        # Existing set
        flashcard_set = flashcard_manager.get_set(set_id)
        
        if not flashcard_set:
            flash('Flashcard set not found', 'error')
            return redirect(url_for('fireflies_routes.flashcards'))
    
    # Load settings
    settings = load_settings()
    
    # Get available subjects
    subjects = flashcard_manager.get_subjects()
    
    return render_template('edit_flashcards.html',
                          flashcard_set=flashcard_set,
                          subjects=subjects,
                          settings=settings)

@fireflies_routes.route('/create_flashcard/<set_id>', methods=['POST'])
def create_flashcard(set_id):
    """Create a new flashcard"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize flashcard manager
    flashcard_manager = FlashcardManager(username)
    
    # Get form data
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    question = data.get('question', '').strip()
    answer = data.get('answer', '').strip()
    tags = data.get('tags', [])
    image_url = data.get('image_url', '')
    audio_url = data.get('audio_url', '')
    
    if not question or not answer:
        return jsonify({'success': False, 'message': 'Question and answer are required'}), 400
    
    # Create flashcard
    card_id = flashcard_manager.add_card(set_id, question, answer, tags, image_url, audio_url)
    
    if not card_id:
        return jsonify({'success': False, 'message': 'Failed to create flashcard'}), 500
    
    return jsonify({'success': True, 'card_id': card_id}), 201

@fireflies_routes.route('/update_flashcard/<set_id>/<card_id>', methods=['POST'])
def update_flashcard(set_id, card_id):
    """Update a flashcard"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize flashcard manager
    flashcard_manager = FlashcardManager(username)
    
    # Get form data
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    question = data.get('question', '').strip()
    answer = data.get('answer', '').strip()
    tags = data.get('tags', [])
    image_url = data.get('image_url', '')
    audio_url = data.get('audio_url', '')
    
    if not question or not answer:
        return jsonify({'success': False, 'message': 'Question and answer are required'}), 400
    
    # Update flashcard
    success = flashcard_manager.update_card(set_id, card_id, question, answer, tags, image_url, audio_url)
    
    if not success:
        return jsonify({'success': False, 'message': 'Failed to update flashcard'}), 500
    
    return jsonify({'success': True}), 200

@fireflies_routes.route('/delete_flashcard/<set_id>/<card_id>', methods=['POST'])
def delete_flashcard(set_id, card_id):
    """Delete a flashcard"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize flashcard manager
    flashcard_manager = FlashcardManager(username)
    
    # Delete flashcard
    success = flashcard_manager.delete_card(set_id, card_id)
    
    if not success:
        return jsonify({'success': False, 'message': 'Failed to delete flashcard'}), 500
    
    return jsonify({'success': True}), 200

@fireflies_routes.route('/delete_flashcard_set/<set_id>', methods=['POST'])
def delete_flashcard_set(set_id):
    """Delete a flashcard set"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize flashcard manager
    flashcard_manager = FlashcardManager(username)
    
    # Delete flashcard set
    success = flashcard_manager.delete_set(set_id)
    
    if not success:
        return jsonify({'success': False, 'message': 'Failed to delete flashcard set'}), 500
    
    return jsonify({'success': True}), 200

@fireflies_routes.route('/api/flashcards', methods=['POST'])
def create_flashcard_set():
    """Create a new flashcard set via API"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize flashcard manager
    flashcard_manager = FlashcardManager(username)
    
    # Get JSON data
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    # Get required fields
    name = data.get('name', '').strip()
    subject = data.get('subject', '').strip()
    description = data.get('description', '').strip()
    
    # Validate required fields
    if not name:
        return jsonify({'success': False, 'message': 'Name is required'}), 400
    
    if not subject:
        return jsonify({'success': False, 'message': 'Subject is required'}), 400
    
    # Create the set
    set_data = flashcard_manager.create_set(name, subject, description)
    
    if not set_data:
        return jsonify({'success': False, 'message': 'Failed to create flashcard set'}), 500
    
    return jsonify({'success': True, 'data': set_data}), 201

@fireflies_routes.route('/api/flashcards/<set_id>', methods=['PUT'])
def update_flashcard_set(set_id):
    """Update a flashcard set via API"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize flashcard manager
    flashcard_manager = FlashcardManager(username)
    
    # Get JSON data
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    # Check if we're updating set details
    if 'name' in data or 'subject' in data or 'description' in data:
        update_data = {}
        
        if 'name' in data:
            update_data['name'] = data['name'].strip()
        
        if 'subject' in data:
            update_data['subject'] = data['subject'].strip()
        
        if 'description' in data:
            update_data['description'] = data['description'].strip()
        
        # Check if the set exists
        existing_set = flashcard_manager.get_set(set_id)
        if not existing_set:
            return jsonify({'success': False, 'message': 'Flashcard set not found'}), 404
            
        # Update the set
        updated_set = flashcard_manager.update_set(set_id, update_data)
        
        if not updated_set:
            return jsonify({'success': False, 'message': 'Failed to update flashcard set'}), 500
    
    # Check if we're updating cards
    if 'cards' in data:
        cards = data['cards']
        
        # Get the current set
        current_set = flashcard_manager.get_set(set_id)
        
        if not current_set:
            return jsonify({'success': False, 'message': 'Flashcard set not found'}), 404
        
        # Replace all cards
        current_set['cards'] = []
        
        # Add each card
        for card_data in cards:
            if 'question' in card_data and 'answer' in card_data:
                # Create the card
                card = {
                    "id": card_data.get('id') or f"card_{len(current_set['cards'])}_" + str(int(datetime.datetime.now().timestamp())),
                    "question": card_data["question"],
                    "answer": card_data["answer"],
                    "created_at": datetime.datetime.now().isoformat(),
                    "image_url": card_data.get("image_url"),
                    "audio_url": card_data.get("audio_url"),
                    "tags": card_data.get("tags", []),
                    "learning_data": {
                        "ease_factor": 2.5,
                        "interval": 0,
                        "reviews": 0,
                        "last_review": None,
                        "next_review": datetime.datetime.now().isoformat(),
                        "history": []
                    }
                }
                
                current_set["cards"].append(card)
        
        # Update the set
        updated_set = flashcard_manager.update_set(set_id, current_set)
        
        if not updated_set:
            return jsonify({'success': False, 'message': 'Failed to update flashcard cards'}), 500
    
    return jsonify({'success': True}), 200
    
@fireflies_routes.route('/api/flashcards/<set_id>', methods=['DELETE'])
def delete_flashcard_set_api(set_id):
    """Delete a flashcard set via API"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize flashcard manager
    flashcard_manager = FlashcardManager(username)
    
    # Delete flashcard set
    success = flashcard_manager.delete_set(set_id)
    
    if not success:
        return jsonify({'success': False, 'message': 'Failed to delete flashcard set'}), 500
    
    return jsonify({'success': True}), 200

@fireflies_routes.route('/api/flashcards/rate_card', methods=['POST'])
def rate_card():
    """Rate a flashcard during quiz"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize flashcard manager
    flashcard_manager = FlashcardManager(username)
    
    # Get form data
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    set_id = data.get('set_id')
    card_id = data.get('card_id')
    rating = data.get('rating')  # 0=failed, 1=hard, 2=good, 3=easy
    
    if not set_id or not card_id or rating is None:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    # Rate card
    result = flashcard_manager.rate_card(set_id, card_id, rating)
    
    if not result.get('success', False):
        return jsonify({'success': False, 'message': result.get('message', 'Failed to rate card')}), 500
    
    return jsonify(result), 200

@fireflies_routes.route('/api/flashcards/complete_session', methods=['POST'])
def complete_flashcard_session():
    """Complete a flashcard study session"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize flashcard manager and gamification system
    flashcard_manager = FlashcardManager(username)
    gamification_system = GamificationSystem(username)
    study_analytics = StudyAnalytics(username)
    
    # Get form data
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    set_id = data.get('set_id')
    stats = data.get('stats', {})
    duration = data.get('duration', 0)  # Duration in seconds
    
    if not set_id or not stats:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    # Record session in analytics
    study_analytics.record_flashcard_session(set_id, stats, duration)
    
    # Track completion for gamification
    gamification_result = gamification_system.track_flashcard_completion(set_id, stats)
    
    return jsonify({
        'success': True,
        'gamification': gamification_result
    }), 200

@fireflies_routes.route('/api/flashcards/import', methods=['POST'])
def import_flashcards():
    """Import flashcards from CSV or JSON"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize flashcard manager
    flashcard_manager = FlashcardManager(username)
    
    # Check if file was uploaded
    if 'file' not in request.files:
        return jsonify({'success': False, 'message': 'No file uploaded'}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'message': 'No file selected'}), 400
    
    # Get set ID if provided (for adding to existing set)
    set_id = request.form.get('set_id')
    
    # Get set details if creating new set
    set_name = request.form.get('set_name', '').strip()
    set_subject = request.form.get('set_subject', '').strip()
    set_description = request.form.get('set_description', '').strip()
    
    # Import flashcards
    result = flashcard_manager.import_cards(file, set_id, set_name, set_subject, set_description)
    
    if not result.get('success', False):
        return jsonify({'success': False, 'message': result.get('message', 'Import failed')}), 500
    
    return jsonify(result), 200

@fireflies_routes.route('/api/flashcards/export/<set_id>', methods=['GET'])
def export_flashcards(set_id):
    """Export flashcards to JSON"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize flashcard manager
    flashcard_manager = FlashcardManager(username)
    
    # Get the flashcard set
    flashcard_set = flashcard_manager.get_set(set_id)
    
    if not flashcard_set:
        return jsonify({'success': False, 'message': 'Flashcard set not found'}), 404
    
    # Export as JSON
    return jsonify(flashcard_set), 200

# Study Analytics routes
@fireflies_routes.route('/study_analytics')
def study_analytics():
    """Study analytics dashboard"""
    if not check_login():
        return redirect(url_for('index'))
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize study analytics
    study_analytics = StudyAnalytics(username)
    
    # Get period from query params (default to week)
    period = request.args.get('period', 'week')
    
    # Get study data
    study_data = study_analytics.get_study_data(period)
    
    # Get flashcard set progress
    flashcard_sets = study_analytics.get_flashcard_set_progress()
    
    # Get difficult cards
    difficult_cards = study_analytics.get_difficult_cards()
    
    # Get recommendations
    recommendations = study_analytics.get_study_recommendations()
    
    # Load settings
    settings = load_settings()
    
    return render_template('study_analytics.html',
                          study_stats=study_data,
                          study_data=study_data,
                          flashcard_sets=flashcard_sets,
                          difficult_cards=difficult_cards,
                          recommendations=recommendations,
                          settings=settings)

@fireflies_routes.route('/api/analytics/study-data')
def get_study_data():
    """API endpoint to get study data"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize study analytics
    study_analytics = StudyAnalytics(username)
    
    # Get period from query params (default to week)
    period = request.args.get('period', 'week')
    
    # Get study data
    study_data = study_analytics.get_study_data(period)
    
    return jsonify({'success': True, 'data': study_data}), 200

# Accessibility routes
@fireflies_routes.route('/accessibility')
def accessibility():
    """Accessibility settings page"""
    if not check_login():
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
    
    return render_template('dark_mode.html',
                          user_settings=user_settings,
                          settings=settings)

@fireflies_routes.route('/api/settings/accessibility', methods=['POST'])
def update_accessibility_settings():
    """API endpoint to update accessibility settings"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Get request data
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    setting = data.get('setting')
    value = data.get('value')
    
    if setting is None or value is None:
        return jsonify({'success': False, 'message': 'Missing required fields'}), 400
    
    # Load current settings
    settings_dir = Path('data/user_settings')
    os.makedirs(settings_dir, exist_ok=True)
    settings_file = settings_dir / f'{username}_accessibility.json'
    
    user_settings = {}
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                user_settings = json.load(f)
        except Exception as e:
            print(f"Error loading accessibility settings: {e}")
    
    # Update setting
    user_settings[setting] = value
    
    # Save settings
    try:
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(user_settings, f, indent=2)
    except Exception as e:
        print(f"Error saving accessibility settings: {e}")
        return jsonify({'success': False, 'message': f'Error saving settings: {e}'}), 500
    
    return jsonify({'success': True}), 200

@fireflies_routes.route('/api/settings/accessibility/get', methods=['GET'])
def get_accessibility_settings():
    """API endpoint to get accessibility settings"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Load settings
    settings_dir = Path('data/user_settings')
    settings_file = settings_dir / f'{username}_accessibility.json'
    
    user_settings = {}
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                user_settings = json.load(f)
        except Exception as e:
            print(f"Error loading accessibility settings: {e}")
            return jsonify({'success': False, 'message': f'Error loading settings: {e}'}), 500
    
    return jsonify({'success': True, 'settings': user_settings}), 200

@fireflies_routes.route('/api/study_analytics', methods=['GET'])
def get_study_analytics():
    """API endpoint to get study analytics data"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize study analytics
    study_analytics = StudyAnalytics(username)
    
    # Get period from query parameters
    period = request.args.get('period', 'week')
    if period not in ['week', 'month', 'year']:
        period = 'week'
    
    # Get study data
    study_data = study_analytics.get_study_data(period)
    
    # Get flashcard set progress
    flashcard_sets = []
    try:
        flashcard_sets = study_analytics.get_flashcard_set_progress()
    except Exception as e:
        print(f"Error getting flashcard set progress: {e}")
    
    # Get difficult cards
    difficult_cards = []
    try:
        difficult_cards = study_analytics.get_difficult_cards()
    except Exception as e:
        print(f"Error getting difficult cards: {e}")
    
    # Get recommendations
    recommendations = []
    try:
        recommendations = study_analytics.get_study_recommendations()
    except Exception as e:
        print(f"Error getting study recommendations: {e}")
    
    return jsonify({
        'success': True,
        'study_data': study_data,
        'flashcard_sets': flashcard_sets,
        'difficult_cards': difficult_cards,
        'recommendations': recommendations,
        'period': period
    }), 200

# Calendar and Task Management Routes
@fireflies_routes.route('/study_schedule')
def study_schedule():
    """Study schedule builder page"""
    if not check_login():
        return redirect(url_for('index'))
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize calendar integration
    calendar_integration = CalendarIntegration(username)
    
    # Get study blocks
    study_blocks = calendar_integration.get_study_blocks()
    
    # Get preferences
    preferences = calendar_integration.get_preferences()
    
    # Get scheduled sessions for the next 14 days
    today = datetime.datetime.now().date()
    end_date = today + datetime.timedelta(days=14)
    scheduled_sessions = calendar_integration.get_scheduled_sessions(today, end_date)
    
    # Get external calendars
    external_calendars = calendar_integration.get_external_calendars()
    
    # Get homework from Pronote for prioritization
    # This would typically come from the Pronote client
    # For now, we'll use a placeholder
    homework_list = []
    try:
        # Check if there's a Pronote client in the session
        if 'pronote_client' in session and session['pronote_client']:
            # Get the client from the session
            start_date = datetime.datetime.now().date()
            
            # Import the function to get homework
            from pronote_web_app import get_homework_for_user
            
            # Get homework using the function
            homework_data = get_homework_for_user(session.get('username', 'unknown_user'), start_date)
            
            # Use the returned homework data
            homework_list = homework_data if homework_data else []
    except Exception as e:
        print(f"Error getting homework: {e}")
    
    # Prioritize homework
    prioritized_homework = calendar_integration.prioritize_homework(homework_list)
    
    # Load settings
    settings = load_settings()
    
    # Get day names for display
    day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    
    return render_template('study_schedule.html',
                          study_blocks=study_blocks,
                          preferences=preferences,
                          scheduled_sessions=scheduled_sessions,
                          external_calendars=external_calendars,
                          prioritized_homework=prioritized_homework,
                          day_names=day_names,
                          settings=settings)

@fireflies_routes.route('/api/study_blocks', methods=['POST'])
def add_study_block():
    """API endpoint to add a study block"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize calendar integration
    calendar_integration = CalendarIntegration(username)
    
    # Get request data
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    # Get required fields
    day_of_week = data.get('day_of_week')
    start_time = data.get('start_time')
    end_time = data.get('end_time')
    
    # Validate required fields
    if day_of_week is None:
        return jsonify({'success': False, 'message': 'Day of week is required'}), 400
    
    if not start_time:
        return jsonify({'success': False, 'message': 'Start time is required'}), 400
    
    if not end_time:
        return jsonify({'success': False, 'message': 'End time is required'}), 400
    
    try:
        # Add study block
        study_block = calendar_integration.add_study_block(day_of_week, start_time, end_time)
        
        return jsonify({'success': True, 'study_block': study_block}), 200
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error adding study block: {e}'}), 500

@fireflies_routes.route('/api/study_blocks/<block_id>', methods=['DELETE'])
def remove_study_block(block_id):
    """API endpoint to remove a study block"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize calendar integration
    calendar_integration = CalendarIntegration(username)
    
    try:
        # Remove study block
        success = calendar_integration.remove_study_block(block_id)
        
        if not success:
            return jsonify({'success': False, 'message': 'Study block not found'}), 404
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error removing study block: {e}'}), 500

@fireflies_routes.route('/api/calendar/preferences', methods=['POST'])
def update_calendar_preferences():
    """API endpoint to update calendar preferences"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize calendar integration
    calendar_integration = CalendarIntegration(username)
    
    # Get request data
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    try:
        # Update preferences
        calendar_integration.update_preferences(data)
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error updating preferences: {e}'}), 500

@fireflies_routes.route('/api/study_schedule/build', methods=['POST'])
def build_study_schedule():
    """API endpoint to build a study schedule"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize calendar integration
    calendar_integration = CalendarIntegration(username)
    
    # Get request data
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    # Get parameters
    start_date_str = data.get('start_date')
    days_ahead = data.get('days_ahead', 7)
    
    # Validate parameters
    if not start_date_str:
        # Default to today
        start_date = datetime.datetime.now().date()
    else:
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid start date format'}), 400
    
    # Get homework from Pronote for prioritization
    homework_list = []
    try:
        # Get homework from Pronote client (if available in session)
        if 'pronote_client' in globals():
            homework_list = pronote_client.get_homework(start_date)
            
            # Convert to dictionary format
            homework_list = [
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
        print(f"Error getting homework: {e}")
    
    try:
        # Build study schedule
        schedule = calendar_integration.build_study_schedule(start_date, days_ahead, homework_list)
        
        return jsonify({'success': True, 'schedule': schedule}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error building study schedule: {e}'}), 500

@fireflies_routes.route('/api/calendar/export', methods=['GET'])
def export_calendar():
    """API endpoint to export calendar in iCal format"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize calendar integration
    calendar_integration = CalendarIntegration(username)
    
    # Get date range from query parameters
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')
    
    # Parse dates if provided
    start_date = None
    end_date = None
    
    if start_date_str:
        try:
            start_date = datetime.datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid start date format'}), 400
    
    if end_date_str:
        try:
            end_date = datetime.datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({'success': False, 'message': 'Invalid end date format'}), 400
    
    try:
        # Export to iCal
        ical_data = calendar_integration.export_to_ical(start_date, end_date)
        
        # Return as file download
        response = Response(ical_data, mimetype='text/calendar')
        response.headers['Content-Disposition'] = f'attachment; filename=fireflies_study_schedule_{username}.ics'
        return response
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error exporting calendar: {e}'}), 500

@fireflies_routes.route('/api/external_calendars', methods=['POST'])
def add_external_calendar():
    """API endpoint to add an external calendar"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize calendar integration
    calendar_integration = CalendarIntegration(username)
    
    # Get request data
    data = request.get_json()
    if not data:
        return jsonify({'success': False, 'message': 'No data provided'}), 400
    
    # Get required fields
    calendar_type = data.get('type')
    calendar_id = data.get('calendar_id')
    access_token = data.get('access_token')
    
    # Validate required fields
    if not calendar_type:
        return jsonify({'success': False, 'message': 'Calendar type is required'}), 400
    
    if not calendar_id:
        return jsonify({'success': False, 'message': 'Calendar ID is required'}), 400
    
    try:
        # Add external calendar
        calendar = calendar_integration.add_external_calendar(calendar_type, calendar_id, access_token)
        
        return jsonify({'success': True, 'calendar': calendar}), 200
    except ValueError as e:
        return jsonify({'success': False, 'message': str(e)}), 400
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error adding external calendar: {e}'}), 500

@fireflies_routes.route('/api/external_calendars/<calendar_id>', methods=['DELETE'])
def remove_external_calendar(calendar_id):
    """API endpoint to remove an external calendar"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize calendar integration
    calendar_integration = CalendarIntegration(username)
    
    try:
        # Remove external calendar
        success = calendar_integration.remove_external_calendar(calendar_id)
        
        if not success:
            return jsonify({'success': False, 'message': 'External calendar not found'}), 404
        
        return jsonify({'success': True}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error removing external calendar: {e}'}), 500

@fireflies_routes.route('/api/calendar/sync', methods=['POST'])
def sync_calendars():
    """API endpoint to sync with external calendars"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize calendar integration
    calendar_integration = CalendarIntegration(username)
    
    try:
        # Sync with external calendars
        results = calendar_integration.sync_with_external_calendars()
        
        return jsonify({'success': True, 'results': results}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error syncing calendars: {e}'}), 500

@fireflies_routes.route('/homework_priority')
def homework_priority():
    """Homework priority system page"""
    if not check_login():
        return redirect(url_for('index'))
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize calendar integration
    calendar_integration = CalendarIntegration(username)
    
    # Get homework from Pronote
    homework_list = []
    try:
        # Get homework from Pronote client (if available in session)
        if 'pronote_client' in globals():
            start_date = datetime.datetime.now().date()
            homework_list = pronote_client.get_homework(start_date)
            
            # Convert to dictionary format
            homework_list = [
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
        print(f"Error getting homework: {e}")
    
    # Prioritize homework
    prioritized_homework = calendar_integration.prioritize_homework(homework_list)
    
    # Group by priority level
    high_priority = [hw for hw in prioritized_homework if hw.get('priority_level') == 'high']
    medium_priority = [hw for hw in prioritized_homework if hw.get('priority_level') == 'medium']
    low_priority = [hw for hw in prioritized_homework if hw.get('priority_level') == 'low']
    
    # Load settings
    settings = load_settings()
    
    return render_template('homework_priority.html',
                          high_priority=high_priority,
                          medium_priority=medium_priority,
                          low_priority=low_priority,
                          settings=settings)

@fireflies_routes.route('/api/homework/update_time', methods=['POST'])
def update_homework_time():
    """API endpoint to update estimated completion time for homework"""
    if not check_login():
        return jsonify({'success': False, 'message': 'Not logged in'}), 401
    
    # Get username from session
    username = session.get('username', 'unknown_user')
    
    # Initialize calendar integration
    calendar_integration = CalendarIntegration(username)
    
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
        # Get homework from Pronote
        homework_list = []
        if 'pronote_client' in globals():
            start_date = datetime.datetime.now().date()
            homework_list = pronote_client.get_homework(start_date)
            
            # Convert to dictionary format
            homework_list = [
                {
                    'id': str(hw.id),
                    'subject': hw.subject.name,
                    'description': hw.description,
                    'date': hw.date.strftime('%Y-%m-%d'),
                    'done': hw.done,
                    'estimated_time': 60 if str(hw.id) != homework_id else estimated_time
                }
                for hw in homework_list
            ]
        
        # Prioritize homework
        prioritized_homework = calendar_integration.prioritize_homework(homework_list)
        
        return jsonify({'success': True, 'homework': prioritized_homework}), 200
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error updating homework time: {e}'}), 500

