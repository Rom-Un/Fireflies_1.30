"""
Gamification module for the Pronote Web App
"""

import json
import datetime
import os
import random
import math
from pathlib import Path
from typing import Dict, List, Any, Optional

# Path for gamification data
GAMIFICATION_DIR = Path('data/gamification')
os.makedirs(GAMIFICATION_DIR, exist_ok=True)

class GamificationSystem:
    """Class to handle gamification features"""
    
    def __init__(self, username: str):
        """
        Initialize the gamification system for a user
        
        Args:
            username: The username of the user
        """
        self.username = username
        self.data_file = GAMIFICATION_DIR / f"{username}.json"
        self.data = self._load_data()
        
    def _load_data(self) -> Dict[str, Any]:
        """
        Load gamification data from file

        Returns:
            Dict containing gamification data
        """
        if not self.data_file.exists():
            # Initialize with default data
            return {
                "points": 0,
                "xp": 0,
                "level": 1,
                "next_level_xp": 100,  # XP needed for next level
                "streak": {
                    "current": 0,
                    "max": 0,
                    "last_login": None,
                    "flame_level": 0,  # 0-5 flame level based on streak
                    "multiplier": 1.0  # Point multiplier based on streak
                },
                "achievements": [],
                "completed_homework": 0,
                "viewed_grades": 0,
                "checked_timetable": 0,
                "sent_messages": 0,
                "completed_flashcards": 0,  # New field for flashcard tracking
                "last_points_update": None,
                "activity_history": [],
                "badges": [],  # Special badges earned
                "inventory": {  # Virtual items earned
                    "boosters": [],
                    "avatars": ["default"],
                    "themes": ["default"]
                },
                "quests": {  # Daily and weekly quests
                    "daily": [],
                    "weekly": [],
                    "last_refresh": None
                },
                "stats": {  # Additional stats for achievements
                    "login_days": 0,
                    "perfect_weeks": 0,
                    "early_bird_logins": 0,
                    "night_owl_logins": 0
                }
            }
        
        try:
            with open(self.data_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading gamification data: {e}")
            return {
                "points": 0,
                "xp": 0,
                "level": 1,
                "next_level_xp": 100,  # XP needed for next level
                "streak": {
                    "current": 0,
                    "max": 0,
                    "last_login": None,
                    "flame_level": 0,  # 0-5 flame level based on streak
                    "multiplier": 1.0  # Point multiplier based on streak
                },
                "achievements": [],
                "completed_homework": 0,
                "viewed_grades": 0,
                "checked_timetable": 0,
                "sent_messages": 0,
                "last_points_update": None,
                "activity_history": [],
                "badges": [],  # Special badges earned
                "inventory": {  # Virtual items earned
                    "boosters": [],
                    "avatars": ["default"],
                    "themes": ["default"]
                },
                "quests": {  # Daily and weekly quests
                    "daily": [],
                    "weekly": [],
                    "last_refresh": None
                },
                "stats": {  # Additional stats for achievements
                    "login_days": 0,
                    "perfect_weeks": 0,
                    "early_bird_logins": 0,
                    "night_owl_logins": 0
                }
            }
    
    def _save_data(self) -> None:
        """Save gamification data to file"""
        try:
            with open(self.data_file, 'w') as f:
                json.dump(self.data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving gamification data: {e}")
    
    def update_login_streak(self) -> Dict[str, Any]:
        """
        Update login streak when user logs in
        
        Returns:
            Dict with streak information
        """
        today = datetime.date.today().isoformat()
        last_login = self.data["streak"]["last_login"]
        
        # If first login or login date is not set
        if not last_login:
            self.data["streak"]["current"] = 1
            self.data["streak"]["max"] = 1
            self.data["streak"]["last_login"] = today
            self.add_points(10, "Première connexion")
            self._save_data()
            return {
                "current": 1,
                "max": 1,
                "points_earned": 10,
                "message": "Bienvenue ! Vous avez gagné 10 points pour votre première connexion."
            }
        
        # Convert string date to datetime.date object
        last_login_date = datetime.date.fromisoformat(last_login)
        today_date = datetime.date.today()
        
        # If already logged in today
        if last_login_date == today_date:
            return {
                "current": self.data["streak"]["current"],
                "max": self.data["streak"]["max"],
                "points_earned": 0,
                "message": "Vous vous êtes déjà connecté aujourd'hui."
            }
        
        # If logged in yesterday, increment streak
        if (today_date - last_login_date).days == 1:
            self.data["streak"]["current"] += 1
            
            # Update max streak if current is higher
            if self.data["streak"]["current"] > self.data["streak"]["max"]:
                self.data["streak"]["max"] = self.data["streak"]["current"]
            
            # Update flame level based on streak
            self._update_flame_level()

            # Award points based on streak
            points_earned = min(50, 5 + (self.data["streak"]["current"] * 2))
            points_result = self.add_points(points_earned, f"Série de connexion: {self.data['streak']['current']} jours")

            # Check for streak achievements
            self._check_streak_achievements()

            self.data["streak"]["last_login"] = today

            # Update stats
            if "stats" not in self.data:
                self.data["stats"] = {"login_days": 0}
            if "login_days" not in self.data["stats"]:
                self.data["stats"]["login_days"] = 0
            self.data["stats"]["login_days"] += 1

            # Check if it's an early bird login (before 8 AM)
            current_hour = datetime.datetime.now().hour
            if current_hour < 8:
                if "early_bird_logins" not in self.data["stats"]:
                    self.data["stats"]["early_bird_logins"] = 0
                self.data["stats"]["early_bird_logins"] += 1

            # Check if it's a night owl login (after 10 PM)
            elif current_hour >= 22:
                if "night_owl_logins" not in self.data["stats"]:
                    self.data["stats"]["night_owl_logins"] = 0
                self.data["stats"]["night_owl_logins"] += 1

            # Generate daily quests if needed
            self._refresh_quests()

            self._save_data()

            # Prepare response
            flame_emoji = self._get_flame_emoji()

            return {
                "current": self.data["streak"]["current"],
                "max": self.data["streak"]["max"],
                "flame_level": self.data["streak"].get("flame_level", 0),
                "flame_emoji": flame_emoji,
                "multiplier": self.data["streak"].get("multiplier", 1.0),
                "points_earned": points_result["points_earned"],
                "xp_gained": points_result.get("xp_gained", 0),
                "level_up": points_result.get("level_up", {"leveled_up": False}),
                "message": f"Série: {self.data['streak']['current']} jours {flame_emoji} ! Vous avez gagné {points_result['points_earned']} points et {points_result.get('xp_gained', 0)} XP."
            }
        
        # If missed a day, reset streak
        else:
            # Check if streak shield is active
            shield_active = self._check_streak_shield()

            if shield_active:
                # Streak shield is active, don't reset streak
                self.data["streak"]["last_login"] = today
                points_result = self.add_points(10, "Connexion protégée par le Bouclier de Série")

                # Update flame level
                self._update_flame_level()

                # Generate daily quests if needed
                self._refresh_quests()

                self._save_data()

                flame_emoji = self._get_flame_emoji()

                return {
                    "current": self.data["streak"]["current"],
                    "max": self.data["streak"]["max"],
                    "flame_level": self.data["streak"].get("flame_level", 0),
                    "flame_emoji": flame_emoji,
                    "shield_used": True,
                    "points_earned": points_result["points_earned"],
                    "xp_gained": points_result.get("xp_gained", 0),
                    "message": f"Bouclier de Série utilisé ! Votre série de {self.data['streak']['current']} jours {flame_emoji} est préservée. Vous avez gagné {points_result['points_earned']} points."
                }
            else:
                # No shield, reset streak
                old_streak = self.data["streak"]["current"]
                self.data["streak"]["current"] = 1
                self.data["streak"]["last_login"] = today

                # Reset flame level and multiplier
                self.data["streak"]["flame_level"] = 0
                self.data["streak"]["multiplier"] = 1.0

                points_result = self.add_points(5, "Connexion après une pause")

                # Generate daily quests if needed
                self._refresh_quests()

                self._save_data()

                return {
                    "current": 1,
                    "max": self.data["streak"]["max"],
                    "flame_level": 0,
                    "flame_emoji": "",
                    "points_earned": points_result["points_earned"],
                    "xp_gained": points_result.get("xp_gained", 0),
                    "message": f"Bon retour ! Votre série a été réinitialisée (était {old_streak}). Vous avez gagné {points_result['points_earned']} points."
                }

    def add_points(self, points: int, reason: str) -> Dict[str, Any]:
        """
        Add points to the user's account

        Args:
            points: Number of points to add
            reason: Reason for adding points

        Returns:
            Dict with information about points and XP gained
        """
        # Apply streak multiplier if available
        multiplier = self.data["streak"].get("multiplier", 1.0)
        adjusted_points = int(points * multiplier)

        # Add points
        self.data["points"] += adjusted_points

        # Add XP (1 point = 5 XP)
        xp_gained = adjusted_points * 5
        if "xp" not in self.data:
            self.data["xp"] = 0
        self.data["xp"] += xp_gained

        # Add to activity history
        self.data["activity_history"].append({
            "date": datetime.datetime.now().isoformat(),
            "action": reason,
            "points": adjusted_points,
            "xp": xp_gained
        })

        # Limit history to last 100 entries
        if len(self.data["activity_history"]) > 100:
            self.data["activity_history"] = self.data["activity_history"][-100:]

        # Update level
        level_up_info = self._update_level()

        # Save changes
        self._save_data()

        return {
            "points_earned": adjusted_points,
            "xp_gained": xp_gained,
            "multiplier": multiplier,
            "level_up": level_up_info
        }
    
    def _update_level(self) -> Dict[str, Any]:
        """
        Update user level based on XP

        Returns:
            Dict with level up information
        """
        old_level = self.data["level"]

        # Initialize next_level_xp if it doesn't exist
        if "next_level_xp" not in self.data:
            self.data["next_level_xp"] = int(100 * (self.data["level"] ** 1.5))

        # Check if we have enough XP to level up
        while self.data.get("xp", 0) >= self.data["next_level_xp"]:
            self.data["level"] += 1

            # Calculate XP needed for next level (increases with each level)
            # Formula: 100 * (level^1.5)
            self.data["next_level_xp"] = int(100 * (self.data["level"] ** 1.5))

            # Award random booster on level up
            booster = self._award_random_booster()

            # Add level up to activity history
            self.data["activity_history"].append({
                "date": datetime.datetime.now().isoformat(),
                "action": f"Niveau supérieur ! {old_level} → {self.data['level']}",
                "points": 0,
                "xp": 0,
                "booster": booster["name"] if booster else None
            })

        # If level changed, return level up info
        if self.data["level"] > old_level:
            return {
                "leveled_up": True,
                "old_level": old_level,
                "new_level": self.data["level"],
                "booster": self._get_last_booster()
            }

        return {"leveled_up": False}

    def _award_random_booster(self) -> Optional[Dict[str, Any]]:
        """
        Award a random booster on level up

        Returns:
            Dict with booster information or None if inventory not initialized
        """
        boosters = [
            {"id": "double_xp", "name": "Double XP", "description": "Double XP pendant 1 jour", "duration": 1},
            {"id": "triple_points", "name": "Triple Points", "description": "Triple points pour les devoirs terminés", "duration": 1},
            {"id": "streak_shield", "name": "Bouclier de Série", "description": "Protège votre série pendant 1 jour si vous manquez une connexion", "duration": 1},
            {"id": "lucky_charm", "name": "Porte-Bonheur", "description": "Chance de gagner des points bonus pour chaque action", "duration": 1}
        ]

        booster = random.choice(boosters)
        booster["expires"] = (datetime.datetime.now() + datetime.timedelta(days=booster["duration"])).isoformat()

        # Initialize inventory if needed
        if "inventory" not in self.data:
            self.data["inventory"] = {"boosters": []}
        elif "boosters" not in self.data["inventory"]:
            self.data["inventory"]["boosters"] = []

        self.data["inventory"]["boosters"].append(booster)

        return booster

    def _get_last_booster(self) -> Optional[Dict[str, Any]]:
        """Get the most recently awarded booster"""
        if "inventory" in self.data and "boosters" in self.data["inventory"] and self.data["inventory"]["boosters"]:
            return self.data["inventory"]["boosters"][-1]
        return None
    
    def track_homework_completion(self) -> Dict[str, Any]:
        """
        Track when user completes homework
        
        Returns:
            Dict with points information
        """
        self.data["completed_homework"] += 1
        points_earned = 15
        
        # Bonus points for milestone completions
        milestone_bonus = 0
        milestone_message = ""

        if self.data["completed_homework"] in [5, 10, 25, 50, 100]:
            milestone_bonus = self.data["completed_homework"] * 2
            milestone_message = f"Étape : {self.data['completed_homework']} devoirs terminés ! Bonus : {milestone_bonus} points."

        total_points = points_earned + milestone_bonus
        self.add_points(total_points, f"Devoir terminé ({self.data['completed_homework']} au total)")

        # Check for homework achievements
        self._check_homework_achievements()

        return {
            "points_earned": total_points,
            "message": f"Vous avez gagné {points_earned} points pour avoir terminé un devoir." +
                      (f" {milestone_message}" if milestone_message else "")
        }
        
    def track_flashcard_completion(self, set_id: str, stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Track when user completes a flashcard study session
        
        Args:
            set_id: The ID of the flashcard set
            stats: Statistics about the study session
                - failed: Number of cards rated as failed
                - hard: Number of cards rated as hard
                - good: Number of cards rated as good
                - easy: Number of cards rated as easy
                - total: Total number of cards reviewed
                
        Returns:
            Dict with points information
        """
        # Initialize completed_flashcards if it doesn't exist
        if "completed_flashcards" not in self.data:
            self.data["completed_flashcards"] = 0
            
        # Initialize flashcard_stats if it doesn't exist
        if "flashcard_stats" not in self.data:
            self.data["flashcard_stats"] = {
                "total_reviews": 0,
                "correct_reviews": 0,
                "sets_studied": {},
                "study_sessions": 0,
                "perfect_sessions": 0,
                "study_streak": 0,
                "last_study_date": None
            }
            
        # Update flashcard stats
        self.data["completed_flashcards"] += 1
        self.data["flashcard_stats"]["total_reviews"] += stats.get("total", 0)
        self.data["flashcard_stats"]["correct_reviews"] += (stats.get("good", 0) + stats.get("easy", 0))
        self.data["flashcard_stats"]["study_sessions"] += 1
        
        # Check if this is a perfect session (all cards rated as good or easy)
        if stats.get("total", 0) > 0 and stats.get("failed", 0) == 0 and stats.get("hard", 0) == 0:
            self.data["flashcard_stats"]["perfect_sessions"] += 1
        
        # Update study streak
        today = datetime.date.today().isoformat()
        last_study_date = self.data["flashcard_stats"].get("last_study_date")
        
        if last_study_date:
            last_date = datetime.date.fromisoformat(last_study_date)
            today_date = datetime.date.today()
            
            if last_date == today_date:
                # Already studied today, no streak update
                pass
            elif (today_date - last_date).days == 1:
                # Studied yesterday, increment streak
                self.data["flashcard_stats"]["study_streak"] += 1
            else:
                # Missed a day, reset streak
                self.data["flashcard_stats"]["study_streak"] = 1
        else:
            # First study session
            self.data["flashcard_stats"]["study_streak"] = 1
            
        self.data["flashcard_stats"]["last_study_date"] = today
        
        # Track study for this specific set
        if set_id not in self.data["flashcard_stats"]["sets_studied"]:
            self.data["flashcard_stats"]["sets_studied"][set_id] = {
                "total_reviews": 0,
                "correct_reviews": 0,
                "study_sessions": 0,
                "last_study_date": None
            }
            
        self.data["flashcard_stats"]["sets_studied"][set_id]["total_reviews"] += stats.get("total", 0)
        self.data["flashcard_stats"]["sets_studied"][set_id]["correct_reviews"] += (stats.get("good", 0) + stats.get("easy", 0))
        self.data["flashcard_stats"]["sets_studied"][set_id]["study_sessions"] += 1
        self.data["flashcard_stats"]["sets_studied"][set_id]["last_study_date"] = today
        
        # Calculate points based on performance
        base_points = 10  # Base points for completing a study session
        performance_bonus = 0
        
        # Calculate performance percentage (correct / total)
        if stats.get("total", 0) > 0:
            correct_percentage = (stats.get("good", 0) + stats.get("easy", 0)) / stats.get("total", 0)
            
            # Bonus points based on performance
            if correct_percentage >= 0.9:
                performance_bonus = 15  # Excellent performance
            elif correct_percentage >= 0.7:
                performance_bonus = 10  # Good performance
            elif correct_percentage >= 0.5:
                performance_bonus = 5   # Average performance
        
        # Streak bonus
        streak_bonus = 0
        streak_message = ""
        
        if self.data["flashcard_stats"]["study_streak"] >= 5:
            streak_bonus = self.data["flashcard_stats"]["study_streak"]
            streak_message = f"Série d'étude de {self.data['flashcard_stats']['study_streak']} jours ! Bonus : {streak_bonus} points."
        
        # Milestone bonus
        milestone_bonus = 0
        milestone_message = ""
        
        if self.data["completed_flashcards"] in [5, 10, 25, 50, 100]:
            milestone_bonus = self.data["completed_flashcards"] * 2
            milestone_message = f"Étape : {self.data['completed_flashcards']} sessions d'étude terminées ! Bonus : {milestone_bonus} points."
        
        # Calculate total points
        total_points = base_points + performance_bonus + streak_bonus + milestone_bonus
        
        # Add points to user's account
        self.add_points(total_points, f"Session d'étude de cartes mémoire terminée ({stats.get('total', 0)} cartes)")
        
        # Check for flashcard achievements
        self._check_flashcard_achievements()
        
        # Save data
        self._save_data()
        
        return {
            "points_earned": total_points,
            "base_points": base_points,
            "performance_bonus": performance_bonus,
            "streak_bonus": streak_bonus,
            "milestone_bonus": milestone_bonus,
            "message": f"Vous avez gagné {total_points} points pour votre session d'étude !" +
                      (f" {streak_message}" if streak_message else "") +
                      (f" {milestone_message}" if milestone_message else "")
        }
    
    def track_grade_view(self) -> Dict[str, Any]:
        """
        Track when user views grades

        Returns:
            Dict with points information
        """
        # Only award points once per day
        today = datetime.date.today().isoformat()

        # Initialize last_points_update if it doesn't exist or is None
        if "last_points_update" not in self.data or self.data["last_points_update"] is None:
            self.data["last_points_update"] = {}

        # Get the last update date for viewed_grades
        last_update = self.data["last_points_update"].get("viewed_grades")

        if last_update == today:
            return {
                "points_earned": 0,
                "message": "Vous avez déjà gagné des points pour avoir consulté vos notes aujourd'hui."
            }

        self.data["viewed_grades"] += 1
        points_earned = 5

        self.data["last_points_update"]["viewed_grades"] = today
        self.add_points(points_earned, "Consultation des notes")

        # Check for grade view achievements
        self._check_grade_view_achievements()

        return {
            "points_earned": points_earned,
            "message": f"Vous avez gagné {points_earned} points pour avoir consulté vos notes."
        }
    
    def track_timetable_view(self) -> Dict[str, Any]:
        """
        Track when user views timetable

        Returns:
            Dict with points information
        """
        # Only award points once per day
        today = datetime.date.today().isoformat()

        # Initialize last_points_update if it doesn't exist or is None
        if "last_points_update" not in self.data or self.data["last_points_update"] is None:
            self.data["last_points_update"] = {}

        # Get the last update date for checked_timetable
        last_update = self.data["last_points_update"].get("checked_timetable")

        if last_update == today:
            return {
                "points_earned": 0,
                "message": "Vous avez déjà gagné des points pour avoir consulté votre emploi du temps aujourd'hui."
            }

        self.data["checked_timetable"] += 1
        points_earned = 5

        if not "last_points_update" in self.data:
            self.data["last_points_update"] = {}

        self.data["last_points_update"]["checked_timetable"] = today
        self.add_points(points_earned, "Consultation de l'emploi du temps")

        # Check for timetable achievements
        self._check_timetable_achievements()

        return {
            "points_earned": points_earned,
            "message": f"Vous avez gagné {points_earned} points pour avoir consulté votre emploi du temps."
        }
    
    def track_message_sent(self) -> Dict[str, Any]:
        """
        Track when user sends a message

        Returns:
            Dict with points information
        """
        self.data["sent_messages"] += 1
        points_earned = 10

        # Bonus points for milestone messages
        milestone_bonus = 0
        milestone_message = ""

        if self.data["sent_messages"] in [5, 10, 25, 50]:
            milestone_bonus = self.data["sent_messages"]
            milestone_message = f"Étape : {self.data['sent_messages']} messages envoyés ! Bonus : {milestone_bonus} points."

        total_points = points_earned + milestone_bonus
        self.add_points(total_points, f"Message envoyé ({self.data['sent_messages']} au total)")

        # Check for message achievements
        self._check_message_achievements()

        return {
            "points_earned": total_points,
            "message": f"Vous avez gagné {points_earned} points pour avoir envoyé un message." +
                      (f" {milestone_message}" if milestone_message else "")
        }

    def track_flashcard_completion(self) -> Dict[str, Any]:
        """
        Track when user completes a flashcard quiz

        Returns:
            Dict with points information
        """
        # Initialize if not exists
        if "completed_flashcards" not in self.data:
            self.data["completed_flashcards"] = 0

        self.data["completed_flashcards"] += 1
        points_earned = 20  # More points than homework as it requires active learning

        # Bonus points for milestone completions
        milestone_bonus = 0
        milestone_message = ""

        if self.data["completed_flashcards"] in [5, 10, 25, 50, 100]:
            milestone_bonus = self.data["completed_flashcards"] * 3
            milestone_message = f"Milestone: {self.data['completed_flashcards']} quizzes completed! Bonus: {milestone_bonus} points."

        total_points = points_earned + milestone_bonus
        self.add_points(total_points, f"Flashcard quiz completed ({self.data['completed_flashcards']} total)")

        # Check for flashcard achievements
        self._check_flashcard_achievements()

        return {
            "points_earned": total_points,
            "message": f"You earned {points_earned} points for completing a flashcard quiz." +
                      (f" {milestone_message}" if milestone_message else "")
        }
    
    def _check_streak_achievements(self) -> None:
        """Check and award streak-based achievements"""
        streak = self.data["streak"]["current"]
        achievements = self.data["achievements"]

        # Define streak achievements
        streak_achievements = [
            {"id": "streak_3", "name": "Série de 3 jours", "description": "Connexion pendant 3 jours consécutifs", "threshold": 3, "points": 20, "category": "streak"},
            {"id": "streak_7", "name": "Guerrier Hebdomadaire", "description": "Connexion pendant 7 jours consécutifs", "threshold": 7, "points": 50, "category": "streak"},
            {"id": "streak_14", "name": "Combattant de la Quinzaine", "description": "Connexion pendant 14 jours consécutifs", "threshold": 14, "points": 100, "category": "streak"},
            {"id": "streak_30", "name": "Maître du Mois", "description": "Connexion pendant 30 jours consécutifs", "threshold": 30, "points": 200, "category": "streak"},
            {"id": "streak_60", "name": "Guerrier Saisonnier", "description": "Connexion pendant 60 jours consécutifs", "threshold": 60, "points": 300, "category": "streak"},
            {"id": "streak_100", "name": "Légende de l'Assiduité", "description": "Connexion pendant 100 jours consécutifs", "threshold": 100, "points": 500, "category": "streak"},
        ]

        # Check each achievement
        for achievement in streak_achievements:
            if streak >= achievement["threshold"] and not any(a["id"] == achievement["id"] for a in achievements):
                # Award achievement
                achievement["date_earned"] = datetime.datetime.now().isoformat()
                self.data["achievements"].append(achievement)

                # Award points
                self.add_points(achievement["points"], f"Succès : {achievement['name']}")

                # Award badge for special achievements
                if achievement["threshold"] >= 30:
                    self._award_badge(achievement["id"], achievement["name"], achievement["description"])

    def _check_homework_achievements(self) -> None:
        """Check and award homework-based achievements"""
        completed = self.data["completed_homework"]
        achievements = self.data["achievements"]

        # Define homework achievements
        homework_achievements = [
            {"id": "hw_5", "name": "Débutant des Devoirs", "description": "Terminer 5 devoirs", "threshold": 5, "points": 25, "category": "homework"},
            {"id": "hw_20", "name": "Héros des Devoirs", "description": "Terminer 20 devoirs", "threshold": 20, "points": 75, "category": "homework"},
            {"id": "hw_50", "name": "Maître des Devoirs", "description": "Terminer 50 devoirs", "threshold": 50, "points": 150, "category": "homework"},
            {"id": "hw_100", "name": "Légende des Devoirs", "description": "Terminer 100 devoirs", "threshold": 100, "points": 300, "category": "homework"},
            {"id": "hw_200", "name": "Érudit des Devoirs", "description": "Terminer 200 devoirs", "threshold": 200, "points": 500, "category": "homework"},
        ]

        # Check each achievement
        for achievement in homework_achievements:
            if completed >= achievement["threshold"] and not any(a["id"] == achievement["id"] for a in achievements):
                # Award achievement
                achievement["date_earned"] = datetime.datetime.now().isoformat()
                self.data["achievements"].append(achievement)

                # Award points
                self.add_points(achievement["points"], f"Succès : {achievement['name']}")

                # Award badge for special achievements
                if achievement["threshold"] >= 50:
                    self._award_badge(achievement["id"], achievement["name"], achievement["description"])

    def _check_flashcard_achievements(self) -> None:
        """Check and award flashcard-based achievements"""
        completed = self.data.get("completed_flashcards", 0)
        achievements = self.data["achievements"]

        # Initialize flashcard_stats if it doesn't exist
        if "flashcard_stats" not in self.data:
            self.data["flashcard_stats"] = {
                "total_reviews": 0,
                "correct_reviews": 0,
                "sets_studied": {},
                "study_sessions": 0,
                "perfect_sessions": 0,
                "study_streak": 0,
                "last_study_date": None
            }
            
        # Get stats
        sessions_count = self.data["flashcard_stats"].get("study_sessions", 0)
        perfect_sessions = self.data["flashcard_stats"].get("perfect_sessions", 0)
        total_reviews = self.data["flashcard_stats"].get("total_reviews", 0)
        study_streak = self.data["flashcard_stats"].get("study_streak", 0)
        sets_studied = len(self.data["flashcard_stats"].get("sets_studied", {}))

        # Define flashcard achievements
        flashcard_achievements = [
            # Basic completion achievements
            {"id": "fc_5", "name": "Apprenti des Flashcards", "description": "Terminer 5 quiz de flashcards", "threshold": 5, "points": 30, "category": "flashcards", "stat": completed},
            {"id": "fc_20", "name": "Étudiant Assidu", "description": "Terminer 20 quiz de flashcards", "threshold": 20, "points": 80, "category": "flashcards", "stat": completed},
            {"id": "fc_50", "name": "Maître de la Mémorisation", "description": "Terminer 50 quiz de flashcards", "threshold": 50, "points": 200, "category": "flashcards", "stat": completed},
            {"id": "fc_100", "name": "Génie des Flashcards", "description": "Terminer 100 quiz de flashcards", "threshold": 100, "points": 350, "category": "flashcards", "stat": completed},
            {"id": "fc_200", "name": "Sage de la Connaissance", "description": "Terminer 200 quiz de flashcards", "threshold": 200, "points": 600, "category": "flashcards", "stat": completed},
            
            # Perfect session achievements
            {"id": "fc_perfect_5", "name": "Mémoire Photographique", "description": "Obtenir 5 sessions parfaites", "threshold": 5, "points": 50, "category": "flashcards_perfect", "stat": perfect_sessions},
            {"id": "fc_perfect_25", "name": "Mémoire d'Éléphant", "description": "Obtenir 25 sessions parfaites", "threshold": 25, "points": 150, "category": "flashcards_perfect", "stat": perfect_sessions},
            
            # Card review achievements
            {"id": "fc_reviews_100", "name": "Centenaire", "description": "Réviser 100 cartes", "threshold": 100, "points": 40, "category": "flashcards_reviews", "stat": total_reviews},
            {"id": "fc_reviews_500", "name": "Réviseur Assidu", "description": "Réviser 500 cartes", "threshold": 500, "points": 100, "category": "flashcards_reviews", "stat": total_reviews},
            {"id": "fc_reviews_1000", "name": "Maître de la Révision", "description": "Réviser 1000 cartes", "threshold": 1000, "points": 250, "category": "flashcards_reviews", "stat": total_reviews},
            
            # Study streak achievements
            {"id": "fc_streak_3", "name": "Habitude Naissante", "description": "Maintenir une série d'étude de 3 jours", "threshold": 3, "points": 25, "category": "flashcards_streak", "stat": study_streak},
            {"id": "fc_streak_7", "name": "Habitude Hebdomadaire", "description": "Maintenir une série d'étude de 7 jours", "threshold": 7, "points": 60, "category": "flashcards_streak", "stat": study_streak},
            {"id": "fc_streak_30", "name": "Habitude Mensuelle", "description": "Maintenir une série d'étude de 30 jours", "threshold": 30, "points": 200, "category": "flashcards_streak", "stat": study_streak},
            
            # Sets studied achievements
            {"id": "fc_sets_3", "name": "Explorateur", "description": "Étudier 3 ensembles de cartes différents", "threshold": 3, "points": 30, "category": "flashcards_sets", "stat": sets_studied},
            {"id": "fc_sets_10", "name": "Polymathe", "description": "Étudier 10 ensembles de cartes différents", "threshold": 10, "points": 80, "category": "flashcards_sets", "stat": sets_studied}
        ]

        # Check each achievement
        for achievement in flashcard_achievements:
            if achievement["stat"] >= achievement["threshold"] and not any(a["id"] == achievement["id"] for a in achievements):
                # Award achievement
                achievement["date_earned"] = datetime.datetime.now().isoformat()
                self.data["achievements"].append(achievement)

                # Award points
                self.add_points(achievement["points"], f"Succès : {achievement['name']}")

                # Award badge for special achievements
                if "flashcards_perfect" in achievement["category"] or "flashcards_streak" in achievement["category"] or achievement["threshold"] >= 50:
                    self._award_badge(achievement["id"], achievement["name"], achievement["description"])

    def _check_grade_view_achievements(self) -> None:
        """Check and award grade view-based achievements"""
        views = self.data["viewed_grades"]
        achievements = self.data["achievements"]

        # Define grade view achievements
        grade_achievements = [
            {"id": "grades_5", "name": "Observateur de Notes", "description": "Consulter ses notes 5 fois", "threshold": 5, "points": 20, "category": "grades"},
            {"id": "grades_15", "name": "Analyste de Notes", "description": "Consulter ses notes 15 fois", "threshold": 15, "points": 50, "category": "grades"},
            {"id": "grades_30", "name": "Expert en Notes", "description": "Consulter ses notes 30 fois", "threshold": 30, "points": 100, "category": "grades"},
            {"id": "grades_50", "name": "Maître des Notes", "description": "Consulter ses notes 50 fois", "threshold": 50, "points": 150, "category": "grades"},
        ]

        # Check each achievement
        for achievement in grade_achievements:
            if views >= achievement["threshold"] and not any(a["id"] == achievement["id"] for a in achievements):
                # Award achievement
                achievement["date_earned"] = datetime.datetime.now().isoformat()
                self.data["achievements"].append(achievement)

                # Award points
                self.add_points(achievement["points"], f"Succès : {achievement['name']}")

    def _check_timetable_achievements(self) -> None:
        """Check and award timetable view-based achievements"""
        views = self.data["checked_timetable"]
        achievements = self.data["achievements"]

        # Define timetable view achievements
        timetable_achievements = [
            {"id": "timetable_5", "name": "Planificateur Débutant", "description": "Consulter son emploi du temps 5 fois", "threshold": 5, "points": 20, "category": "timetable"},
            {"id": "timetable_15", "name": "Organisateur", "description": "Consulter son emploi du temps 15 fois", "threshold": 15, "points": 50, "category": "timetable"},
            {"id": "timetable_30", "name": "Maître du Temps", "description": "Consulter son emploi du temps 30 fois", "threshold": 30, "points": 100, "category": "timetable"},
            {"id": "timetable_50", "name": "Chronométreur Suprême", "description": "Consulter son emploi du temps 50 fois", "threshold": 50, "points": 150, "category": "timetable"},
        ]

        # Check each achievement
        for achievement in timetable_achievements:
            if views >= achievement["threshold"] and not any(a["id"] == achievement["id"] for a in achievements):
                # Award achievement
                achievement["date_earned"] = datetime.datetime.now().isoformat()
                self.data["achievements"].append(achievement)

                # Award points
                self.add_points(achievement["points"], f"Succès : {achievement['name']}")

    def _check_message_achievements(self) -> None:
        """Check and award message-based achievements"""
        messages = self.data["sent_messages"]
        achievements = self.data["achievements"]

        # Define message achievements
        message_achievements = [
            {"id": "msg_5", "name": "Communicateur Débutant", "description": "Envoyer 5 messages", "threshold": 5, "points": 25, "category": "messages"},
            {"id": "msg_15", "name": "Communicateur Actif", "description": "Envoyer 15 messages", "threshold": 15, "points": 50, "category": "messages"},
            {"id": "msg_30", "name": "Communicateur Expert", "description": "Envoyer 30 messages", "threshold": 30, "points": 100, "category": "messages"},
            {"id": "msg_50", "name": "Maître de la Communication", "description": "Envoyer 50 messages", "threshold": 50, "points": 150, "category": "messages"},
        ]

        # Check each achievement
        for achievement in message_achievements:
            if messages >= achievement["threshold"] and not any(a["id"] == achievement["id"] for a in achievements):
                # Award achievement
                achievement["date_earned"] = datetime.datetime.now().isoformat()
                self.data["achievements"].append(achievement)

                # Award points
                self.add_points(achievement["points"], f"Succès : {achievement['name']}")

                # Award badge for special achievements
                if achievement["threshold"] >= 30:
                    self._award_badge(achievement["id"], achievement["name"], achievement["description"])

    def _check_study_plan_achievements(self) -> None:
        """Check and award study plan-based achievements"""
        if "study_plans" not in self.data:
            return

        total_plans = len(self.data["study_plans"])
        completed_plans = len([p for p in self.data["study_plans"] if p.get("completed", False)])
        achievements = self.data["achievements"]

        # Define study plan achievements
        study_plan_achievements = [
            {"id": "plan_create_3", "name": "Planificateur Débutant", "description": "Créer 3 plans d'étude", "threshold": 3, "points": 30, "category": "study_plans", "check": total_plans},
            {"id": "plan_create_10", "name": "Planificateur Expert", "description": "Créer 10 plans d'étude", "threshold": 10, "points": 75, "category": "study_plans", "check": total_plans},
            {"id": "plan_complete_3", "name": "Étudiant Discipliné", "description": "Compléter 3 plans d'étude", "threshold": 3, "points": 50, "category": "study_plans", "check": completed_plans},
            {"id": "plan_complete_10", "name": "Maître de l'Étude", "description": "Compléter 10 plans d'étude", "threshold": 10, "points": 150, "category": "study_plans", "check": completed_plans},
        ]

        # Check each achievement
        for achievement in study_plan_achievements:
            check_value = achievement["check"]
            if check_value >= achievement["threshold"] and not any(a["id"] == achievement["id"] for a in achievements):
                # Award achievement
                achievement["date_earned"] = datetime.datetime.now().isoformat()
                self.data["achievements"].append(achievement)

                # Award points
                self.add_points(achievement["points"], f"Succès : {achievement['name']}")

                # Award badge for completing 10 study plans
                if achievement["id"] == "plan_complete_10":
                    self._award_badge(achievement["id"], achievement["name"], achievement["description"])

    def _award_badge(self, badge_id: str, name: str, description: str) -> None:
        """Award a badge to the user"""
        if "badges" not in self.data:
            self.data["badges"] = []

        # Check if badge already exists
        if any(b["id"] == badge_id for b in self.data["badges"]):
            return

        # Create badge with additional properties
        badge = {
            "id": badge_id,
            "name": name,
            "description": description,
            "date_earned": datetime.datetime.now().isoformat(),
            "icon": self._get_badge_icon(badge_id),
            "rarity": self._get_badge_rarity(badge_id)
        }

        # Add badge
        self.data["badges"].append(badge)

        # Add to activity history
        self.data["activity_history"].append({
            "date": datetime.datetime.now().isoformat(),
            "action": f"Badge obtenu : {name}",
            "points": 0,
            "xp": 50  # Award XP for badges
        })

        # Add XP
        if "xp" not in self.data:
            self.data["xp"] = 0
        self.data["xp"] += 50

        # Update level
        self._update_level()

        # Award special reward for certain badges
        self._award_badge_reward(badge_id)

    def _get_badge_icon(self, badge_id: str) -> str:
        """Get the appropriate icon for a badge"""
        if badge_id.startswith("streak"):
            return "🔥"
        elif badge_id.startswith("hw"):
            return "📚"
        elif badge_id.startswith("msg"):
            return "💬"
        elif badge_id.startswith("plan"):
            return "📝"
        else:
            return "🏆"

    def _get_badge_rarity(self, badge_id: str) -> str:
        """Get the rarity of a badge"""
        if badge_id in ["streak_100", "hw_200", "plan_complete_10"]:
            return "legendary"
        elif badge_id in ["streak_60", "hw_100", "msg_50"]:
            return "epic"
        elif badge_id in ["streak_30", "hw_50", "msg_30"]:
            return "rare"
        else:
            return "common"

    def _award_badge_reward(self, badge_id: str) -> None:
        """Award special rewards for certain badges"""
        rewards = {
            "streak_30": {"type": "avatar", "id": "flame_master", "name": "Maître des Flammes"},
            "streak_60": {"type": "theme", "id": "dark_flame", "name": "Flamme Sombre"},
            "streak_100": {"type": "booster", "id": "permanent_shield", "name": "Bouclier Permanent",
                          "description": "Protège votre série une fois par semaine", "duration": 365},
            "hw_50": {"type": "avatar", "id": "homework_master", "name": "Maître des Devoirs"},
            "hw_100": {"type": "theme", "id": "scholar", "name": "Érudit"},
            "hw_200": {"type": "booster", "id": "double_points", "name": "Points Doublés",
                      "description": "Double les points pour tous les devoirs pendant 7 jours", "duration": 7},
            "msg_30": {"type": "avatar", "id": "communicator", "name": "Communicateur"},
            "msg_50": {"type": "theme", "id": "social", "name": "Social"},
            "plan_complete_10": {"type": "booster", "id": "study_master", "name": "Maître de l'Étude",
                               "description": "Triple XP pour les exercices de plan d'étude pendant 7 jours", "duration": 7}
        }

        if badge_id not in rewards:
            return

        reward = rewards[badge_id]

        # Initialize inventory if needed
        if "inventory" not in self.data:
            self.data["inventory"] = {"boosters": [], "avatars": ["default"], "themes": ["default"]}

        # Award the reward based on type
        if reward["type"] == "avatar":
            if "avatars" not in self.data["inventory"]:
                self.data["inventory"]["avatars"] = ["default"]
            if reward["id"] not in self.data["inventory"]["avatars"]:
                self.data["inventory"]["avatars"].append(reward["id"])

                # Add to activity history
                self.data["activity_history"].append({
                    "date": datetime.datetime.now().isoformat(),
                    "action": f"Avatar débloqué : {reward['name']}",
                    "points": 0,
                    "xp": 0
                })

        elif reward["type"] == "theme":
            if "themes" not in self.data["inventory"]:
                self.data["inventory"]["themes"] = ["default"]
            if reward["id"] not in self.data["inventory"]["themes"]:
                self.data["inventory"]["themes"].append(reward["id"])

                # Add to activity history
                self.data["activity_history"].append({
                    "date": datetime.datetime.now().isoformat(),
                    "action": f"Thème débloqué : {reward['name']}",
                    "points": 0,
                    "xp": 0
                })

        elif reward["type"] == "booster":
            if "boosters" not in self.data["inventory"]:
                self.data["inventory"]["boosters"] = []

            # Create booster
            booster = {
                "id": reward["id"],
                "name": reward["name"],
                "description": reward["description"],
                "duration": reward["duration"],
                "expires": (datetime.datetime.now() + datetime.timedelta(days=reward["duration"])).isoformat()
            }

            self.data["inventory"]["boosters"].append(booster)

            # Add to activity history
            self.data["activity_history"].append({
                "date": datetime.datetime.now().isoformat(),
                "action": f"Booster débloqué : {reward['name']}",
                "points": 0,
                "xp": 0
            })

    def _update_flame_level(self) -> None:
        """Update flame level based on streak"""
        streak = self.data["streak"]["current"]

        # Initialize flame level if it doesn't exist
        if "flame_level" not in self.data["streak"]:
            self.data["streak"]["flame_level"] = 0

        # Initialize multiplier if it doesn't exist
        if "multiplier" not in self.data["streak"]:
            self.data["streak"]["multiplier"] = 1.0

        # Update flame level based on streak
        if streak >= 30:
            self.data["streak"]["flame_level"] = 5  # Max flame
            self.data["streak"]["multiplier"] = 2.0  # 2x multiplier
        elif streak >= 21:
            self.data["streak"]["flame_level"] = 4
            self.data["streak"]["multiplier"] = 1.8
        elif streak >= 14:
            self.data["streak"]["flame_level"] = 3
            self.data["streak"]["multiplier"] = 1.5
        elif streak >= 7:
            self.data["streak"]["flame_level"] = 2
            self.data["streak"]["multiplier"] = 1.3
        elif streak >= 3:
            self.data["streak"]["flame_level"] = 1
            self.data["streak"]["multiplier"] = 1.1
        else:
            self.data["streak"]["flame_level"] = 0
            self.data["streak"]["multiplier"] = 1.0

    def _get_flame_emoji(self) -> str:
        """Get flame emoji based on flame level"""
        flame_level = self.data["streak"].get("flame_level", 0)

        if flame_level == 5:
            return "🔥🔥🔥🔥🔥"  # Max flame
        elif flame_level == 4:
            return "🔥🔥🔥🔥"
        elif flame_level == 3:
            return "🔥🔥🔥"
        elif flame_level == 2:
            return "🔥🔥"
        elif flame_level == 1:
            return "🔥"
        else:
            return ""

    def _check_streak_shield(self) -> bool:
        """
        Check if user has an active streak shield

        Returns:
            True if shield is active and used, False otherwise
        """
        if "inventory" not in self.data or "boosters" not in self.data["inventory"]:
            return False

        now = datetime.datetime.now()

        # Check for active streak shield
        for i, booster in enumerate(self.data["inventory"]["boosters"]):
            if booster["id"] == "streak_shield":
                # Check if it's still valid
                expires = datetime.datetime.fromisoformat(booster["expires"])
                if expires > now:
                    # Use the shield and remove it
                    self.data["inventory"]["boosters"].pop(i)

                    # Add to activity history
                    self.data["activity_history"].append({
                        "date": now.isoformat(),
                        "action": "Bouclier de Série utilisé",
                        "points": 0,
                        "xp": 0
                    })

                    return True

        return False

    def _refresh_quests(self) -> None:
        """Refresh daily and weekly quests if needed"""
        today = datetime.date.today()

        # Initialize quests if needed
        if "quests" not in self.data:
            self.data["quests"] = {
                "daily": [],
                "weekly": [],
                "last_refresh": None
            }

        last_refresh = self.data["quests"].get("last_refresh")

        # If never refreshed or last refresh was not today
        if not last_refresh or datetime.date.fromisoformat(last_refresh) < today:
            # Generate new daily quests
            self.data["quests"]["daily"] = self._generate_daily_quests()
            self.data["quests"]["last_refresh"] = today.isoformat()

            # Check if we need to refresh weekly quests (Monday)
            if not last_refresh or today.weekday() == 0 and datetime.date.fromisoformat(last_refresh).weekday() != 0:
                self.data["quests"]["weekly"] = self._generate_weekly_quests()

    def _generate_daily_quests(self) -> List[Dict[str, Any]]:
        """Generate random daily quests"""
        possible_quests = [
            {"id": "login", "name": "Connexion Quotidienne", "description": "Connectez-vous aujourd'hui", "xp": 20, "completed": True},
            {"id": "check_grades", "name": "Vérifier les Notes", "description": "Consultez vos notes aujourd'hui", "xp": 30, "completed": False},
            {"id": "check_timetable", "name": "Vérifier l'Emploi du Temps", "description": "Consultez votre emploi du temps aujourd'hui", "xp": 30, "completed": False},
            {"id": "complete_homework", "name": "Terminer un Devoir", "description": "Marquez un devoir comme terminé", "xp": 50, "completed": False},
            {"id": "send_message", "name": "Envoyer un Message", "description": "Envoyez un message à un enseignant ou camarade", "xp": 40, "completed": False}
        ]

        # Always include login quest and 2 random others
        quests = [possible_quests[0]]
        quests.extend(random.sample(possible_quests[1:], 2))

        return quests

    def _generate_weekly_quests(self) -> List[Dict[str, Any]]:
        """Generate random weekly quests"""
        possible_quests = [
            {"id": "login_streak_5", "name": "Série de 5 Jours", "description": "Connectez-vous 5 jours cette semaine", "target": 5, "progress": 0, "xp": 100, "completed": False},
            {"id": "complete_5_homework", "name": "5 Devoirs", "description": "Terminez 5 devoirs cette semaine", "target": 5, "progress": 0, "xp": 150, "completed": False},
            {"id": "check_grades_3", "name": "Vérifier les Notes 3 Fois", "description": "Consultez vos notes 3 jours différents", "target": 3, "progress": 0, "xp": 80, "completed": False},
            {"id": "send_3_messages", "name": "Envoyer 3 Messages", "description": "Envoyez 3 messages cette semaine", "target": 3, "progress": 0, "xp": 120, "completed": False}
        ]

        # Select 3 random weekly quests
        return random.sample(possible_quests, 3)

    def get_stats(self) -> Dict[str, Any]:
        """
        Get user's gamification stats

        Returns:
            Dict with user stats
        """
        # Ensure we have all the required fields
        if "xp" not in self.data:
            self.data["xp"] = 0

        if "next_level_xp" not in self.data:
            self.data["next_level_xp"] = int(100 * (self.data["level"] ** 1.5))

        if "flame_level" not in self.data["streak"]:
            self._update_flame_level()

        # Initialize badges if needed
        if "badges" not in self.data:
            self.data["badges"] = []

        # Get active boosters
        active_boosters = []
        if "inventory" in self.data and "boosters" in self.data["inventory"]:
            now = datetime.datetime.now()
            for booster in self.data["inventory"]["boosters"]:
                expires = datetime.datetime.fromisoformat(booster["expires"])
                if expires > now:
                    active_boosters.append(booster)

        # Get quests
        quests = self.data.get("quests", {"daily": [], "weekly": []})

        # Ensure study_plans exists
        if "study_plans" not in self.data:
            self.data["study_plans"] = []

        # Get available avatars and themes
        avatars = self.data.get("inventory", {}).get("avatars", ["default"])
        themes = self.data.get("inventory", {}).get("themes", ["default"])

        return {
            "points": self.data["points"],
            "xp": self.data["xp"],
            "level": self.data["level"],
            "next_level_xp": self.data["next_level_xp"],
            "xp_progress": min(100, int((self.data["xp"] / self.data["next_level_xp"]) * 100)),
            "streak": {
                "current": self.data["streak"]["current"],
                "max": self.data["streak"]["max"],
                "flame_level": self.data["streak"].get("flame_level", 0),
                "flame_emoji": self._get_flame_emoji(),
                "multiplier": self.data["streak"].get("multiplier", 1.0)
            },
            "achievements": {
                "total": len(self.data["achievements"]),
                "recent": self.data["achievements"][-3:] if self.data["achievements"] else []
            },
            "badges": {
                "total": len(self.data["badges"]),
                "recent": self.data["badges"][-3:] if self.data["badges"] else [],
                "all": self.data["badges"]
            },
            "activity": {
                "completed_homework": self.data["completed_homework"],
                "viewed_grades": self.data["viewed_grades"],
                "checked_timetable": self.data["checked_timetable"],
                "sent_messages": self.data["sent_messages"]
            },
            "recent_activity": self.data["activity_history"][-5:] if self.data["activity_history"] else [],
            "boosters": active_boosters,
            "quests": quests,
            "inventory": {
                "avatars": avatars,
                "themes": themes
            },
            "study_plans": {
                "total": len(self.data.get("study_plans", [])),
                "active": len([p for p in self.data.get("study_plans", []) if not p.get("completed", False)]),
                "completed": len([p for p in self.data.get("study_plans", []) if p.get("completed", False)]),
                "upcoming_tests": sorted(
                    [p for p in self.data.get("study_plans", [])
                     if not p.get("completed", False) and
                     datetime.date.fromisoformat(p.get("test_date")) >= datetime.date.today()],
                    key=lambda x: x.get("test_date")
                )[:3]  # Get the next 3 upcoming tests
            }
        }
    
    def get_achievements(self) -> List[Dict[str, Any]]:
        """
        Get user's achievements

        Returns:
            List of achievements
        """
        return self.data["achievements"]

    def get_badges(self) -> List[Dict[str, Any]]:
        """
        Get user's badges

        Returns:
            List of badges
        """
        if "badges" not in self.data:
            self.data["badges"] = []
        return self.data["badges"]

    def get_activity_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """
        Get user's activity history

        Args:
            limit: Maximum number of entries to return

        Returns:
            List of activity entries
        """
        return self.data["activity_history"][-limit:] if self.data["activity_history"] else []
    
    def get_leaderboard(self, top_n: int = 10) -> List[Dict[str, Any]]:
        """
        Get leaderboard of top users
        
        Args:
            top_n: Number of top users to return
            
        Returns:
            List of top users
        """
        leaderboard = []
        
        # Get all user files
        for file in GAMIFICATION_DIR.glob("*.json"):
            try:
                with open(file, 'r') as f:
                    user_data = json.load(f)
                    username = file.stem
                    
                    leaderboard.append({
                        "username": username,
                        "points": user_data.get("points", 0),
                        "xp": user_data.get("xp", 0),
                        "level": user_data.get("level", 1),
                        "streak": user_data.get("streak", {}).get("current", 0),
                        "flame_level": user_data.get("streak", {}).get("flame_level", 0)
                    })
            except Exception as e:
                print(f"Error loading leaderboard data for {file}: {e}")
        
        # Sort by level first, then by XP (descending)
        leaderboard.sort(key=lambda x: (x["level"], x["xp"]), reverse=True)
        
        # Return top N
        return leaderboard[:top_n]

    def create_study_plan(self, test_name: str, test_date: str, subject: str, num_exercises: int) -> Dict[str, Any]:
        """
        Create a new study plan for an upcoming test

        Args:
            test_name: Name of the test
            test_date: Date of the test (YYYY-MM-DD)
            subject: Subject of the test
            num_exercises: Number of exercises to complete before the test

        Returns:
            Dict with the created study plan
        """
        # Initialize study_plans if it doesn't exist
        if "study_plans" not in self.data:
            self.data["study_plans"] = []

        # Also initialize in both default data structures
        # This ensures it's always available for new users

        # Generate a unique ID for the study plan
        plan_id = f"plan_{len(self.data['study_plans']) + 1}_{int(datetime.datetime.now().timestamp())}"

        # Create the study plan
        study_plan = {
            "id": plan_id,
            "test_name": test_name,
            "test_date": test_date,
            "subject": subject,
            "num_exercises": num_exercises,
            "exercises_completed": 0,
            "last_exercise_date": None,
            "completed": False,
            "created_at": datetime.datetime.now().isoformat()
        }

        # Add to study plans
        self.data["study_plans"].append(study_plan)

        # Save data
        self._save_data()

        # Award points for creating a study plan
        self.add_points(10, f"Plan d'étude créé pour {test_name}")

        # Check for study plan achievements
        self._check_study_plan_achievements()

        return study_plan

    def track_exercise_completion(self, plan_id: str) -> Dict[str, Any]:
        """
        Track completion of an exercise for a study plan

        Args:
            plan_id: ID of the study plan

        Returns:
            Dict with updated study plan and points information
        """
        # Initialize study_plans if it doesn't exist
        if "study_plans" not in self.data:
            self.data["study_plans"] = []
            return {"success": False, "message": "Plan d'étude non trouvé"}

        # Find the study plan
        study_plan = None
        for plan in self.data["study_plans"]:
            if plan["id"] == plan_id:
                study_plan = plan
                break

        if not study_plan:
            return {"success": False, "message": "Plan d'étude non trouvé"}

        # Check if already completed today
        today = datetime.date.today().isoformat()
        if study_plan.get("last_exercise_date") == today:
            return {
                "success": True,
                "message": "Vous avez déjà complété un exercice aujourd'hui pour ce plan",
                "study_plan": study_plan,
                "points_earned": 0
            }

        # Update the study plan
        study_plan["exercises_completed"] += 1
        study_plan["last_exercise_date"] = today

        # Check if all exercises are completed
        if study_plan["exercises_completed"] >= study_plan["num_exercises"]:
            study_plan["completed"] = True

        # Save data
        self._save_data()

        # Award points
        points_earned = 15
        message = f"Exercice complété pour {study_plan['test_name']}"

        # Bonus points if completed all exercises
        if study_plan["completed"]:
            bonus_points = 25
            points_earned += bonus_points
            message += f" (Plan complété ! +{bonus_points} points bonus)"

        self.add_points(points_earned, message)

        # Check for study plan achievements if plan was completed
        if study_plan["completed"]:
            self._check_study_plan_achievements()

        return {
            "success": True,
            "message": message,
            "study_plan": study_plan,
            "points_earned": points_earned
        }

    def get_study_plans(self) -> List[Dict[str, Any]]:
        """
        Get all study plans

        Returns:
            List of study plans
        """
        if "study_plans" not in self.data:
            self.data["study_plans"] = []

        # Sort by test date (ascending)
        return sorted(self.data["study_plans"], key=lambda x: x["test_date"])

    def delete_study_plan(self, plan_id: str) -> Dict[str, Any]:
        """
        Delete a study plan

        Args:
            plan_id: ID of the study plan

        Returns:
            Dict with success status
        """
        if "study_plans" not in self.data:
            return {"success": False, "message": "Plan d'étude non trouvé"}

        # Find the study plan
        for i, plan in enumerate(self.data["study_plans"]):
            if plan["id"] == plan_id:
                # Remove the plan
                self.data["study_plans"].pop(i)
                self._save_data()
                return {"success": True, "message": "Plan d'étude supprimé"}

        return {"success": False, "message": "Plan d'étude non trouvé"}