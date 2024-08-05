"""
Ashutosh Sundresh (ashutoshsundresh@gmail.com)
2024-08-05
World and CharacterTemplate Class Definitions

Simulating a dynamic virtual environment where characters can interact, move between locations, and experience events over time.

"""

from typing import List, Dict, Any
import datetime
import pytz
import random

class WorldDefinition:
    def __init__(
        self,
        name: str,
        description: str,
        locations: List[Dict[str, Any]] = None,
        global_events: List[Dict[str, Any]] = None,
        relationships: Dict[str, Dict[str, str]] = None,
        custom_parameters: Dict[str, Any] = None
    ):
        self.name = name
        self.description = description
        self.locations = locations or []
        self.global_events = global_events or []
        self.relationships = relationships or {}
        self.custom_parameters = custom_parameters or {}
        self.characters = {}
        self.current_date = datetime.datetime.now()
        self.technologies = []

    # force advance time with days parameter
    def advance_time(self, days: int = 1):
        for _ in range(days):
            self.current_date += datetime.timedelta(days=1)
            self._update_weather()
            self._trigger_events()
            for character in self.characters.values():
                character.update_daily()

    def _update_weather(self):
        for location in self.locations:
            location["weather"] = random.choice(["Sunny", "Rainy", "Cloudy", "Stormy"])

    def _trigger_events(self):
        for event in self.global_events:
            if event["date"] == self.current_date.strftime("%Y-%m-%d"):
                print(f"Global Event Triggered: {event['name']} - {event['description']}")

    def add_location(self, name: str, description: str, coordinates: tuple, timezone: int):
        self.locations.append({
            "name": name,
            "description": description,
            "coordinates": coordinates,
            "weather": "Sunny",  # Default weather
            "timezone": timezone
        })

    def add_character(self, character):
        self.characters[character.character_name] = character
        character._sync_friends_with_world()

    # arguments are name of first character, name of second character, and type of relationship (eg. "friend" or "unfriend")
    def set_relationship(self, character1: str, character2: str, relationship: str):
        if character1 not in self.relationships:
            self.relationships[character1] = {}
        self.relationships[character1][character2] = relationship
        
        # Update friends list in individual character templates if the relationship is "friend"
        if relationship.lower() == "friend":
            if character1 in self.characters:
                self.characters[character1].add_friend(character2)
            if character2 in self.characters:
                self.characters[character2].add_friend(character1)
        elif relationship.lower() == "unfriend":
            if character1 in self.characters:
                self.characters[character1].remove_friend(character2)
            if character2 in self.characters:
                self.characters[character2].remove_friend(character1)

    def get_relationship(self, character1: str, character2: str) -> str:
        return self.relationships.get(character1, {}).get(character2, "unknown")

    # other custom parameters if necessary established as dictionary
    def set_custom_parameter(self, key: str, value: Any):
        self.custom_parameters[key] = value

    def get_custom_parameter(self, key: str) -> Any:
        return self.custom_parameters.get(key)

class CharacterTemplate(WorldDefinition):
    def __init__(
        self,
        world: WorldDefinition,
        name: str,
        personality: Dict[str, float], #basic description would be something like {"hospitality":0.4, "ego": 0.9}
        timezone: str, # something like "-8" 
        location: str, 
        preferences: Dict[str, Any], #something like {"food": "sushi, taco bell", "climate": "rainy"}
        interests: List[str],
        goals: List[str],
        past_experiences: List[str],
        texting_style: str # maybe "uses several emojis with no caps lock and frequent slang"
    ):
        super().__init__(
            name=world.name,
            description=world.description,
            locations=world.locations,
            global_events=world.global_events,
            relationships=world.relationships,
            custom_parameters=world.custom_parameters
        )
        self.world = world
        self.character_name = name
        self.personality = personality
        self.timezone = int(timezone)
        self.location = location
        self.preferences = preferences
        self.interests = interests
        self.goals = goals
        self.past_experiences = past_experiences
        self.texting_style = texting_style
        self.friends = []
        self.tasks_done_today = []
        self.user_can_recommend_tasks = True # set true by default
        self.skills = {}
        self.current_experiences = [] 
        self.is_jet_lagged = False
        self.jet_lag_recovery_date = None
        self._sync_friends_with_world()

    # make the character move there, and remember it by storing it in current experience (so will be eventually forgotten)
    def move_to_location(self, location_name: str):
        location = next((loc for loc in self.world.locations if loc["name"] == location_name), None)
        if location:
            old_timezone = self.timezone
            self.location = location_name
            self.timezone = location["timezone"]
            self.add_current_experience(f"Moved to {location_name}.")
           
            # Check for jet lag
            timezone_diff = abs(self.timezone - old_timezone)
            if timezone_diff >= 5:  # Jet lag if time difference is 5 or more hours
                recovery_days = min(timezone_diff // 2, 7)  # Max 7 days to recover
                self.is_jet_lagged = True
                self.jet_lag_recovery_date = self.world.current_date + datetime.timedelta(days=recovery_days)
                self.add_current_experience(f"Experiencing jet lag after moving to {location_name}. Expected to recover in {recovery_days} days.")

    def update_daily(self):
        # Check if jet lag has recovered
        if self.is_jet_lagged and self.world.current_date >= self.jet_lag_recovery_date:
            self.is_jet_lagged = False
            self.add_current_experience("Recovered from jet lag.")

        # Summarize and add tasks done today to current experiences
        if self.tasks_done_today:
            # to-do
            # use openai here to summarise all the tasks of the day and append to current experiences before clearing
            self.clear_tasks_done_today()

    # may have to be implemented in a more advanced way    
    def develop_skill(self, skill_name: str, increase: float = 0.1):
        if skill_name not in self.skills:
            self.skills[skill_name] = 0
        self.skills[skill_name] = min(1.0, self.skills[skill_name] + increase)

    def _sync_friends_with_world(self):
        self.friends = [
            char_name for char_name, relation in self.world.relationships.get(self.character_name, {}).items()
            if relation.lower() == "friend"
        ]

    def add_friend(self, friend_name: str):
        if friend_name not in self.friends and friend_name != self.character_name:
            self.friends.append(friend_name)
            self.world.set_relationship(self.character_name, friend_name, "friend")            

    # maybe if something happens in chat that changes this aspect of the universe
    def remove_friend(self, friend_name: str):
        if friend_name in self.friends:
            self.friends.remove(friend_name)
            self.world.set_relationship(self.character_name, friend_name, "unfriend")

    # based on talk from meet (user tells char1 hes going to monaco, char2 may only know too if friends with char1)
    def communicate(self, friend_name: str, message: str):
        if friend_name in self.friends:
            friend = self.world.characters.get(friend_name)
            if friend:
                friend.receive_message(self.character_name, message)

    def receive_message(self, sender_name: str, message: str):
        # to-do
        # maybe you'd want to use openai here to summarise the message first
        experience = f"Received a message from {sender_name}: {message}"
        self.add_current_experience(experience)

    def add_current_experience(self, experience: str):
        timestamp = self.world.current_date.strftime("%Y-%m-%d")
        self.current_experiences.append(f"[{timestamp}] {experience}")
        # Limit the number of current experiences to the last 10
        # possibly increase this when more current experience worthy things are happening consistently
        self.current_experiences = self.current_experiences[-10:]

    def add_user_shared_info(self, info: str):
        self.add_current_experience(f"User shared: {info}")

    def generate_random_event(self):
        # to-do
        # add some implementation with openai here
        # take into consideration entries in current_experience, past_experiences, goals and interests
        return

    def get_current_experiences(self) -> List[str]:
        return self.current_experiences

    def clear_current_experiences(self):
        self.current_experiences.clear()

    # you can use random event with this, or maybe some user recommendation
    def add_task_done(self, task: str):
        self.tasks_done_today.append(task)

    def clear_tasks_done_today(self):
        self.tasks_done_today.clear()

    def set_user_can_recommend_tasks(self, value: bool):
        self.user_can_recommend_tasks = value

    def recommend_task(self, task: str):
        if self.user_can_recommend_tasks:
            # maybe you'd want to use random module along with the character's personality to determine if it accepts
            # to-do: place if block here
            self.add_task_done(task)

    def get_local_time(self) -> datetime.datetime:
        return datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=self.timezone)))

    def update_personality(self, trait: str, value: float):
        self.personality[trait] = value

    def set_preference(self, key: str, value: Any):
        self.preferences[key] = value

    def add_interest(self, interest: str):
        self.interests.append(interest)

    def add_goal(self, goal: str):
        self.goals.append(goal)

    def add_past_experience(self, experience: str):
        self.past_experiences.append(experience)
