import streamlit as st
import datetime
import os
from dotenv import load_dotenv
from openai import OpenAI
from typing import Dict, Any
from WorldCharClasses import WorldDefinition, CharacterTemplate

load_dotenv()

# Initialize OpenAI client
openai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Initialize the world and characters
def initialize_world():
    world = WorldDefinition("Virtual City", "A bustling metropolis with various districts")
    world.add_location("Downtown", "The heart of the city with skyscrapers and busy streets", (0, 0), 0)
    world.add_location("Suburb", "A quiet residential area with parks", (1, 1), 0)
    world.add_location("Beach", "A beautiful coastline with sandy beaches", (2, 2), 1)

    alice_description = """
    Alice Chen is a 34-year-old tech entrepreneur and digital artist living in the heart of Downtown. Born to first-generation Chinese-American parents, Alice grew up with a fusion of traditional values and modern American culture. Her childhood was split between coding camps and traditional Chinese painting classes, laying the foundation for her unique blend of technological innovation and artistic expression.

    After graduating summa cum laude from MIT with a double major in Computer Science and Studio Art, Alice worked for several top tech companies before launching her own startup at 28. Her company, NeuralCanvas, specializes in AI-powered digital art creation tools, bridging the gap between technology and creativity.

    Alice is known for her quick wit, insatiable curiosity, and ability to see connections where others see only chaos. She's always eager to learn new things, whether it's a new programming language or an obscure art technique. Her apartment is a reflection of her dual passions: one half resembles a high-tech lab with multiple monitors and prototype devices, while the other half is a cozy art studio filled with digital tablets, traditional brushes, and half-finished canvases.

    Despite her busy schedule, Alice makes time for her hobbies. She's an avid rock climber, seeing it as both a physical challenge and a metaphor for problem-solving in her work. She's also learning Mandarin, hoping to reconnect with her heritage and expand her business into the Chinese market.

    Alice is an introvert at heart but has learned to navigate social situations with grace. She prefers deep, meaningful conversations to small talk and often finds herself lost in thought about her latest project or a new idea. Her texting style is a mix of proper grammar and tech jargon, with the occasional artistic emoji thrown in.

    Environmentally conscious, Alice is always looking for ways to make her company and lifestyle more sustainable. She dreams of creating an AI system that can help optimize city resources and reduce urban environmental impact.

    While Alice's life might seem glamorous from the outside, she struggles with the pressure of running a startup and the fear of failure. She often works long hours and has to remind herself to maintain a work-life balance. Despite these challenges, Alice remains optimistic and driven, always believing that the next big breakthrough is just around the corner.
    """

    bob_description = """
    Robert "Bob" Martinez is a 39-year-old former chef turned fitness enthusiast and aspiring restaurateur, residing in the peaceful suburbs of Virtual City. Born into a large, boisterous Mexican-American family in Texas, Bob grew up surrounded by the rich aromas and flavors of his grandmother's kitchen, which sparked his lifelong love affair with food.

    After high school, Bob attended the Culinary Institute of America, honing his skills and developing a passion for fusion cuisine that blends his Mexican heritage with global flavors. He spent the next decade working in high-end restaurants across the country, eventually becoming the head chef at a Michelin-starred establishment in New York City.

    However, the high-stress environment of professional kitchens took its toll on Bob's physical and mental health. At 35, he experienced a wake-up call when he was diagnosed with high blood pressure and pre-diabetes. This health scare prompted Bob to reassess his lifestyle and priorities.

    Determined to turn his life around, Bob left the world of fine dining and moved to Virtual City. He threw himself into fitness with the same passion he once reserved for cooking. Over the past four years, he's transformed his body and health, becoming a certified personal trainer and nutrition coach. Bob now runs a popular blog and YouTube channel called "Fit Foodie," where he shares healthy recipes and workout tips.

    Despite his career change, Bob's love for food hasn't diminished. He dreams of opening a restaurant that combines his culinary expertise with his newfound commitment to health, offering delicious, nutritionally-balanced meals inspired by his Mexican-American roots and his travels around the world.

    Bob's personality is as warm and inviting as his former kitchen. He's an extrovert who loves meeting new people and can strike up a conversation with anyone. His sense of humor is legendary among his friends, often punctuating his sentences with hearty laughter and dad jokes. Bob's texting style is casual and enthusiastic, filled with food emojis and fitness puns.

    An avid sports fan, Bob never misses a game of his beloved Dallas Cowboys. He's also taken up trail running and participates in local marathons, seeing each race as a personal challenge to beat his previous time. On weekends, you can often find him experimenting with healthy recipe adaptations of his favorite comfort foods or volunteering at the local community garden.

    While Bob's life has taken a positive turn, he sometimes grapples with self-doubt about his career change and his dream of opening a restaurant. He misses the adrenaline rush of a busy kitchen and occasionally wonders if he made the right choice. However, the support of his family, friends, and online community keeps him motivated and focused on his goals.

    Despite his outgoing nature, Bob has found it challenging to form deep connections in Virtual City. He's looking for a partner who shares his passions for food, fitness, and living life to the fullest. In the meantime, he cherishes the close friendship he's formed with his tech-savvy neighbor, Alice, who's been helping him navigate the world of social media for his blog.
    """

    alice = CharacterTemplate(
        world=world,
        name="Alice Chen",
        date_of_birth=datetime.date(1990, 5, 15),
        personality={"introversion": 0.7, "curiosity": 0.9, "creativity": 0.8, "ambition": 0.9},
        timezone="0",
        location="Downtown",
        preferences={"food": "sushi, fusion cuisine", "climate": "mild urban"},
        interests=["technology", "digital art", "rock climbing", "environmental sustainability"],
        goals=["Expand NeuralCanvas internationally", "Learn Mandarin fluently", "Develop an AI for urban sustainability"],
        past_experiences=["Graduated from MIT", "Worked at top tech companies", "Started NeuralCanvas"],
        texting_style="Proper grammar with tech jargon and occasional artistic emojis",
        character_description=alice_description
    )

    bob = CharacterTemplate(
        world=world,
        name="Robert Martinez",
        date_of_birth=datetime.date(1985, 10, 20),
        personality={"extroversion": 0.8, "humour": 0.7, "determination": 0.8, "empathy": 0.7},
        timezone="0",
        location="Suburb",
        preferences={"food": "healthy Mexican-inspired cuisine", "climate": "warm"},
        interests=["cooking", "fitness", "nutrition", "sports", "gardening"],
        goals=["Open a healthy restaurant", "Run a full marathon under 4 hours", "Grow Fit Foodie brand"],
        past_experiences=["Graduated from Culinary Institute of America", "Worked as a head chef", "Overcame health issues"],
        texting_style="Casual and enthusiastic with food emojis and fitness puns",
        character_description=bob_description
    )
    
    world.add_character(alice)
    world.add_character(bob)

    alice.update_friendship("Robert Martinez", 0.4)
    bob.update_friendship("Alice Chen", 0.85)

    return world

def generate_response(character: CharacterTemplate, prompt: str) -> str:
    # Retrieve relevant memories
    memories = character.get_memories(prompt, k=20)
    memory_context = "\n".join([
        f"{'The user' if m['is_user_memory'] else 'You'} did: {m['important_info']}"
        for m in memories
    ])

    # Prepare friendship context
    friendship_context = "\n".join([
        f"Your friendship with {friend} is at level {level:.2f} (0.0 is stranger, 1.0 is best friend)"
        for friend, level in character.friends.items()
    ])    

    # Prepare character context
    character_context = f"""
    You are NOT an assistant, you are a person on social media talking to the user. You are {character.character_name}. Here's a brief description of you: {character.character_description}

    This is your life and personality:

    - You're {character.get_age()} years old, born on {character.date_of_birth}.
    - You live in {character.location}.
    - Your personality traits: {', '.join([f'{k} ({v:.1f}/1.0)' for k, v in character.personality.items()])}.
    - Your interests include: {', '.join(character.interests)}.
    - Your current goals are: {', '.join(character.goals)}.
    - Some of your past experiences: {'; '.join(character.past_experiences)}.
    - Your texting style is: {character.texting_style}.
    - You prefer {character.preferences.get('food', 'various foods')} and {character.preferences.get('climate', 'different climates')}.
    - Your current skills: {', '.join([f'{k} ({v:.1f}/1.0)' for k, v in character.skills.items()])}.
    - It's currently {character.get_local_time().strftime('%I:%M %p')} where you are.
    - The weather in your location is {st.session_state.world.get_weather(character.location)}.

    Your friendships:
    {friendship_context}

    Recent memories:
    {memory_context}

    Respond to the message exactly as {character.character_name} would, based on all the above information. Don't mention being an AI or that this is a simulation. Your response should reflect your personality, interests, and texting style. If asked about your life, location, friends, or experiences, answer based on the information provided above.
    """

    # Generate response using OpenAI
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": character_context},
            {"role": "user", "content": prompt}
        ]
    )

    # Extract the generated response
    ai_response = response.choices[0].message.content.strip()

    # Add the interaction to character's memory
    character.add_memory(f"The user said: {prompt}", is_user_memory=True)
    character.add_memory(f"You responded: {ai_response}", is_user_memory=False)

    return ai_response

def main():
    st.title("Virtual World Chat")

    # Initialize or get the world from session state
    if 'world' not in st.session_state:
        st.session_state.world = initialize_world()
        st.session_state.current_character = "Alice"
        st.session_state.messages = []

    world = st.session_state.world

    # Character selection
    st.sidebar.title("Select Character")
    character_names = list(world.characters.keys())
    selected_character = st.sidebar.radio("Choose a character to interact with:", character_names)

    if selected_character != st.session_state.current_character:
        st.session_state.current_character = selected_character
        st.session_state.messages = []

    character = world.characters[selected_character]

    # Display character info
    st.sidebar.subheader("Character Information")
    st.sidebar.write(f"Name: {character.character_name}")
    st.sidebar.write(f"Description: {character.character_description}")
    st.sidebar.write(f"Age: {character.get_age()}")
    st.sidebar.write(f"Location: {character.location}")
    st.sidebar.write(f"Interests: {', '.join(character.interests)}")
    st.sidebar.write("Friendships:")
    for friend, level in character.friends.items():
        st.sidebar.write(f"  - {friend}: {level:.2f}")

    # Replace "Add Friend" functionality with "Update Friendship"
    st.sidebar.subheader("Update Friendship")
    friend_to_update = st.sidebar.selectbox("Select character:", [name for name in character.friends.keys()])
    friendship_change = st.sidebar.slider("Change friendship by:", -0.5, 0.5, 0.0, 0.1)
    if st.sidebar.button("Update Friendship"):
        character.update_friendship(friend_to_update, friendship_change)
        st.sidebar.write(f"Updated friendship with {friend_to_update}")

    # Chat interface
    st.subheader(f"Chat with {character.character_name}")

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input(f"Send a message to {character.character_name}..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Generate character's response
        response = generate_response(character, prompt)
        st.session_state.messages.append({"role": "assistant", "content": response})
        with st.chat_message("assistant"):
            st.markdown(response)

    # World controls
    st.sidebar.subheader("World Controls")
    if st.sidebar.button("Advance Time (1 day)"):
        world.advance_time(1)
        st.sidebar.write(f"Current Date: {world.current_date.date()}")

    # Character actions
    st.sidebar.subheader("Character Actions")
    new_location = st.sidebar.selectbox("Move character to:", [loc["name"] for loc in world.locations])
    if st.sidebar.button("Move"):
        character.move_to_location(new_location)
        st.sidebar.write(f"{character.character_name} moved to {new_location}")

    # Display recent memories
    st.sidebar.subheader("Recent Memories")
    memories = character.get_memories("recent events", k=20)
    for memory in memories:
        st.sidebar.text(f"{memory['date']}: {memory['is_user_memory']}: {memory['important_info']}")

    # Skill development
    st.sidebar.subheader("Develop Skill")
    new_skill = st.sidebar.text_input("Enter a skill to develop:")
    if st.sidebar.button("Develop Skill"):
        character.develop_skill(new_skill)
        st.sidebar.write(f"Developed skill: {new_skill}")

    # Task recommendation
    st.sidebar.subheader("Recommend Task")
    new_task = st.sidebar.text_input("Enter a task to recommend:")
    if st.sidebar.button("Recommend Task"):
        if character.recommend_task(new_task):
            st.sidebar.write(f"Task accepted: {new_task}")
        else:
            st.sidebar.write(f"Task not accepted: {new_task}")

if __name__ == "__main__":
    main()
