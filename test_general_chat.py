import asyncio
import os
from dotenv import load_dotenv
from ai import ClaudeClient
import logging

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_general_chat():
    load_dotenv()
    client = ClaudeClient()
    
    user_profile = {
        'goals': 'Розтяжка',
        'experience_level': 'intermediate',
        'health_conditions': [],
        'available_duration': 15
    }
    
    user_message = "Про що цей бот"
    
    print(f"Testing general AI response for: '{user_message}'")
    try:
        response = await client.generate_general_response(
            user_message=user_message,
            user_data=user_profile
        )
        print("Success! AI Response:")
        print(response)
    except Exception as e:
        print(f"FAILED: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_general_chat())
