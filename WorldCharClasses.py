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
import os

from dotenv import load_dotenv
from openai import OpenAI
from pinecone.grpc import PineconeGRPC as Pinecone
from pydantic import BaseModel

load_dotenv()

pinecone_client = Pinecone(api_key=os.getenv("PINECONE_API_KEY"))
# warning: todo: different index from skylow-memories because this isn't chat memory, it's a simulation of "brain memory"
skylow_brainmemories_index = pinecone_client.Index("fire-ambulance-quick-setup")
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
embedding_model = "text-embedding-3-small"

class Memory(BaseModel):
    skylow_message: str
    user_message: str
    date: str

class Memories(BaseModel):
    memories: List[Memory]

class WorldDefinition:
    def __init__(
        self,
        name: str,
        description: str,
        locations: List[Dict[str, Any]] = None,
        global_events: List[Dict[str, Any]] = None,
        custom_parameters: Dict[str, Any] = None
    ):
        self.name = name
        self.description = description
        self.locations = locations or []
        self.global_events = global_events or []
        self.custom_parameters = custom_parameters or {}
        self.characters = {}
        self.current_date = datetime.datetime.now()

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

    # Function to get the weather for a specific location
    def get_weather(self, location_name: str) -> str:
        for location in self.locations:
            if location["name"] == location_name:
                return location["weather"]
        return "Location not found"

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
        # Initialize friendships for the new character
        character.initialize_friendships()
        # Update friendships for existing characters
        for existing_char in self.characters.values():
            if existing_char != character:
                existing_char.friends[character.character_name] = 0.0

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
        date_of_birth: datetime.date,        
        personality: Dict[str, float], #basic description would be something like {"hospitality":0.4, "ego": 0.9}
        timezone: str, # something like "-8" 
        location: str, 
        preferences: Dict[str, Any], #something like {"food": "sushi, taco bell", "climate": "rainy"}
        interests: List[str],
        goals: List[str],
        past_experiences: List[str],
        texting_style: str, # maybe "uses several emojis with no caps lock and frequent slang"
        character_description: str  # New parameter
    ):
        super().__init__(
            name=world.name,
            description=world.description,
            locations=world.locations,
            global_events=world.global_events,
            custom_parameters=world.custom_parameters
        )
        self.world = world
        self.character_name = name
        self.date_of_birth = date_of_birth        
        self.personality = personality
        self.timezone = int(timezone)
        self.location = location
        self.preferences = preferences
        self.interests = interests
        self.goals = goals
        self.past_experiences = past_experiences
        self.texting_style = texting_style
        self.character_description = character_description  # New attribute
        self.friends = {} 
        self.skills = {}
        self.is_jet_lagged = False
        self.jet_lag_recovery_date = None

    def get_embedding(self, text: str) -> list:
        text = text.replace("\n", " ")
        return openai_client.embeddings.create(input=[text], model=embedding_model).data[0].embedding

    def add_memory(self, user_message: str, is_user_memory: bool):
        prompt = f"Extract the most important information from this message in a concise format:\n\n{user_message}"
        sys_prompt = """You are an AI assistant that extracts key information from messages. Your task is to:

        1. Identify and extract only the most important and memorable information from the given message.
        2. Focus on facts, events, opinions, or emotions that might be significant for future interactions or understanding the context of a conversation.
        3. Ignore routine or trivial information such as simple greetings, small talk about the weather, or other non-consequential exchanges.
        4. Summarize the key information in a concise format, ideally in 20 words or less.
        5. If there is no significant information worth remembering, return an empty string.

        Examples:
        - Input: "Hi there! How are you doing today?"
        Output: "" (empty string, as this is just a greeting)
    
        - Input: "I just got a new job at Google as a software engineer! I'm starting next month."
        Output: "Got a new job as software engineer at Google, starting next month."
    
        - Input: "I'm feeling really upset because my dog passed away yesterday. He was with me for 15 years."
        Output: "Dog passed away yesterday after 15 years, feeling very upset."
    
        - Input: "Did you hear about the new policy? They're implementing work-from-home Fridays starting next week."
        Output: "New policy: work-from-home Fridays starting next week."

        Remember, if there's nothing significant to extract, return an empty string."""
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": sys_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        important_info = response.choices[0].message.content.strip()

        if important_info == '""':
            return

        date = datetime.datetime.now()
        date_string: str = date.strftime("%Y-%m-%dT%H:%M:%SZ")
        date_timestamp: int = int(date.timestamp())
        memory_embedding: list = self.get_embedding(important_info)

        vector = {
            "id": f"{self.character_name}#{date}",
            "values": memory_embedding,
            "metadata": {
                "character_name": self.character_name,
                "createdAt": date_string,
                "important_info": important_info,
                "timestamp": date_timestamp,
                "is_user_memory": is_user_memory, 
            },
        }
        skylow_brainmemories_index.upsert(vectors=[vector])

    def get_memories(self, query: str, k: int = 5) -> List[Dict[str, Any]]:
        query_embedding = self.get_embedding(query)
        response = skylow_brainmemories_index.query(
            vector=query_embedding,
            filter={"character_name": {"$eq": self.character_name}},
            top_k=k,
            include_values=False,
            include_metadata=True,
        )

        memory_list = []
        for match in response.matches:
            memory = {
                "is_user_memory": match.metadata["is_user_memory"],
                "important_info": match.metadata["important_info"],
                "date": match.metadata["createdAt"],
            }
            memory_list.append(memory)
        
        return memory_list

    # make the character move there, and remember it by storing it in current experience (so will be eventually forgotten)
    def move_to_location(self, location_name: str):
        location = next((loc for loc in self.world.locations if loc["name"] == location_name), None)
        if location:
            old_timezone = self.timezone
            self.location = location_name
            self.timezone = location["timezone"]
            self.add_memory(f"Moved to {location_name}.", is_user_memory=False)
           
            # Check for jet lag
            timezone_diff = abs(self.timezone - old_timezone)
            if timezone_diff >= 5:  # Jet lag if time difference is 5 or more hours
                recovery_days = min(timezone_diff // 2, 7)  # Max 7 days to recover
                self.is_jet_lagged = True
                self.jet_lag_recovery_date = self.world.current_date + datetime.timedelta(days=recovery_days)
                self.add_memory(f"Experiencing jet lag after moving to {location_name}. Expected to recover in {recovery_days} days.", is_user_memory=False)

    def get_age(self) -> int:
        today = self.world.current_date.date()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

    def is_birthday(self) -> bool:
        return (self.world.current_date.month, self.world.current_date.day) == (self.date_of_birth.month, self.date_of_birth.day)

    def celebrate_birthday(self):
        age = self.get_age()
        celebration = f"Celebrated {self.character_name}'s {age}th birthday!"
        self.add_memory(celebration, is_user_memory=False)
        
        for friend_name, friendship_level in self.friends.items():
            friend = self.world.characters.get(friend_name)
            if friend:
                friend.add_memory(f"It's {self.character_name}'s {age}th birthday today!", is_user_memory=False)
                friend.add_task_done(f"Wished {self.character_name} a happy birthday")
                # Increase friendship more for close friends
                friendship_increase = 0.05 * friendship_level
                self.update_friendship(friend_name, friendship_increase)
                friend.update_friendship(self.character_name, friendship_increase)
        
        birthday_tasks = self.generate_birthday_tasks()
        for task in birthday_tasks:
            self.add_task_done(task)

    def update_daily(self):
        if self.is_birthday():
            self.celebrate_birthday()
            
        if self.is_jet_lagged and self.world.current_date >= self.jet_lag_recovery_date:
            self.is_jet_lagged = False
            self.add_memory("Recovered from jet lag.", is_user_memory=False)

        day_summary = self.summarize_day()
        self.add_memory(day_summary, is_user_memory=False)
        
    def summarize_day(self) -> str:
        recent_memories = self.search_similar_memories(query="today's events", top_k=10)
        memory_text = "\n".join([f"User: {m['important_info']}" for m in recent_memories])
        
        prompt = f"Summarize the following events of the day for {self.character_name}:\n\n{memory_text}"
        
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
        )
        
        return response.choices[0].message.content        

    # may have to be implemented in a more advanced way    
    def develop_skill(self, skill_name: str, increase: float = 0.1):
        if skill_name not in self.skills:
            self.skills[skill_name] = 0
        self.skills[skill_name] = min(1.0, self.skills[skill_name] + increase)
        
    def add_task_done(self, task: str):
        self.add_memory(f"Task completed: {task}", is_user_memory=False)

    def recommend_task(self, task: str):
        # Use OpenAI to determine if the character accepts the task based on personality
        prompt = f"Given {self.character_name}'s personality: {self.personality}, would they accept the task: '{task}'? Respond with 'Yes' or 'No'."
        
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
        )
        
        if response.choices[0].message.content.strip().lower() == "yes":
            self.add_task_done(task)
            return True
        return False

    def initialize_friendships(self):
        for char_name in self.world.characters:
            if char_name != self.character_name:
                self.friends[char_name] = 0.0

    def update_friendship(self, friend_name: str, change: float):
        if friend_name != self.character_name:
            current_level = self.friends.get(friend_name, 0.0)
            new_level = max(0.0, min(1.0, current_level + change))
            self.friends[friend_name] = new_level
            self.add_memory(f"Friendship with {friend_name} changed to level {new_level:.2f}", is_user_memory=False)

    def get_friendship_level(self, friend_name: str) -> float:
        return self.friends.get(friend_name, 0.0)

    # based on talk from meet (user tells char1 hes going to monaco, char2 may only know too if friends with char1)
    def communicate(self, friend_name: str, message: str):
        friend = self.world.characters.get(friend_name)
        if friend:
            friend.receive_message(self.character_name, message)
            # Increase friendship slightly with each communication
            self.update_friendship(friend_name, 0.01)
            friend.update_friendship(self.character_name, 0.01)

    def receive_message(self, sender_name: str, message: str):
        summarized_message = self.summarize_message(message)
        experience = f"Received a message from {sender_name}: {summarized_message}"
        self.add_memory(experience, is_user_memory=False)

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

    def generate_birthday_tasks(self) -> List[str]:
        prompt = f"""
        Generate 3-5 special birthday tasks for {self.character_name} based on their personality and interests:
        Personality: {self.personality}
        Interests: {self.interests}
        Current location: {self.location}
        """
        
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
        )
        
        tasks = response.choices[0].message.content.split('\n')
        return [task.strip() for task in tasks if task.strip()]

    def summarize_message(self, message: str) -> str:
        if len(message) <= 100:
            return message
        
        prompt = f"Summarize the following message in 50 words or less:\n\n{message}"
        
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "system", "content": prompt}],
        )
        
        return response.choices[0].message.content.strip()

    def search_similar_memories(self, query: str, top_k: int = 3):
        query_embedding = self.get_embedding(query)
    
        response = skylow_brainmemories_index.query(
            vector=query_embedding,
            filter={"character_name": {"$eq": self.character_name}},
            top_k=top_k,
            include_values=False,
            include_metadata=True,
        )
    
        similar_memories = []
        for match in response.matches:
            memory = {
                "important_info": match.metadata["important_info"],
                "date": match.metadata["createdAt"],
            }
            similar_memories.append(memory)
    
        return similar_memories
