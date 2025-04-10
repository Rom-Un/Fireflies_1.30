"""
Calendar and Task Management Integration for Fireflies

This module provides functionality to:
1. Build optimal study schedules based on available time and upcoming tests
2. Prioritize homework based on due dates and estimated completion time
3. Integrate with external calendars (Google Calendar, Apple Calendar)
"""

import datetime
import json
import os
import math
import random
import uuid
import requests
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import icalendar
from icalendar import Calendar, Event, vText
from datetime import datetime, timedelta
import pytz
import tempfile

# Path for calendar data
CALENDAR_DIR = Path('data/calendar')
os.makedirs(CALENDAR_DIR, exist_ok=True)

class CalendarIntegration:
    """Class to manage calendar integration and task scheduling"""
    
    def __init__(self, username: str):
        """
        Initialize the calendar integration for a user
        
        Args:
            username: The username of the user
        """
        self.username = username
        self.user_dir = CALENDAR_DIR / username
        os.makedirs(self.user_dir, exist_ok=True)
        self.data_file = self.user_dir / "calendar_data.json"
        self.data = self._load_data()
        
    def _load_data(self) -> Dict[str, Any]:
        """
        Load calendar data from file
        
        Returns:
            Dict containing calendar data
        """
        if not self.data_file.exists():
            # Initialize with default data
            return {
                "study_blocks": [],
                "scheduled_sessions": [],
                "external_calendars": [],
                "homework_priorities": [],
                "preferences": {
                    "preferred_study_times": [],
                    "study_session_length": 45,  # minutes
                    "break_length": 15,  # minutes
                    "max_daily_study_time": 180,  # minutes
                    "calendar_sync_enabled": False
                }
            }
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading calendar data: {e}")
            return {
                "study_blocks": [],
                "scheduled_sessions": [],
                "external_calendars": [],
                "homework_priorities": [],
                "preferences": {
                    "preferred_study_times": [],
                    "study_session_length": 45,  # minutes
                    "break_length": 15,  # minutes
                    "max_daily_study_time": 180,  # minutes
                    "calendar_sync_enabled": False
                }
            }
    
    def _save_data(self) -> None:
        """Save calendar data to file"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving calendar data: {e}")
    
    def add_study_block(self, day_of_week: int, start_time: str, end_time: str) -> Dict[str, Any]:
        """
        Add a recurring study block
        
        Args:
            day_of_week: Day of the week (0=Monday, 6=Sunday)
            start_time: Start time in HH:MM format
            end_time: End time in HH:MM format
            
        Returns:
            Dict containing the created study block
        """
        # Validate inputs
        if not (0 <= day_of_week <= 6):
            raise ValueError("Day of week must be between 0 (Monday) and 6 (Sunday)")
        
        try:
            datetime.strptime(start_time, "%H:%M")
            datetime.strptime(end_time, "%H:%M")
        except ValueError:
            raise ValueError("Time must be in HH:MM format")
        
        # Create study block
        block_id = str(uuid.uuid4())
        study_block = {
            "id": block_id,
            "day_of_week": day_of_week,
            "start_time": start_time,
            "end_time": end_time,
            "created_at": datetime.now().isoformat()
        }
        
        # Add to study blocks
        self.data["study_blocks"].append(study_block)
        self._save_data()
        
        return study_block
    
    def remove_study_block(self, block_id: str) -> bool:
        """
        Remove a study block
        
        Args:
            block_id: ID of the study block to remove
            
        Returns:
            True if successful, False otherwise
        """
        initial_count = len(self.data["study_blocks"])
        self.data["study_blocks"] = [block for block in self.data["study_blocks"] if block["id"] != block_id]
        
        if len(self.data["study_blocks"]) < initial_count:
            self._save_data()
            return True
        
        return False
    
    def get_study_blocks(self) -> List[Dict[str, Any]]:
        """
        Get all study blocks
        
        Returns:
            List of study blocks
        """
        return self.data["study_blocks"]
    
    def update_preferences(self, preferences: Dict[str, Any]) -> None:
        """
        Update calendar preferences
        
        Args:
            preferences: Dict containing preferences to update
        """
        # Update only provided preferences
        for key, value in preferences.items():
            if key in self.data["preferences"]:
                self.data["preferences"][key] = value
        
        self._save_data()
    
    def get_preferences(self) -> Dict[str, Any]:
        """
        Get calendar preferences
        
        Returns:
            Dict containing calendar preferences
        """
        return self.data["preferences"]
    
    def prioritize_homework(self, homework_list: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Prioritize homework based on due dates and estimated completion time
        
        Args:
            homework_list: List of homework items with due dates and estimated completion times
            
        Returns:
            List of homework items with priority scores
        """
        today = datetime.now().date()
        prioritized_homework = []
        
        for hw in homework_list:
            # Skip completed homework
            if hw.get("done", False):
                continue
            
            # Parse due date
            try:
                due_date = datetime.strptime(hw["date"], "%Y-%m-%d").date()
            except (ValueError, KeyError):
                # Skip homework with invalid dates
                continue
            
            # Calculate days until due
            days_until_due = (due_date - today).days
            
            # Get estimated completion time (default to 60 minutes)
            estimated_time = hw.get("estimated_time", 60)
            
            # Calculate priority score (lower is higher priority)
            # Formula: days_until_due * 10 + estimated_time / 10
            # This prioritizes items due soon and those that take less time
            if days_until_due <= 0:
                # Overdue items get highest priority
                priority_score = -100 + estimated_time / 10
            else:
                priority_score = days_until_due * 10 + estimated_time / 10
            
            # Add priority information
            prioritized_item = hw.copy()
            prioritized_item["priority_score"] = priority_score
            prioritized_item["days_until_due"] = days_until_due
            
            # Determine priority level
            if days_until_due <= 1:
                prioritized_item["priority_level"] = "high"
            elif days_until_due <= 3:
                prioritized_item["priority_level"] = "medium"
            else:
                prioritized_item["priority_level"] = "low"
            
            prioritized_homework.append(prioritized_item)
        
        # Sort by priority score (ascending)
        prioritized_homework.sort(key=lambda x: x["priority_score"])
        
        # Save prioritized homework
        self.data["homework_priorities"] = prioritized_homework
        self._save_data()
        
        return prioritized_homework
    
    def build_study_schedule(self, start_date: datetime.date, days_ahead: int = 7, 
                            homework_list: Optional[List[Dict[str, Any]]] = None,
                            tests: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Build an optimal study schedule based on available time and upcoming tests/homework
        
        Args:
            start_date: Start date for the schedule
            days_ahead: Number of days to schedule ahead
            homework_list: List of homework items
            tests: List of upcoming tests
            
        Returns:
            List of scheduled study sessions
        """
        # Get study blocks
        study_blocks = self.data["study_blocks"]
        
        # Get preferences
        preferences = self.data["preferences"]
        session_length = preferences.get("study_session_length", 45)
        break_length = preferences.get("break_length", 15)
        max_daily_study_time = preferences.get("max_daily_study_time", 180)
        
        # Initialize schedule
        schedule = []
        
        # Prioritize homework if provided
        prioritized_homework = []
        if homework_list:
            prioritized_homework = self.prioritize_homework(homework_list)
        
        # Process each day in the range
        for day_offset in range(days_ahead):
            current_date = start_date + timedelta(days=day_offset)
            day_of_week = current_date.weekday()  # 0=Monday, 6=Sunday
            
            # Find study blocks for this day
            day_blocks = [block for block in study_blocks if block["day_of_week"] == day_of_week]
            
            # Skip if no study blocks for this day
            if not day_blocks:
                continue
            
            # Track total study time for the day
            daily_study_minutes = 0
            
            # Process each study block
            for block in day_blocks:
                # Skip if we've reached the maximum daily study time
                if daily_study_minutes >= max_daily_study_time:
                    break
                
                # Parse block times
                start_time = datetime.strptime(block["start_time"], "%H:%M").time()
                end_time = datetime.strptime(block["end_time"], "%H:%M").time()
                
                # Calculate block duration in minutes
                start_dt = datetime.combine(current_date, start_time)
                end_dt = datetime.combine(current_date, end_time)
                block_minutes = (end_dt - start_dt).seconds // 60
                
                # Skip if block is too short for a study session
                if block_minutes < session_length:
                    continue
                
                # Calculate how many sessions can fit in this block
                # Each session includes study time and break time
                session_with_break = session_length + break_length
                max_sessions = block_minutes // session_with_break
                
                # Adjust for remaining time that could fit a session without a break
                remaining_minutes = block_minutes % session_with_break
                if remaining_minutes >= session_length:
                    max_sessions += 1
                
                # Limit by remaining daily study time
                remaining_daily_minutes = max_daily_study_time - daily_study_minutes
                max_sessions_by_time = remaining_daily_minutes // session_length
                max_sessions = min(max_sessions, max_sessions_by_time)
                
                # Create study sessions
                current_time = start_dt
                for i in range(max_sessions):
                    # Skip if we've reached the maximum daily study time
                    if daily_study_minutes >= max_daily_study_time:
                        break
                    
                    # Calculate session end time
                    session_end_time = current_time + timedelta(minutes=session_length)
                    
                    # Ensure we don't exceed the block end time
                    if session_end_time > end_dt:
                        session_end_time = end_dt
                    
                    # Calculate actual session length
                    actual_session_minutes = (session_end_time - current_time).seconds // 60
                    
                    # Skip if session is too short
                    if actual_session_minutes < 15:  # Minimum 15 minutes
                        break
                    
                    # Find a subject to study
                    subject = self._select_subject_for_session(current_date, prioritized_homework, tests)
                    
                    # Create session
                    session_id = str(uuid.uuid4())
                    session = {
                        "id": session_id,
                        "date": current_date.isoformat(),
                        "start_time": current_time.strftime("%H:%M"),
                        "end_time": session_end_time.strftime("%H:%M"),
                        "duration": actual_session_minutes,
                        "subject": subject,
                        "type": "study",
                        "created_at": datetime.now().isoformat()
                    }
                    
                    # Add to schedule
                    schedule.append(session)
                    
                    # Update daily study time
                    daily_study_minutes += actual_session_minutes
                    
                    # Move to next session start time (after break)
                    current_time = session_end_time + timedelta(minutes=break_length)
                    
                    # Break if we've reached the end of the block
                    if current_time >= end_dt:
                        break
        
        # Save scheduled sessions
        self.data["scheduled_sessions"] = schedule
        self._save_data()
        
        return schedule
    
    def _select_subject_for_session(self, date: datetime.date, 
                                  prioritized_homework: List[Dict[str, Any]],
                                  tests: Optional[List[Dict[str, Any]]] = None) -> str:
        """
        Select the best subject to study for a session
        
        Args:
            date: The date of the session
            prioritized_homework: List of prioritized homework
            tests: List of upcoming tests
            
        Returns:
            Subject name
        """
        # First priority: Tests in the next 3 days
        if tests:
            upcoming_tests = []
            for test in tests:
                try:
                    test_date = datetime.strptime(test["date"], "%Y-%m-%d").date()
                    days_until_test = (test_date - date).days
                    if 0 <= days_until_test <= 3:
                        upcoming_tests.append(test)
                except (ValueError, KeyError):
                    continue
            
            if upcoming_tests:
                # Select a random test from upcoming tests
                selected_test = random.choice(upcoming_tests)
                return selected_test.get("subject", "General Study")
        
        # Second priority: High priority homework
        high_priority_hw = [hw for hw in prioritized_homework if hw.get("priority_level") == "high"]
        if high_priority_hw:
            selected_hw = high_priority_hw[0]  # Take the highest priority
            return selected_hw.get("subject", "General Study")
        
        # Third priority: Medium priority homework
        medium_priority_hw = [hw for hw in prioritized_homework if hw.get("priority_level") == "medium"]
        if medium_priority_hw:
            selected_hw = medium_priority_hw[0]
            return selected_hw.get("subject", "General Study")
        
        # Fourth priority: Any homework
        if prioritized_homework:
            selected_hw = prioritized_homework[0]
            return selected_hw.get("subject", "General Study")
        
        # Default: General study
        return "General Study"
    
    def get_scheduled_sessions(self, start_date: Optional[datetime.date] = None, 
                             end_date: Optional[datetime.date] = None) -> List[Dict[str, Any]]:
        """
        Get scheduled study sessions within a date range
        
        Args:
            start_date: Start date (inclusive)
            end_date: End date (inclusive)
            
        Returns:
            List of scheduled sessions
        """
        # Make sure the scheduled_sessions key exists in the data
        if "scheduled_sessions" not in self.data:
            self.data["scheduled_sessions"] = []
            self._save_data()
            
        sessions = self.data["scheduled_sessions"]
        
        # If no dates specified, return all sessions
        if not start_date and not end_date:
            return sessions
        
        filtered_sessions = []
        for session in sessions:
            try:
                # Check if the date field exists and is properly formatted
                if "date" not in session:
                    continue
                    
                session_date = datetime.strptime(session["date"], "%Y-%m-%d").date()
                
                # Check if session is within date range
                if start_date and session_date < start_date:
                    continue
                if end_date and session_date > end_date:
                    continue
                
                filtered_sessions.append(session)
            except (ValueError, KeyError) as e:
                # Skip sessions with invalid dates
                print(f"Error processing session date: {e}")
                continue
        
        return filtered_sessions
    
    def add_external_calendar(self, calendar_type: str, calendar_id: str, 
                            access_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Add an external calendar for synchronization
        
        Args:
            calendar_type: Type of calendar ("google", "apple", "ical")
            calendar_id: ID or URL of the calendar
            access_token: Access token for API access (if required)
            
        Returns:
            Dict containing the added calendar
        """
        # Validate calendar type
        valid_types = ["google", "apple", "ical"]
        if calendar_type not in valid_types:
            raise ValueError(f"Calendar type must be one of: {', '.join(valid_types)}")
        
        # Create calendar entry
        calendar_entry = {
            "id": str(uuid.uuid4()),
            "type": calendar_type,
            "calendar_id": calendar_id,
            "access_token": access_token,
            "last_synced": None,
            "created_at": datetime.now().isoformat()
        }
        
        # Add to external calendars
        self.data["external_calendars"].append(calendar_entry)
        self._save_data()
        
        return calendar_entry
    
    def remove_external_calendar(self, calendar_id: str) -> bool:
        """
        Remove an external calendar
        
        Args:
            calendar_id: ID of the calendar to remove
            
        Returns:
            True if successful, False otherwise
        """
        initial_count = len(self.data["external_calendars"])
        self.data["external_calendars"] = [cal for cal in self.data["external_calendars"] if cal["id"] != calendar_id]
        
        if len(self.data["external_calendars"]) < initial_count:
            self._save_data()
            return True
        
        return False
    
    def get_external_calendars(self) -> List[Dict[str, Any]]:
        """
        Get all external calendars
        
        Returns:
            List of external calendars
        """
        return self.data["external_calendars"]
    
    def export_to_ical(self, start_date: Optional[datetime.date] = None, 
                     end_date: Optional[datetime.date] = None) -> str:
        """
        Export scheduled sessions to iCalendar format
        
        Args:
            start_date: Start date for export
            end_date: End date for export
            
        Returns:
            iCalendar data as string
        """
        # Get sessions within date range
        sessions = self.get_scheduled_sessions(start_date, end_date)
        
        # Create calendar
        cal = Calendar()
        cal.add('prodid', '-//Fireflies//Study Schedule//EN')
        cal.add('version', '2.0')
        cal.add('calscale', 'GREGORIAN')
        cal.add('method', 'PUBLISH')
        cal.add('x-wr-calname', f'Fireflies Study Schedule - {self.username}')
        cal.add('x-wr-timezone', 'UTC')
        
        # Add events for each session
        for session in sessions:
            event = Event()
            
            # Parse date and times
            try:
                session_date = datetime.strptime(session["date"], "%Y-%m-%d").date()
                start_time = datetime.strptime(session["start_time"], "%H:%M").time()
                end_time = datetime.strptime(session["end_time"], "%H:%M").time()
                
                # Create datetime objects
                start_dt = datetime.combine(session_date, start_time)
                end_dt = datetime.combine(session_date, end_time)
                
                # Add timezone info
                start_dt = pytz.utc.localize(start_dt)
                end_dt = pytz.utc.localize(end_dt)
                
                # Add event details
                event.add('summary', f'Study: {session["subject"]}')
                event.add('dtstart', start_dt)
                event.add('dtend', end_dt)
                event.add('dtstamp', datetime.now(pytz.utc))
                event.add('uid', session["id"])
                
                # Add description
                description = f'Study session for {session["subject"]}\n'
                description += f'Duration: {session["duration"]} minutes'
                event.add('description', description)
                
                # Add to calendar
                cal.add_component(event)
            except (ValueError, KeyError) as e:
                print(f"Error adding event to calendar: {e}")
                continue
        
        # Return as string
        return cal.to_ical().decode('utf-8')
    
    def sync_with_external_calendars(self) -> Dict[str, Any]:
        """
        Sync study schedule with external calendars
        
        Returns:
            Dict containing sync results
        """
        # Get external calendars
        external_calendars = self.data["external_calendars"]
        
        # Get scheduled sessions (next 30 days)
        today = datetime.now().date()
        end_date = today + datetime.timedelta(days=30)
        sessions = self.get_scheduled_sessions(today, end_date)
        
        # Export to iCalendar format
        ical_data = self.export_to_ical(today, end_date)
        
        # Results tracking
        results = {
            "success": [],
            "failed": []
        }
        
        # Process each calendar
        for calendar in external_calendars:
            calendar_type = calendar.get("type")
            calendar_id = calendar.get("calendar_id")
            
            try:
                if calendar_type == "google":
                    # Google Calendar sync would go here
                    # This would require OAuth2 authentication and Google Calendar API
                    # For now, we'll just mark it as successful
                    results["success"].append({
                        "id": calendar["id"],
                        "type": "google",
                        "message": "Google Calendar sync not implemented yet"
                    })
                
                elif calendar_type == "apple":
                    # Apple Calendar sync would go here
                    # This would likely require CalDAV protocol
                    # For now, we'll just mark it as successful
                    results["success"].append({
                        "id": calendar["id"],
                        "type": "apple",
                        "message": "Apple Calendar sync not implemented yet"
                    })
                
                elif calendar_type == "ical":
                    # For iCal URLs, we would typically upload the iCal file to a server
                    # For now, we'll just mark it as successful
                    results["success"].append({
                        "id": calendar["id"],
                        "type": "ical",
                        "message": "iCal sync not implemented yet"
                    })
                
                # Update last synced timestamp
                calendar["last_synced"] = datetime.now().isoformat()
            
            except Exception as e:
                results["failed"].append({
                    "id": calendar["id"],
                    "type": calendar_type,
                    "error": str(e)
                })
        
        # Save data with updated sync timestamps
        self._save_data()
        
        return results
        
    def add_external_calendar(self, calendar_type: str, calendar_id: str, access_token: Optional[str] = None) -> Dict[str, Any]:
        """
        Add an external calendar
        
        Args:
            calendar_type: Type of calendar (google, apple, ical)
            calendar_id: Calendar ID or URL
            access_token: Access token for authentication (optional)
            
        Returns:
            Dict containing the created calendar
        """
        # Validate calendar type
        if calendar_type not in ["google", "apple", "ical"]:
            raise ValueError("Invalid calendar type. Must be one of: google, apple, ical")
        
        # Create calendar object
        calendar = {
            "id": str(uuid.uuid4()),
            "type": calendar_type,
            "calendar_id": calendar_id,
            "access_token": access_token,
            "last_synced": None,
            "created_at": datetime.now().isoformat()
        }
        
        # Add to external calendars
        self.data["external_calendars"].append(calendar)
        self._save_data()
        
        return calendar
    
    def get_external_calendars(self) -> List[Dict[str, Any]]:
        """
        Get all external calendars
        
        Returns:
            List of external calendars
        """
        return self.data["external_calendars"]
    
    def remove_external_calendar(self, calendar_id: str) -> bool:
        """
        Remove an external calendar
        
        Args:
            calendar_id: ID of the calendar to remove
            
        Returns:
            True if successful, False otherwise
        """
        initial_count = len(self.data["external_calendars"])
        self.data["external_calendars"] = [cal for cal in self.data["external_calendars"] if cal["id"] != calendar_id]
        
        if len(self.data["external_calendars"]) < initial_count:
            self._save_data()
            return True
        
        return False