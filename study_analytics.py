"""
Study Analytics System for tracking and analyzing study habits and performance
"""

import json
import datetime
import os
import math
import random
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from flashcard_system import FlashcardManager

# Path for analytics data
ANALYTICS_DIR = Path('data/analytics')
os.makedirs(ANALYTICS_DIR, exist_ok=True)

class StudyAnalytics:
    """Class to manage study analytics"""
    
    def __init__(self, username: str):
        """
        Initialize the study analytics for a user
        
        Args:
            username: The username of the user
        """
        self.username = username
        self.user_dir = ANALYTICS_DIR / username
        os.makedirs(self.user_dir, exist_ok=True)
        self.data_file = self.user_dir / "study_data.json"
        self.data = self._load_data()
        self.flashcard_manager = FlashcardManager(username)
        
    def _load_data(self) -> Dict[str, Any]:
        """
        Load study analytics data from file
        
        Returns:
            Dict containing study analytics data
        """
        if not self.data_file.exists():
            # Initialize with default data
            return {
                "study_sessions": [],
                "flashcard_reviews": [],
                "subject_performance": {},
                "daily_stats": {},
                "weekly_stats": {},
                "monthly_stats": {},
                "study_streak": 0,
                "last_study_date": None,
                "total_study_time": 0,
                "preferences": {
                    "best_study_time": None,
                    "best_study_days": [],
                    "favorite_subjects": []
                }
            }
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading study analytics data: {e}")
            return {
                "study_sessions": [],
                "flashcard_reviews": [],
                "subject_performance": {},
                "daily_stats": {},
                "weekly_stats": {},
                "monthly_stats": {},
                "study_streak": 0,
                "last_study_date": None,
                "total_study_time": 0,
                "preferences": {
                    "best_study_time": None,
                    "best_study_days": [],
                    "favorite_subjects": []
                }
            }
    
    def _save_data(self) -> None:
        """Save study analytics data to file"""
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving study analytics data: {e}")
    
    def record_flashcard_session(self, set_id: str, stats: Dict[str, Any], duration: int) -> None:
        """
        Record a flashcard study session
        
        Args:
            set_id: The ID of the flashcard set
            stats: Statistics about the study session
                - failed: Number of cards rated as failed
                - hard: Number of cards rated as hard
                - good: Number of cards rated as good
                - easy: Number of cards rated as easy
                - total: Total number of cards reviewed
            duration: Duration of the session in seconds
        """
        # Get the flashcard set
        flashcard_set = self.flashcard_manager.get_set(set_id)
        
        if not flashcard_set:
            print(f"Error: Flashcard set {set_id} not found")
            return
        
        # Create session data
        now = datetime.datetime.now()
        session_data = {
            "id": f"session_{len(self.data['study_sessions']) + 1}_{int(now.timestamp())}",
            "type": "flashcard",
            "set_id": set_id,
            "set_name": flashcard_set.get("name", "Unknown"),
            "subject": flashcard_set.get("subject", "Unknown"),
            "date": now.isoformat(),
            "day_of_week": now.weekday(),  # 0 = Monday, 6 = Sunday
            "hour_of_day": now.hour,
            "duration": duration,
            "stats": stats,
            "performance": self._calculate_performance(stats)
        }
        
        # Add to study sessions
        self.data["study_sessions"].append(session_data)
        
        # Add to flashcard reviews
        for _ in range(stats.get("total", 0)):
            review_data = {
                "session_id": session_data["id"],
                "set_id": set_id,
                "subject": flashcard_set.get("subject", "Unknown"),
                "date": now.isoformat(),
                "performance": "correct" if random.random() > 0.3 else "incorrect"  # Simplified for now
            }
            self.data["flashcard_reviews"].append(review_data)
        
        # Update subject performance
        subject = flashcard_set.get("subject", "Unknown")
        if subject not in self.data["subject_performance"]:
            self.data["subject_performance"][subject] = {
                "sessions": 0,
                "total_cards": 0,
                "correct_cards": 0,
                "total_time": 0,
                "mastery": 0
            }
        
        self.data["subject_performance"][subject]["sessions"] += 1
        self.data["subject_performance"][subject]["total_cards"] += stats.get("total", 0)
        self.data["subject_performance"][subject]["correct_cards"] += (stats.get("good", 0) + stats.get("easy", 0))
        self.data["subject_performance"][subject]["total_time"] += duration
        
        # Calculate mastery level (0-100)
        if self.data["subject_performance"][subject]["total_cards"] > 0:
            mastery = (self.data["subject_performance"][subject]["correct_cards"] / 
                      self.data["subject_performance"][subject]["total_cards"]) * 100
            self.data["subject_performance"][subject]["mastery"] = round(mastery, 1)
        
        # Update daily stats
        date_key = now.date().isoformat()
        if date_key not in self.data["daily_stats"]:
            self.data["daily_stats"][date_key] = {
                "study_time": 0,
                "cards_reviewed": 0,
                "correct_cards": 0,
                "sessions": 0
            }
        
        self.data["daily_stats"][date_key]["study_time"] += duration
        self.data["daily_stats"][date_key]["cards_reviewed"] += stats.get("total", 0)
        self.data["daily_stats"][date_key]["correct_cards"] += (stats.get("good", 0) + stats.get("easy", 0))
        self.data["daily_stats"][date_key]["sessions"] += 1
        
        # Update weekly stats
        year, week, _ = now.isocalendar()
        week_key = f"{year}-W{week:02d}"
        if week_key not in self.data["weekly_stats"]:
            self.data["weekly_stats"][week_key] = {
                "study_time": 0,
                "cards_reviewed": 0,
                "correct_cards": 0,
                "sessions": 0,
                "days_studied": []
            }
        
        self.data["weekly_stats"][week_key]["study_time"] += duration
        self.data["weekly_stats"][week_key]["cards_reviewed"] += stats.get("total", 0)
        self.data["weekly_stats"][week_key]["correct_cards"] += (stats.get("good", 0) + stats.get("easy", 0))
        self.data["weekly_stats"][week_key]["sessions"] += 1
        
        if date_key not in self.data["weekly_stats"][week_key]["days_studied"]:
            self.data["weekly_stats"][week_key]["days_studied"].append(date_key)
        
        # Update monthly stats
        month_key = f"{now.year}-{now.month:02d}"
        if month_key not in self.data["monthly_stats"]:
            self.data["monthly_stats"][month_key] = {
                "study_time": 0,
                "cards_reviewed": 0,
                "correct_cards": 0,
                "sessions": 0,
                "days_studied": []
            }
        
        self.data["monthly_stats"][month_key]["study_time"] += duration
        self.data["monthly_stats"][month_key]["cards_reviewed"] += stats.get("total", 0)
        self.data["monthly_stats"][month_key]["correct_cards"] += (stats.get("good", 0) + stats.get("easy", 0))
        self.data["monthly_stats"][month_key]["sessions"] += 1
        
        if date_key not in self.data["monthly_stats"][month_key]["days_studied"]:
            self.data["monthly_stats"][month_key]["days_studied"].append(date_key)
        
        # Update study streak
        self._update_study_streak(now.date())
        
        # Update total study time
        self.data["total_study_time"] += duration
        
        # Update preferences
        self._update_preferences()
        
        # Save data
        self._save_data()
    
    def _calculate_performance(self, stats: Dict[str, Any]) -> float:
        """
        Calculate performance score from stats (0-100)
        
        Args:
            stats: Statistics about the study session
            
        Returns:
            Performance score (0-100)
        """
        if stats.get("total", 0) == 0:
            return 0
        
        # Weight different ratings
        weighted_sum = (
            stats.get("easy", 0) * 1.0 +
            stats.get("good", 0) * 0.8 +
            stats.get("hard", 0) * 0.4 +
            stats.get("failed", 0) * 0.0
        )
        
        # Calculate performance (0-100)
        performance = (weighted_sum / stats.get("total", 0)) * 100
        
        return round(performance, 1)
    
    def _update_study_streak(self, study_date: datetime.date) -> None:
        """
        Update the study streak
        
        Args:
            study_date: The date of the study session
        """
        last_study_date = self.data.get("last_study_date")
        
        if not last_study_date:
            # First study session
            self.data["study_streak"] = 1
            self.data["last_study_date"] = study_date.isoformat()
            return
        
        # Convert to date object if it's a string
        if isinstance(last_study_date, str):
            last_study_date = datetime.date.fromisoformat(last_study_date)
        
        # If already studied today, no streak update
        if last_study_date == study_date:
            return
        
        # If studied yesterday, increment streak
        if (study_date - last_study_date).days == 1:
            self.data["study_streak"] += 1
        # If missed a day, reset streak
        elif (study_date - last_study_date).days > 1:
            self.data["study_streak"] = 1
        
        self.data["last_study_date"] = study_date.isoformat()
    
    def _update_preferences(self) -> None:
        """Update user study preferences based on analytics"""
        # Find best study time
        hour_counts = {}
        for session in self.data["study_sessions"]:
            hour = session.get("hour_of_day")
            if hour is not None:
                hour_counts[hour] = hour_counts.get(hour, 0) + 1
        
        if hour_counts:
            best_hour = max(hour_counts, key=hour_counts.get)
            self.data["preferences"]["best_study_time"] = best_hour
        
        # Find best study days
        day_counts = {}
        for session in self.data["study_sessions"]:
            day = session.get("day_of_week")
            if day is not None:
                day_counts[day] = day_counts.get(day, 0) + 1
        
        if day_counts:
            # Get the top 3 days
            best_days = sorted(day_counts.keys(), key=lambda d: day_counts[d], reverse=True)[:3]
            self.data["preferences"]["best_study_days"] = best_days
        
        # Find favorite subjects
        subject_counts = {}
        for session in self.data["study_sessions"]:
            subject = session.get("subject")
            if subject and subject != "Unknown":
                subject_counts[subject] = subject_counts.get(subject, 0) + 1
        
        if subject_counts:
            # Get the top 3 subjects
            favorite_subjects = sorted(subject_counts.keys(), key=lambda s: subject_counts[s], reverse=True)[:3]
            self.data["preferences"]["favorite_subjects"] = favorite_subjects
    
    def get_study_data(self, period: str = "week") -> Dict[str, Any]:
        """
        Get study data for the specified period, including historical data
        
        Args:
            period: The period to get data for ("week", "month", "year")
            
        Returns:
            Dict containing study data
        """
        now = datetime.datetime.now()
        
        # Determine date range based on period
        if period == "week":
            start_date = (now - datetime.timedelta(days=7)).date()
        elif period == "month":
            start_date = (now - datetime.timedelta(days=30)).date()
        elif period == "year":
            start_date = (now - datetime.timedelta(days=365)).date()
        else:
            start_date = (now - datetime.timedelta(days=7)).date()
        
        # Get all study sessions
        all_sessions = self.data.get("study_sessions", [])
        
        # Filter sessions by date for the current period
        filtered_sessions = []
        for session in all_sessions:
            try:
                session_date = datetime.datetime.fromisoformat(session.get("date", "")).date()
                if session_date >= start_date:
                    filtered_sessions.append(session)
            except (ValueError, TypeError):
                # Skip sessions with invalid dates
                continue
        
        # Calculate total study time in minutes
        total_time_seconds = sum(session.get("duration", 0) for session in filtered_sessions)
        total_time_minutes = total_time_seconds // 60
        total_time_str = f"{total_time_minutes // 60}h {total_time_minutes % 60}m"
        
        # Calculate cards reviewed
        cards_reviewed = sum(session.get("stats", {}).get("total", 0) for session in filtered_sessions)
        
        # Calculate accuracy
        correct_cards = sum((session.get("stats", {}).get("good", 0) + session.get("stats", {}).get("easy", 0)) 
                           for session in filtered_sessions)
        accuracy = 0
        if cards_reviewed > 0:
            accuracy = round((correct_cards / cards_reviewed) * 100)
        
        # Get current streak
        streak = self.data.get("study_streak", 0)
        
        # Prepare activity data using all historical sessions
        activity_data = self._prepare_activity_data(filtered_sessions, period)
        
        # Prepare subject performance data using all historical data
        subject_data = self._prepare_subject_data()
        
        # Prepare learning progress data using all historical data
        progress_data = self._prepare_progress_data(period)
        
        # Prepare heatmap data
        heatmap_data = self._prepare_heatmap_data(filtered_sessions)
        
        # Ensure we have valid data structures even if no data is available
        if not activity_data:
            activity_data = {
                "labels": self._generate_default_labels(period),
                "data": [0] * len(self._generate_default_labels(period))
            }
            
        if not subject_data:
            subject_data = {
                "labels": ["No subjects yet"],
                "data": [0]
            }
            
        if not progress_data:
            default_labels = self._generate_default_labels(period)
            progress_data = {
                "labels": default_labels,
                "mastered": [0] * len(default_labels),
                "learning": [0] * len(default_labels),
                "not_started": [0] * len(default_labels)
            }
            
        if not heatmap_data:
            heatmap_data = {
                "data": []
            }
        
        return {
            "total_time": total_time_str,
            "cards_reviewed": cards_reviewed,
            "accuracy": accuracy,
            "streak": streak,
            "activity": activity_data,
            "subjects": subject_data,
            "progress": progress_data,
            "heatmap": heatmap_data
        }
        
    def _generate_default_labels(self, period: str) -> List[str]:
        """
        Generate default labels for charts based on period
        
        Args:
            period: The period to generate labels for ("week", "month", "year")
            
        Returns:
            List of labels
        """
        now = datetime.datetime.now()
        labels = []
        
        if period == "week":
            # Daily labels for the past week
            for i in range(6, -1, -1):
                date = now - datetime.timedelta(days=i)
                labels.append(date.strftime("%a"))
        elif period == "month":
            # Weekly labels for the past month
            for i in range(3, -1, -1):
                week_start = now - datetime.timedelta(days=now.weekday() + 7 * i + 7)
                week_end = week_start + datetime.timedelta(days=6)
                labels.append(f"{week_start.strftime('%d/%m')}-{week_end.strftime('%d/%m')}")
        else:  # year
            # Monthly labels for the past year
            for i in range(11, -1, -1):
                month_date = now - datetime.timedelta(days=30 * i)
                labels.append(month_date.strftime("%b"))
                
        return labels
    
    def get_flashcard_set_progress(self) -> List[Dict[str, Any]]:
        """
        Get progress data for each flashcard set
        
        Returns:
            List of dictionaries with flashcard set progress data
        """
        # Get all flashcard sets
        flashcard_sets = self.flashcard_manager.get_all_sets()
        
        if not flashcard_sets:
            return []
        
        result = []
        
        for set_id, set_data in flashcard_sets.items():
            # Get cards in the set
            cards = self.flashcard_manager.get_cards(set_id)
            
            if not cards:
                continue
            
            # Calculate mastery for each card
            total_cards = len(cards)
            cards_mastered = 0
            
            for card in cards:
                # Consider a card mastered if its mastery level is >= 0.7 (70%)
                if card.get("mastery", 0) >= 0.7:
                    cards_mastered += 1
            
            # Calculate overall mastery percentage
            mastery_percentage = round((cards_mastered / total_cards) * 100) if total_cards > 0 else 0
            
            # Get subject from set data
            subject = set_data.get("subject", "Unknown")
            
            # Add to result
            result.append({
                "id": set_id,
                "name": set_data.get("name", "Unknown Set"),
                "subject": subject,
                "total_cards": total_cards,
                "cards_mastered": cards_mastered,
                "mastery_percentage": mastery_percentage,
                "last_studied": set_data.get("last_studied", None)
            })
        
        # Sort by last studied date (most recent first)
        result.sort(key=lambda x: x.get("last_studied", ""), reverse=True)
        
        return result
    
    def get_difficult_cards(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most difficult flashcards based on review history
        
        Args:
            limit: Maximum number of cards to return
            
        Returns:
            List of dictionaries with difficult card data
        """
        # Get all flashcard reviews
        reviews = self.data.get("flashcard_reviews", [])
        
        if not reviews:
            return []
        
        # Group reviews by card_id
        card_stats = {}
        
        for review in reviews:
            card_id = review.get("card_id")
            if not card_id:
                continue
            
            if card_id not in card_stats:
                card_stats[card_id] = {
                    "total": 0,
                    "incorrect": 0,
                    "set_id": review.get("set_id"),
                    "subject": review.get("subject", "Unknown")
                }
            
            card_stats[card_id]["total"] += 1
            if review.get("performance") == "incorrect":
                card_stats[card_id]["incorrect"] += 1
        
        # Calculate failure rate for each card
        difficult_cards = []
        
        for card_id, stats in card_stats.items():
            if stats["total"] < 3:  # Require at least 3 reviews
                continue
            
            failure_rate = round((stats["incorrect"] / stats["total"]) * 100)
            
            # Only include cards with failure rate > 30%
            if failure_rate > 30:
                # Get card details
                set_id = stats["set_id"]
                if set_id:
                    card = self.flashcard_manager.get_card(set_id, card_id)
                    set_data = self.flashcard_manager.get_set(set_id)
                    
                    if card and set_data:
                        difficult_cards.append({
                            "id": card_id,
                            "question": card.get("question", "Unknown"),
                            "set_id": set_id,
                            "set_name": set_data.get("name", "Unknown Set"),
                            "subject": stats["subject"],
                            "failure_rate": failure_rate,
                            "total_reviews": stats["total"]
                        })
        
        # Sort by failure rate (highest first)
        difficult_cards.sort(key=lambda x: x["failure_rate"], reverse=True)
        
        return difficult_cards[:limit]
    
    def get_study_recommendations(self) -> List[Dict[str, Any]]:
        """
        Generate personalized study recommendations based on analytics
        
        Returns:
            List of dictionaries with recommendation data
        """
        recommendations = []
        
        # 1. Recommend reviewing difficult cards
        difficult_cards = self.get_difficult_cards(limit=3)
        if difficult_cards:
            subjects = set(card["subject"] for card in difficult_cards)
            subject_list = ", ".join(subjects)
            
            recommendations.append({
                "type": "review",
                "title": "Review Difficult Cards",
                "description": f"Focus on reviewing difficult cards in {subject_list}.",
                "priority": "high"
            })
        
        # 2. Recommend based on study streak
        streak = self.data.get("study_streak", 0)
        if streak == 0:
            recommendations.append({
                "type": "schedule",
                "title": "Start a Study Streak",
                "description": "Study today to start building a streak and improve retention.",
                "priority": "medium"
            })
        elif streak > 0 and streak < 3:
            recommendations.append({
                "type": "schedule",
                "title": "Maintain Your Streak",
                "description": f"You have a {streak}-day streak. Keep it going!",
                "priority": "medium"
            })
        
        # 3. Recommend based on best study time
        best_time = self.data.get("preferences", {}).get("best_study_time")
        if best_time is not None:
            # Convert 24-hour format to 12-hour format with AM/PM
            hour_12 = best_time % 12
            if hour_12 == 0:
                hour_12 = 12
            am_pm = "AM" if best_time < 12 else "PM"
            
            recommendations.append({
                "type": "schedule",
                "title": "Optimal Study Time",
                "description": f"Your data shows you study best around {hour_12} {am_pm}.",
                "priority": "low"
            })
        
        # 4. Recommend based on subject performance
        subject_performance = self.data.get("subject_performance", {})
        if subject_performance:
            # Find subject with lowest mastery
            lowest_mastery_subject = min(
                subject_performance.items(),
                key=lambda x: x[1].get("mastery", 100) if x[1].get("sessions", 0) > 0 else 100
            )
            
            subject_name = lowest_mastery_subject[0]
            mastery = lowest_mastery_subject[1].get("mastery", 0)
            
            if mastery < 70 and lowest_mastery_subject[1].get("sessions", 0) > 0:
                recommendations.append({
                    "type": "focus",
                    "title": f"Focus on {subject_name}",
                    "description": f"Your mastery in {subject_name} is {mastery}%. More practice needed.",
                    "priority": "high"
                })
        
        # 5. General recommendation based on total study time
        total_time_minutes = self.data.get("total_study_time", 0) // 60
        if total_time_minutes < 60:  # Less than 1 hour total
            recommendations.append({
                "type": "general",
                "title": "Increase Study Time",
                "description": "Try to study for at least 20 minutes each day for better results.",
                "priority": "medium"
            })
        
        return recommendations
    
    def _prepare_subject_data(self) -> Dict[str, Any]:
        """
        Prepare subject performance data for radar chart
        
        Returns:
            Dict with labels and data for subject performance chart
        """
        subject_performance = self.data.get("subject_performance", {})
        
        if not subject_performance:
            return {}
        
        # Get subjects with at least one session
        active_subjects = {
            subject: data for subject, data in subject_performance.items()
            if data.get("sessions", 0) > 0
        }
        
        if not active_subjects:
            return {}
        
        # Prepare data for chart
        labels = list(active_subjects.keys())
        mastery = [active_subjects[subject].get("mastery", 0) for subject in labels]
        
        return {
            "labels": labels,
            "mastery": mastery
        }
    
    def _prepare_progress_data(self, period: str) -> Dict[str, Any]:
        """
        Prepare learning progress data over time
        
        Args:
            period: The period to get data for ("week", "month", "year")
            
        Returns:
            Dict with labels and data for progress chart
        """
        now = datetime.datetime.now()
        
        # Determine date range based on period
        if period == "week":
            start_date = (now - datetime.timedelta(days=7)).date()
            date_format = "%a"  # Abbreviated weekday name
        elif period == "month":
            start_date = (now - datetime.timedelta(days=30)).date()
            date_format = "%d %b"  # Day and abbreviated month name
        elif period == "year":
            start_date = (now - datetime.timedelta(days=365)).date()
            date_format = "%b"  # Abbreviated month name
        else:
            start_date = (now - datetime.timedelta(days=7)).date()
            date_format = "%a"
        
        # Get daily stats
        daily_stats = self.data.get("daily_stats", {})
        
        if not daily_stats:
            return {}
        
        # Generate date range
        date_range = []
        current_date = start_date
        while current_date <= now.date():
            date_range.append(current_date)
            current_date += datetime.timedelta(days=1)
        
        # Prepare data
        labels = [date.strftime(date_format) for date in date_range]
        accuracy_data = []
        
        for date in date_range:
            date_key = date.isoformat()
            if date_key in daily_stats:
                stats = daily_stats[date_key]
                cards_reviewed = stats.get("cards_reviewed", 0)
                correct_cards = stats.get("correct_cards", 0)
                
                if cards_reviewed > 0:
                    accuracy = (correct_cards / cards_reviewed) * 100
                    accuracy_data.append(round(accuracy))
                else:
                    accuracy_data.append(None)  # No data for this day
            else:
                accuracy_data.append(None)  # No data for this day
        
        return {
            "labels": labels,
            "accuracy": accuracy_data
        }
    
    def _prepare_heatmap_data(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Prepare heatmap data for study activity
        
        Args:
            sessions: List of study sessions
            
        Returns:
            Dict with data for heatmap
        """
        # Group sessions by date
        session_dates = {}
        
        for session in sessions:
            date_str = session.get("date", "")
            if date_str:
                date = datetime.datetime.fromisoformat(date_str).date().isoformat()
                if date not in session_dates:
                    session_dates[date] = {
                        "count": 0,
                        "duration": 0
                    }
                
                session_dates[date]["count"] += 1
                session_dates[date]["duration"] += session.get("duration", 0)
        
        # Convert to format needed for heatmap
        heatmap_data = [
            {
                "date": date,
                "count": data["count"],
                "duration": data["duration"] // 60  # Convert to minutes
            }
            for date, data in session_dates.items()
        ]
        
        return heatmap_data
    
    def _prepare_activity_data(self, sessions: List[Dict[str, Any]], period: str) -> Dict[str, Any]:
        """
        Prepare activity data for chart using historical session data
        
        Args:
            sessions: List of study sessions
            period: The period to get data for ("week", "month", "year")
            
        Returns:
            Dict with labels and data for activity chart
        """
        now = datetime.datetime.now()
        
        if period == "week":
            # Daily data for the past week
            labels = []
            data = [0] * 7
            cards_data = [0] * 7
            
            # Generate date labels for the past week
            for i in range(6, -1, -1):
                date = now - datetime.timedelta(days=i)
                labels.append(date.strftime("%a"))
            
            # Process each session
            for session in sessions:
                try:
                    session_date = datetime.datetime.fromisoformat(session.get("date", ""))
                    days_ago = (now - session_date).days
                    
                    if 0 <= days_ago < 7:
                        # Add study time in minutes
                        data[6 - days_ago] += session.get("duration", 0) // 60
                        # Add cards reviewed
                        cards_data[6 - days_ago] += session.get("stats", {}).get("total", 0)
                except (ValueError, TypeError):
                    # Skip sessions with invalid dates
                    continue
        
        elif period == "month":
            # Weekly data for the past month
            labels = []
            data = [0] * 4
            cards_data = [0] * 4
            
            # Generate week labels for the past month
            for i in range(3, -1, -1):
                week_start = now - datetime.timedelta(days=now.weekday() + 7 * i + 7)
                week_end = week_start + datetime.timedelta(days=6)
                labels.append(f"{week_start.strftime('%d/%m')}-{week_end.strftime('%d/%m')}")
            
            # Process each session
            for session in sessions:
                try:
                    session_date = datetime.datetime.fromisoformat(session.get("date", ""))
                    days_ago = (now - session_date).days
                    
                    if 0 <= days_ago < 28:
                        week_index = days_ago // 7
                        if week_index < 4:
                            # Add study time in minutes
                            data[3 - week_index] += session.get("duration", 0) // 60
                            # Add cards reviewed
                            cards_data[3 - week_index] += session.get("stats", {}).get("total", 0)
                except (ValueError, TypeError):
                    # Skip sessions with invalid dates
                    continue
        
        else:  # year
            # Monthly data for the past year
            labels = []
            data = [0] * 12
            cards_data = [0] * 12
            
            # Generate month labels for the past year
            for i in range(11, -1, -1):
                month_date = now - datetime.timedelta(days=30 * i)
                labels.append(month_date.strftime("%b"))
            
            # Process each session
            for session in sessions:
                try:
                    session_date = datetime.datetime.fromisoformat(session.get("date", ""))
                    months_ago = (now.year - session_date.year) * 12 + now.month - session_date.month
                    
                    if 0 <= months_ago < 12:
                        # Add study time in minutes
                        data[11 - months_ago] += session.get("duration", 0) // 60
                        # Add cards reviewed
                        cards_data[11 - months_ago] += session.get("stats", {}).get("total", 0)
                except (ValueError, TypeError):
                    # Skip sessions with invalid dates
                    continue
        
        return {
            "labels": labels,
            "data": data,
            "cards_reviewed": cards_data
        }
    
    def _prepare_subject_data(self) -> Dict[str, Any]:
        """
        Prepare subject performance data for chart using historical data
        
        Returns:
            Dict with labels and data for subject performance chart
        """
        subjects = self.data.get("subject_performance", {})
        
        # Filter out subjects with no sessions
        active_subjects = {
            subject: stats for subject, stats in subjects.items()
            if stats.get("sessions", 0) > 0
        }
        
        labels = []
        mastery_data = []
        time_data = []
        cards_data = []
        
        for subject, stats in active_subjects.items():
            labels.append(subject)
            mastery_data.append(stats.get("mastery", 0))
            
            # Convert time to hours (from seconds)
            time_hours = round(stats.get("total_time", 0) / 3600, 1)
            time_data.append(time_hours)
            
            # Get total cards reviewed
            cards_data.append(stats.get("total_cards", 0))
        
        # If no subjects with sessions, provide a default
        if not labels:
            labels = ["No data yet"]
            mastery_data = [0]
            time_data = [0]
            cards_data = [0]
        
        return {
            "labels": labels,
            "data": mastery_data,
            "time": time_data,
            "cards": cards_data
        }
    
    def _prepare_progress_data(self, period: str) -> Dict[str, Any]:
        """
        Prepare learning progress data for chart using actual historical data
        
        Args:
            period: The period to get data for ("week", "month", "year")
            
        Returns:
            Dict with labels, mastered, learning, and not_started data
        """
        now = datetime.datetime.now()
        
        # Determine date range and format based on period
        if period == "week":
            # Daily data for the past week
            days = 7
            date_format = "%a"  # Abbreviated weekday name
            start_date = (now - datetime.timedelta(days=days)).date()
        elif period == "month":
            # Weekly data for the past month
            days = 30
            date_format = "%d %b"  # Day and abbreviated month name
            start_date = (now - datetime.timedelta(days=days)).date()
        else:  # year
            # Monthly data for the past year
            days = 365
            date_format = "%b %Y"  # Month and year
            start_date = (now - datetime.timedelta(days=days)).date()
        
        # Get all flashcard sets and their cards
        flashcard_sets = self.flashcard_manager.get_all_sets()
        all_cards = {}
        total_cards = 0
        
        for set_id, set_data in flashcard_sets.items():
            cards = self.flashcard_manager.get_cards(set_id)
            if cards:
                all_cards[set_id] = cards
                total_cards += len(cards)
        
        # Get all study sessions sorted by date
        all_sessions = sorted(
            self.data.get("study_sessions", []),
            key=lambda s: s.get("date", "")
        )
        
        # Generate date range
        date_range = []
        current_date = start_date
        while current_date <= now.date():
            date_range.append(current_date)
            current_date += datetime.timedelta(days=1)
        
        # Prepare data structures
        labels = [date.strftime(date_format) for date in date_range]
        mastered = []
        learning = []
        not_started = []
        
        # Track card mastery progress over time
        card_mastery_history = {}  # {card_id: {date: mastery_level}}
        
        # Initialize with all cards as not started
        for set_id, cards in all_cards.items():
            for card in cards:
                card_id = card.get("id")
                if card_id:
                    card_mastery_history[card_id] = {}
        
        # Process sessions to update card mastery over time
        for session in all_sessions:
            session_date = datetime.datetime.fromisoformat(session.get("date", "")).date()
            
            # Skip sessions before our start date
            if session_date < start_date:
                continue
                
            # Update mastery for cards in this session
            set_id = session.get("set_id")
            if set_id and set_id in all_cards:
                # In a real implementation, we would have detailed card-by-card mastery data
                # Here we'll use the session performance as a proxy for all cards in the set
                performance = session.get("performance", 0)
                
                for card in all_cards[set_id]:
                    card_id = card.get("id")
                    if card_id:
                        # Convert performance (0-100) to mastery level
                        mastery_level = min(1.0, performance / 100)
                        
                        # Update mastery for this card on this date
                        card_mastery_history[card_id][session_date.isoformat()] = mastery_level
        
        # Calculate mastery counts for each date in our range
        for date in date_range:
            date_str = date.isoformat()
            
            # Count cards in each category for this date
            mastered_count = 0
            learning_count = 0
            not_started_count = 0
            
            for card_id, history in card_mastery_history.items():
                # Find the most recent mastery level for this card up to this date
                latest_mastery = 0
                
                for history_date, mastery in sorted(history.items()):
                    if history_date <= date_str:
                        latest_mastery = mastery
                    else:
                        break
                
                # Categorize based on mastery level
                if latest_mastery >= 0.7:  # 70% or higher is considered mastered
                    mastered_count += 1
                elif latest_mastery > 0:   # Any progress is considered learning
                    learning_count += 1
                else:                      # No progress is not started
                    not_started_count += 1
            
            # Add counts to our data arrays
            mastered.append(mastered_count)
            learning.append(learning_count)
            not_started.append(not_started_count)
        
        # If we have no data, provide reasonable defaults
        if not card_mastery_history:
            # Start with all cards not started
            not_started = [total_cards] * len(date_range)
            mastered = [0] * len(date_range)
            learning = [0] * len(date_range)
        
        return {
            "labels": labels,
            "mastered": mastered,
            "learning": learning,
            "not_started": not_started
        }
    
    def _prepare_heatmap_data(self, sessions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Prepare heatmap data for chart using historical session data
        
        Args:
            sessions: List of study sessions
            
        Returns:
            Dict with heatmap data
        """
        # Initialize heatmap data (day of week x hour of day)
        heatmap = []
        
        # Count sessions by day and hour, and track duration
        day_hour_data = {}
        
        for session in sessions:
            try:
                # Get day and hour from session data
                day = session.get("day_of_week")
                hour = session.get("hour_of_day")
                
                # If day/hour not available in session, try to extract from date
                if day is None or hour is None:
                    date_str = session.get("date", "")
                    if date_str:
                        session_datetime = datetime.datetime.fromisoformat(date_str)
                        day = session_datetime.weekday()  # 0 = Monday, 6 = Sunday
                        hour = session_datetime.hour
                
                # Skip if we still don't have valid day/hour
                if day is None or hour is None:
                    continue
                
                # Get duration in minutes
                duration = session.get("duration", 0) // 60
                
                key = (day, hour)
                if key not in day_hour_data:
                    day_hour_data[key] = {
                        "count": 0,
                        "duration": 0
                    }
                
                day_hour_data[key]["count"] += 1
                day_hour_data[key]["duration"] += duration
            except (ValueError, TypeError):
                # Skip sessions with invalid data
                continue
        
        # Create heatmap data for all day/hour combinations
        for day in range(7):  # 0 = Monday, 6 = Sunday
            for hour in range(24):
                key = (day, hour)
                data = day_hour_data.get(key, {"count": 0, "duration": 0})
                
                # Use duration as the value, with a minimum of 1 if there was any activity
                value = data["duration"]
                if data["count"] > 0 and value == 0:
                    value = 1
                
                heatmap.append({
                    "day": day,
                    "hour": hour,
                    "value": value
                })
        
        return {
            "data": heatmap
        }
    
    def get_flashcard_set_progress(self) -> List[Dict[str, Any]]:
        """
        Get progress data for all flashcard sets
        
        Returns:
            List of dicts with set progress data
        """
        # Get all flashcard sets
        flashcard_sets_dict = self.flashcard_manager.get_all_sets()
        
        # Get due cards for each set
        result = []
        
        for set_id, set_data in flashcard_sets_dict.items():
            
            # Get due cards
            due_cards = self.flashcard_manager.get_due_cards(set_id)
            
            # Calculate mastery level
            mastery = 0
            cards = set_data.get("cards", [])
            
            if cards:
                mastered_cards = 0
                for card in cards:
                    if card.get("learning_data", {}).get("interval", 0) >= 7:
                        mastered_cards += 1
                
                mastery = round((mastered_cards / len(cards)) * 100)
            
            # Find last studied date
            last_studied = None
            for session in reversed(self.data["study_sessions"]):
                if session.get("set_id") == set_id:
                    last_studied = datetime.datetime.fromisoformat(session["date"]).strftime("%Y-%m-%d")
                    break
            
            result.append({
                "id": set_id,
                "name": set_data.get("name", "Unknown"),
                "subject": set_data.get("subject", "Unknown"),
                "card_count": len(cards),
                "mastery": mastery,
                "last_studied": last_studied,
                "due_cards": len(due_cards)
            })
        
        # Sort by due cards (descending) and then by mastery (ascending)
        result.sort(key=lambda x: (-x["due_cards"], x["mastery"]))
        
        return result
    
    def get_difficult_cards(self, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Get the most difficult cards across all sets
        
        Args:
            limit: Maximum number of cards to return
            
        Returns:
            List of dicts with difficult card data
        """
        # Get all flashcard sets
        flashcard_sets_dict = self.flashcard_manager.get_all_sets()
        
        # Find difficult cards
        difficult_cards = []
        
        for set_id, set_data in flashcard_sets_dict.items():
            subject = set_data.get("subject", "Unknown")
            
            for card in set_data.get("cards", []):
                # Calculate difficulty based on learning data
                difficulty = 5  # Default medium difficulty
                
                learning_data = card.get("learning_data", {})
                
                if learning_data:
                    # Cards with low ease factor and many reviews are difficult
                    ease_factor = learning_data.get("ease_factor", 2.5)
                    reviews = learning_data.get("reviews", 0)
                    
                    if reviews > 0:
                        # Scale from 1-10, where 10 is most difficult
                        # Lower ease factor = higher difficulty
                        ease_difficulty = max(0, min(10, (2.5 - ease_factor) * 10))
                        
                        # More reviews with still low ease factor indicates difficulty
                        review_factor = min(1, reviews / 10)  # Cap at 10 reviews
                        
                        difficulty = round(ease_difficulty * (0.5 + 0.5 * review_factor))
                
                # Only include cards with difficulty > 5
                if difficulty > 5:
                    difficult_cards.append({
                        "id": card.get("id", ""),
                        "set_id": set_id,
                        "question": card.get("question", ""),
                        "answer": card.get("answer", ""),
                        "subject": subject,
                        "difficulty": difficulty
                    })
        
        # Sort by difficulty (descending)
        difficult_cards.sort(key=lambda x: x["difficulty"], reverse=True)
        
        return difficult_cards[:limit]
    
    def get_study_recommendations(self) -> List[Dict[str, Any]]:
        """
        Get personalized study recommendations
        
        Returns:
            List of dicts with recommendation data
        """
        recommendations = []
        
        # Get flashcard set progress
        set_progress = self.get_flashcard_set_progress()
        
        # Recommendation 1: Sets with most due cards
        due_sets = [s for s in set_progress if s["due_cards"] > 0]
        if due_sets:
            most_due = due_sets[0]
            recommendations.append({
                "title": f"Réviser {most_due['name']}",
                "description": f"Vous avez {most_due['due_cards']} cartes à réviser dans cet ensemble.",
                "action_text": "Réviser",
                "action_url": f"/flashcard_quiz/{most_due['id']}?mode=due"
            })
        
        # Recommendation 2: Sets with low mastery
        low_mastery_sets = [s for s in set_progress if s["card_count"] > 0 and s["mastery"] < 50]
        if low_mastery_sets:
            lowest_mastery = min(low_mastery_sets, key=lambda x: x["mastery"])
            recommendations.append({
                "title": f"Améliorer la maîtrise de {lowest_mastery['name']}",
                "description": f"Votre niveau de maîtrise est de {lowest_mastery['mastery']}%. Continuez à étudier pour l'améliorer.",
                "action_text": "Étudier",
                "action_url": f"/flashcard_quiz/{lowest_mastery['id']}"
            })
        
        # Recommendation 3: Study at optimal time
        best_time = self.data.get("preferences", {}).get("best_study_time")
        if best_time is not None:
            hour_now = datetime.datetime.now().hour
            hour_diff = (best_time - hour_now) % 24
            
            if 0 <= hour_diff <= 3:
                # Within 3 hours of optimal time
                recommendations.append({
                    "title": "Moment optimal pour étudier",
                    "description": f"C'est presque votre meilleure heure d'étude ({best_time}:00). Profitez-en !",
                    "action_text": "Voir les ensembles",
                    "action_url": "/flashcards"
                })
        
        # Recommendation 4: Maintain streak
        streak = self.data.get("study_streak", 0)
        last_study_date = self.data.get("last_study_date")
        
        if streak >= 2 and last_study_date:
            last_date = datetime.date.fromisoformat(last_study_date) if isinstance(last_study_date, str) else last_study_date
            today = datetime.date.today()
            
            if last_date < today:
                recommendations.append({
                    "title": f"Maintenez votre série d'étude de {streak} jours !",
                    "description": "Étudiez aujourd'hui pour ne pas perdre votre série.",
                    "action_text": "Étudier maintenant",
                    "action_url": "/flashcards"
                })
        
        # Recommendation 5: Try new set
        studied_set_ids = {session.get("set_id") for session in self.data["study_sessions"]}
        new_sets = [s for s in set_progress if s["id"] not in studied_set_ids]
        
        if new_sets:
            new_set = new_sets[0]
            recommendations.append({
                "title": f"Essayez un nouvel ensemble : {new_set['name']}",
                "description": f"Vous n'avez pas encore étudié cet ensemble de {new_set['card_count']} cartes.",
                "action_text": "Commencer",
                "action_url": f"/flashcard_quiz/{new_set['id']}"
            })
        
        return recommendations[:5]  # Return at most 5 recommendations