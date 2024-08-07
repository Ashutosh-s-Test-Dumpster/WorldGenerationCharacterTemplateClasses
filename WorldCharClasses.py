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

from openai import OpenAI
from pinecone.grpc import PineconeGRPC as Pinecone
from pydantic import BaseModel

pinecone_client = Pinecone(api_key=os.environ.get("***"))
# warning: use a different index because this isn't chat memory, it's a simulation of "brain memory"
skylow_memories_index = pinecone_client.Index("***")
openai_client = OpenAI(api_key=os.environ.get("***"))
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
        date_of_birth: datetime.date,        
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
        self.date_of_birth = date_of_birth        
        self.personality = personality
        self.timezone = int(timezone)
        self.location = location
        self.preferences = preferences
        self.interests = interests
        self.goals = goals
        self.past_experiences = past_experiences
        self.texting_style = texting_style
        self.friends = []
        self.skills = {}
        self.is_jet_lagged = False
        self.jet_lag_recovery_date = None
        self._sync_friends_with_world()

    def get_embedding(self, text: str) -> list:
        text = text.replace("\n", " ")
        return openai_client.embeddings.create(input=[text], model=embedding_model).data[0].embedding

    def add_memory(self, skylow_message: str, user_message: str):
        date = datetime.datetime.now()
        date_string: str = date.strftime("%Y-%m-%dT%H:%M:%SZ")
        date_timestamp: int = int(date.timestamp())
        memory_embedding: list = self.get_embedding(skylow_message + user_message)

        vector = {
            "id": f"{self.character_name}#{date}",
            "values": memory_embedding,
            "metadata": {
                "character_name": self.character_name,
                "createdAt": date_string,
                "skylow_message": skylow_message,
                "user_message": user_message,
                "timestamp": date_timestamp,
            },
        }
        skylow_memories_index.upsert(vectors=[vector])

    def get_memories(self, query: str, k: int = 5) -> Memories:
        query_embedding = self.get_embedding(query)
        response = skylow_memories_index.query(
            vector=query_embedding,
            filter={"character_name": {"$eq": self.character_name}},
            top_k=k,
            include_values=False,
            include_metadata=True,
        )

        memory_list = []
        for match in response.matches:
            memory = Memory(
                skylow_message=match.metadata["skylow_message"],
                user_message=match.metadata["user_message"],
                date=match.metadata["createdAt"],
            )
            memory_list.append(memory)
        
        return Memories(memories=memory_list)

    # make the character move there, and remember it by storing it in current experience (so will be eventually forgotten)
    def move_to_location(self, location_name: str):
        location = next((loc for loc in self.world.locations if loc["name"] == location_name), None)
        if location:
            old_timezone = self.timezone
            self.location = location_name
            self.timezone = location["timezone"]
            self.add_memory("System", f"Moved to {location_name}.")
           
            # Check for jet lag
            timezone_diff = abs(self.timezone - old_timezone)
            if timezone_diff >= 5:  # Jet lag if time difference is 5 or more hours
                recovery_days = min(timezone_diff // 2, 7)  # Max 7 days to recover
                self.is_jet_lagged = True
                self.jet_lag_recovery_date = self.world.current_date + datetime.timedelta(days=recovery_days)
                self.add_memory("System", f"Experiencing jet lag after moving to {location_name}. Expected to recover in {recovery_days} days.")

    def get_age(self) -> int:
        today = self.world.current_date.date()
        return today.year - self.date_of_birth.year - ((today.month, today.day) < (self.date_of_birth.month, self.date_of_birth.day))

    def is_birthday(self) -> bool:
        return (self.world.current_date.month, self.world.current_date.day) == (self.date_of_birth.month, self.date_of_birth.day)

    def celebrate_birthday(self):
        age = self.get_age()
        celebration = f"Celebrated {self.character_name}'s {age}th birthday!"
        self.add_memory("System", celebration)
        
        for friend_name in self.friends:
            friend = self.world.characters.get(friend_name)
            if friend:
                friend.add_memory("System", f"It's {self.character_name}'s {age}th birthday today!")
                friend.add_task_done(f"Wished {self.character_name} a happy birthday")
        
        birthday_tasks = self.generate_birthday_tasks()
        for task in birthday_tasks:
            self.add_task_done(task)

    def update_daily(self):
        if self.is_birthday():
            self.celebrate_birthday()
            
        if self.is_jet_lagged and self.world.current_date >= self.jet_lag_recovery_date:
            self.is_jet_lagged = False
            self.add_memory("System", "Recovered from jet lag.")

        day_summary = self.summarize_day()
        self.add_memory("System", day_summary)
        
    def summarize_day(self) -> str:
        recent_memories = self.get_memories(query="today's events", k=10)
        memory_text = "\n".join([f"Skylow: {m.skylow_message}\nUser: {m.user_message}" for m in recent_memories.memories])
        
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

    def _sync_friends_with_world(self):
        self.friends = [
            char_name for char_name, relation in self.world.relationships.get(self.character_name, {}).items()
            if relation.lower() == "friend"
        ]
        
    def add_task_done(self, task: str):
        self.add_memory("System", f"Task completed: {task}")

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
        summarized_message = self.summarize_message(message)
        experience = f"Received a message from {sender_name}: {summarized_message}"
        self.add_memory(sender_name, experience)

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
