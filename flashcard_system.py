"""
Enhanced Flashcard System with Spaced Repetition
"""

import json
import datetime
import os
import math
import random
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

# Path for flashcard data
BASE_DIR = Path(os.path.dirname(os.path.abspath(__file__)))
FLASHCARDS_DIR = BASE_DIR / 'data' / 'flashcards'
os.makedirs(FLASHCARDS_DIR, exist_ok=True)
print(f"Flashcards directory: {FLASHCARDS_DIR}")

class SpacedRepetitionSystem:
    """
    Implements the SuperMemo-2 algorithm for spaced repetition
    """
    
    @staticmethod
    def calculate_next_review(ease_factor: float, interval: int, quality: int) -> Tuple[int, float]:
        """
        Calculate the next review interval based on performance
        
        Args:
            ease_factor: The ease factor of the card (starts at 2.5)
            interval: The current interval in days
            quality: The quality of the response (0-5)
                0-2: Incorrect response (hard)
                3: Correct response with difficulty (medium)
                4-5: Correct response (easy)
                
        Returns:
            Tuple of (new_interval, new_ease_factor)
        """
        if quality < 3:
            # If response was incorrect, reset interval to 1
            return 1, max(1.3, ease_factor - 0.2)
        
        # If first time or incorrect last time
        if interval == 0:
            new_interval = 1
        elif interval == 1:
            new_interval = 6
        else:
            new_interval = math.ceil(interval * ease_factor)
            
        # Adjust ease factor based on quality
        new_ease_factor = ease_factor + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        
        # Keep ease factor within reasonable bounds
        new_ease_factor = max(1.3, min(new_ease_factor, 2.5))
        
        return new_interval, new_ease_factor

class FlashcardManager:
    """Class to manage flashcards with spaced repetition"""
    
    def __init__(self, username: str):
        """
        Initialize the flashcard manager for a user
        
        Args:
            username: The username of the user
        """
        self.username = username
        self.user_dir = FLASHCARDS_DIR / username
        
        # Ensure the user directory exists
        try:
            os.makedirs(self.user_dir, exist_ok=True)
            print(f"Initialized flashcard manager for user: {username}")
            print(f"User directory: {self.user_dir}")
            print(f"User directory exists: {os.path.exists(self.user_dir)}")
        except Exception as e:
            print(f"Error creating user directory: {e}")
            import traceback
            traceback.print_exc()
        
    def create_set(self, name: str, subject: str, description: str = "") -> Dict[str, Any]:
        """
        Create a new flashcard set
        
        Args:
            name: The name of the set
            subject: The subject of the set
            description: Optional description
            
        Returns:
            Dict containing the created set information
        """
        # Generate a unique ID
        set_id = f"{int(datetime.datetime.now().timestamp())}"
        
        # Create the set data
        set_data = {
            "id": set_id,
            "name": name,
            "subject": subject,
            "description": description,
            "created_at": datetime.datetime.now().isoformat(),
            "updated_at": datetime.datetime.now().isoformat(),
            "cards": [],
            "stats": {
                "total_reviews": 0,
                "correct_reviews": 0,
                "incorrect_reviews": 0,
                "average_ease": 2.5
            }
        }
        
        # Save the set
        self._save_set(set_id, set_data)
        
        return set_data
        
    def save_set(self, set_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Save a complete flashcard set (used by AI assistant)
        
        Args:
            set_data: The complete set data to save
            
        Returns:
            Dict containing the saved set data
        """
        # Ensure the set has an ID
        if "id" not in set_data:
            set_data["id"] = f"{int(datetime.datetime.now().timestamp())}"
        
        # Ensure created_at and updated_at are present
        if "created_at" not in set_data:
            set_data["created_at"] = datetime.datetime.now().isoformat()
        
        if "updated_at" not in set_data:
            set_data["updated_at"] = datetime.datetime.now().isoformat()
        
        # Ensure stats are present
        if "stats" not in set_data:
            set_data["stats"] = {
                "total_reviews": 0,
                "correct_reviews": 0,
                "incorrect_reviews": 0,
                "average_ease": 2.5
            }
        
        # Save the set
        self._save_set(set_data["id"], set_data)
        
        return set_data
    
    def get_set(self, set_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a flashcard set by ID
        
        Args:
            set_id: The ID of the set
            
        Returns:
            Dict containing the set data or None if not found
        """
        set_file = self.user_dir / f"{set_id}.json"
        
        print(f"Looking for flashcard set at: {set_file}")
        print(f"User directory: {self.user_dir}")
        print(f"Set ID: {set_id}")
        
        if not set_file.exists():
            print(f"Flashcard set file does not exist: {set_file}")
            return None
        
        try:
            with open(set_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"Successfully loaded flashcard set: {set_id}")
                return data
        except Exception as e:
            print(f"Error loading flashcard set: {e}")
            # Print more detailed error information
            import traceback
            traceback.print_exc()
            return None
    
    def get_all_sets(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all flashcard sets for the user
        
        Returns:
            Dict mapping set_id to set data
        """
        sets = {}
        
        for set_file in self.user_dir.glob("*.json"):
            try:
                with open(set_file, 'r', encoding='utf-8') as f:
                    set_data = json.load(f)
                    # Add card count for convenience
                    set_data["card_count"] = len(set_data.get("cards", []))
                    sets[set_data.get("id")] = set_data
            except Exception as e:
                print(f"Error loading flashcard set {set_file}: {e}")
        
        return sets
        
    def get_all_sets_list(self) -> List[Dict[str, Any]]:
        """
        Get all flashcard sets for the user as a sorted list
        
        Returns:
            List of dicts containing set data, sorted by most recently updated
        """
        sets_dict = self.get_all_sets()
        sets_list = list(sets_dict.values())
        
        # Sort by most recently updated
        return sorted(sets_list, key=lambda x: x.get("updated_at", ""), reverse=True)
        
    def get_subjects(self) -> List[str]:
        """
        Get a list of all unique subjects used in flashcard sets
        
        Returns:
            List of unique subject names
        """
        sets_dict = self.get_all_sets()
        subjects = set()
        
        for set_data in sets_dict.values():
            subject = set_data.get("subject")
            if subject:
                subjects.add(subject)
        
        return sorted(list(subjects))
    
    def update_set(self, set_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a flashcard set
        
        Args:
            set_id: The ID of the set
            data: The data to update (can be partial)
            
        Returns:
            Dict containing the updated set data or None if not found
        """
        set_data = self.get_set(set_id)
        
        if not set_data:
            return None
        
        # Update fields
        for key, value in data.items():
            if key != "id" and key != "created_at":  # Don't allow changing ID or creation date
                set_data[key] = value
        
        # Update the updated_at timestamp
        set_data["updated_at"] = datetime.datetime.now().isoformat()
        
        # Save the updated set
        self._save_set(set_id, set_data)
        
        return set_data
    
    def delete_set(self, set_id: str) -> bool:
        """
        Delete a flashcard set
        
        Args:
            set_id: The ID of the set
            
        Returns:
            bool: True if deleted, False if not found
        """
        set_file = self.user_dir / f"{set_id}.json"
        
        if not set_file.exists():
            return False
        
        try:
            os.remove(set_file)
            return True
        except Exception as e:
            print(f"Error deleting flashcard set: {e}")
            return False
    
    def add_card(self, set_id: str, question: str, answer: str, 
                 image_url: str = None, audio_url: str = None, 
                 tags: List[str] = None) -> Optional[Dict[str, Any]]:
        """
        Add a card to a flashcard set
        
        Args:
            set_id: The ID of the set
            question: The question text
            answer: The answer text
            image_url: Optional URL to an image
            audio_url: Optional URL to audio
            tags: Optional list of tags
            
        Returns:
            Dict containing the updated set data or None if not found
        """
        set_data = self.get_set(set_id)
        
        if not set_data:
            return None
        
        # Create the card
        card = {
            "id": f"card_{len(set_data.get('cards', []))}_" + str(int(datetime.datetime.now().timestamp())),
            "question": question,
            "answer": answer,
            "created_at": datetime.datetime.now().isoformat(),
            "image_url": image_url,
            "audio_url": audio_url,
            "tags": tags or [],
            "learning_data": {
                "ease_factor": 2.5,
                "interval": 0,
                "reviews": 0,
                "last_review": None,
                "next_review": datetime.datetime.now().isoformat(),
                "history": []
            }
        }
        
        # Add the card to the set
        if "cards" not in set_data:
            set_data["cards"] = []
        
        set_data["cards"].append(card)
        
        # Update the updated_at timestamp
        set_data["updated_at"] = datetime.datetime.now().isoformat()
        
        # Save the updated set
        self._save_set(set_id, set_data)
        
        return set_data
    
    def update_card(self, set_id: str, card_id: str, data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update a card in a flashcard set
        
        Args:
            set_id: The ID of the set
            card_id: The ID of the card
            data: The data to update (can be partial)
            
        Returns:
            Dict containing the updated set data or None if not found
        """
        set_data = self.get_set(set_id)
        
        if not set_data or "cards" not in set_data:
            return None
        
        # Find the card
        for i, card in enumerate(set_data["cards"]):
            if card.get("id") == card_id:
                # Update fields
                for key, value in data.items():
                    if key != "id" and key != "created_at":  # Don't allow changing ID or creation date
                        card[key] = value
                
                # Update the card in the set
                set_data["cards"][i] = card
                
                # Update the updated_at timestamp
                set_data["updated_at"] = datetime.datetime.now().isoformat()
                
                # Save the updated set
                self._save_set(set_id, set_data)
                
                return set_data
        
        return None
    
    def delete_card(self, set_id: str, card_id: str) -> Optional[Dict[str, Any]]:
        """
        Delete a card from a flashcard set
        
        Args:
            set_id: The ID of the set
            card_id: The ID of the card
            
        Returns:
            Dict containing the updated set data or None if not found
        """
        set_data = self.get_set(set_id)
        
        if not set_data or "cards" not in set_data:
            return None
        
        # Find and remove the card
        for i, card in enumerate(set_data["cards"]):
            if card.get("id") == card_id:
                set_data["cards"].pop(i)
                
                # Update the updated_at timestamp
                set_data["updated_at"] = datetime.datetime.now().isoformat()
                
                # Save the updated set
                self._save_set(set_id, set_data)
                
                return set_data
        
        return None
    
    def get_due_cards(self, set_id: str, limit: int = None) -> List[Dict[str, Any]]:
        """
        Get cards that are due for review
        
        Args:
            set_id: The ID of the set
            limit: Optional limit on the number of cards to return
            
        Returns:
            List of cards due for review
        """
        set_data = self.get_set(set_id)
        
        if not set_data or "cards" not in set_data:
            return []
        
        now = datetime.datetime.now()
        due_cards = []
        
        for card in set_data["cards"]:
            if "learning_data" in card and "next_review" in card["learning_data"]:
                try:
                    next_review = datetime.datetime.fromisoformat(card["learning_data"]["next_review"])
                    if next_review <= now:
                        due_cards.append(card)
                except (ValueError, TypeError):
                    # If there's an error parsing the date, consider the card due
                    due_cards.append(card)
            else:
                # If learning data is not initialized, consider the card due
                due_cards.append(card)
        
        # Limit the number of cards if requested
        if limit is not None and limit > 0:
            due_cards = due_cards[:limit]
        
        return due_cards
    
    def record_review(self, set_id: str, card_id: str, quality: int) -> Optional[Dict[str, Any]]:
        """
        Record a review for a card
        
        Args:
            set_id: The ID of the set
            card_id: The ID of the card
            quality: The quality of the response (0-5)
                0-2: Incorrect response (hard)
                3: Correct response with difficulty (medium)
                4-5: Correct response (easy)
            
        Returns:
            Dict containing the updated set data or None if not found
        """
        set_data = self.get_set(set_id)
        
        if not set_data or "cards" not in set_data:
            return None
        
        # Find the card
        for i, card in enumerate(set_data["cards"]):
            if card.get("id") == card_id:
                # Initialize learning data if it doesn't exist
                if "learning_data" not in card:
                    card["learning_data"] = {
                        "ease_factor": 2.5,
                        "interval": 0,
                        "reviews": 0,
                        "last_review": None,
                        "next_review": datetime.datetime.now().isoformat(),
                        "history": []
                    }
                
                # Get current learning data
                learning_data = card["learning_data"]
                ease_factor = learning_data.get("ease_factor", 2.5)
                interval = learning_data.get("interval", 0)
                
                # Calculate new interval and ease factor
                new_interval, new_ease_factor = SpacedRepetitionSystem.calculate_next_review(
                    ease_factor, interval, quality
                )
                
                # Update learning data
                now = datetime.datetime.now()
                next_review = now + datetime.timedelta(days=new_interval)
                
                learning_data["ease_factor"] = new_ease_factor
                learning_data["interval"] = new_interval
                learning_data["reviews"] = learning_data.get("reviews", 0) + 1
                learning_data["last_review"] = now.isoformat()
                learning_data["next_review"] = next_review.isoformat()
                
                # Add to history
                if "history" not in learning_data:
                    learning_data["history"] = []
                
                learning_data["history"].append({
                    "date": now.isoformat(),
                    "quality": quality,
                    "ease_factor": new_ease_factor,
                    "interval": new_interval
                })
                
                # Limit history to last 100 entries
                if len(learning_data["history"]) > 100:
                    learning_data["history"] = learning_data["history"][-100:]
                
                # Update card in set
                card["learning_data"] = learning_data
                set_data["cards"][i] = card
                
                # Update set stats
                if "stats" not in set_data:
                    set_data["stats"] = {
                        "total_reviews": 0,
                        "correct_reviews": 0,
                        "incorrect_reviews": 0,
                        "average_ease": 2.5
                    }
                
                set_data["stats"]["total_reviews"] = set_data["stats"].get("total_reviews", 0) + 1
                
                if quality >= 3:
                    set_data["stats"]["correct_reviews"] = set_data["stats"].get("correct_reviews", 0) + 1
                else:
                    set_data["stats"]["incorrect_reviews"] = set_data["stats"].get("incorrect_reviews", 0) + 1
                
                # Calculate average ease factor
                total_ease = 0
                card_count = 0
                for card in set_data["cards"]:
                    if "learning_data" in card and "ease_factor" in card["learning_data"]:
                        total_ease += card["learning_data"]["ease_factor"]
                        card_count += 1
                
                if card_count > 0:
                    set_data["stats"]["average_ease"] = total_ease / card_count
                
                # Update the updated_at timestamp
                set_data["updated_at"] = datetime.datetime.now().isoformat()
                
                # Save the updated set
                self._save_set(set_id, set_data)
                
                return set_data
        
        return None
    
    def import_cards(self, set_id: str, cards_data: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Import multiple cards into a flashcard set
        
        Args:
            set_id: The ID of the set
            cards_data: List of card data dictionaries with at least question and answer fields
            
        Returns:
            Dict containing the updated set data or None if not found
        """
        set_data = self.get_set(set_id)
        
        if not set_data:
            return None
        
        # Initialize cards list if it doesn't exist
        if "cards" not in set_data:
            set_data["cards"] = []
        
        # Add each card
        for card_data in cards_data:
            if "question" in card_data and "answer" in card_data:
                # Create the card
                card = {
                    "id": f"card_{len(set_data['cards'])}_" + str(int(datetime.datetime.now().timestamp())),
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
                
                set_data["cards"].append(card)
        
        # Update the updated_at timestamp
        set_data["updated_at"] = datetime.datetime.now().isoformat()
        
        # Save the updated set
        self._save_set(set_id, set_data)
        
        return set_data
    
    def export_cards(self, set_id: str, format: str = "json") -> Optional[str]:
        """
        Export cards from a flashcard set
        
        Args:
            set_id: The ID of the set
            format: The export format ("json" or "csv")
            
        Returns:
            String containing the exported data or None if not found
        """
        set_data = self.get_set(set_id)
        
        if not set_data or "cards" not in set_data:
            return None
        
        if format.lower() == "json":
            # Export as JSON
            export_data = {
                "name": set_data.get("name", ""),
                "subject": set_data.get("subject", ""),
                "description": set_data.get("description", ""),
                "cards": []
            }
            
            for card in set_data["cards"]:
                export_data["cards"].append({
                    "question": card.get("question", ""),
                    "answer": card.get("answer", ""),
                    "image_url": card.get("image_url"),
                    "audio_url": card.get("audio_url"),
                    "tags": card.get("tags", [])
                })
            
            return json.dumps(export_data, indent=2)
        
        elif format.lower() == "csv":
            # Export as CSV
            csv_lines = ["Question,Answer,Tags"]
            
            for card in set_data["cards"]:
                question = card.get("question", "").replace('"', '""').replace(',', '","')
                answer = card.get("answer", "").replace('"', '""').replace(',', '","')
                tags = ",".join(card.get("tags", []))
                
                csv_lines.append(f'"{question}","{answer}","{tags}"')
            
            return "\n".join(csv_lines)
        
        return None
    
    def _save_set(self, set_id: str, data: Dict[str, Any]) -> None:
        """
        Save a flashcard set to file
        
        Args:
            set_id: The ID of the set
            data: The set data to save
        """
        set_file = self.user_dir / f"{set_id}.json"
        
        try:
            with open(set_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving flashcard set: {e}")
            
    def get_card(self, set_id: str, card_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific card from a flashcard set
        
        Args:
            set_id: The ID of the set
            card_id: The ID of the card
            
        Returns:
            Dict containing the card data or None if not found
        """
        set_data = self.get_set(set_id)
        
        if not set_data or "cards" not in set_data:
            return None
        
        # Find the card
        for card in set_data.get("cards", []):
            if card.get("id") == card_id:
                return card
        
        return None
        
    def get_cards(self, set_id: str) -> List[Dict[str, Any]]:
        """
        Get all cards from a flashcard set
        
        Args:
            set_id: The ID of the set
            
        Returns:
            List of cards in the set
        """
        set_data = self.get_set(set_id)
        
        if not set_data or "cards" not in set_data:
            return []
        
        return set_data.get("cards", [])
        
    def get_subjects(self) -> List[str]:
        """
        Get all unique subjects from the user's flashcard sets
        
        Returns:
            List of unique subjects
        """
        subjects = set()
        
        # Get all sets
        sets = self.get_all_sets()
        
        # Extract subjects
        for set_data in sets.values():
            subject = set_data.get("subject")
            if subject:
                subjects.add(subject)
        
        # Add some default subjects if none exist
        if not subjects:
            subjects = {"Mathematics", "Science", "History", "Languages", "Computer Science", "Other"}
        
        # Return sorted list
        return sorted(list(subjects))
        
    def _save_set(self, set_id: str, set_data: Dict[str, Any]) -> None:
        """
        Save a flashcard set to disk
        
        Args:
            set_id: The ID of the set
            set_data: The set data to save
        """
        set_file = self.user_dir / f"{set_id}.json"
        
        print(f"Saving flashcard set to: {set_file}")
        print(f"User directory: {self.user_dir}")
        print(f"Set ID: {set_id}")
        
        try:
            with open(set_file, 'w', encoding='utf-8') as f:
                json.dump(set_data, f, indent=2, ensure_ascii=False)
            print(f"Successfully saved flashcard set: {set_id}")
        except Exception as e:
            print(f"Error saving flashcard set: {e}")
            # Print more detailed error information
            import traceback
            traceback.print_exc()