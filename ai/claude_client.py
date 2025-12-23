import logging
import asyncio
from typing import Dict, List, Optional
from openai import AsyncOpenAI, RateLimitError, APIStatusError
from config import Config

logger = logging.getLogger(__name__)


class ClaudeClient:
    """Client for interacting with AI models via OpenRouter API"""
    
    async def generate_response(
        self,
        system_prompt: str,
        user_message: str,
        conversation_history: Optional[List[Dict]] = None
    ) -> str:
        """
        Generate AI response using OpenRouter
        
        Args:
            system_prompt: System instructions for the AI
            user_message: User's message or request
            conversation_history: Previous conversation messages
            
        Returns:
            Generated response text
        """
        try:
            messages = [{"role": "system", "content": system_prompt}]
            
            if conversation_history:
                messages.extend(conversation_history)
            
            messages.append({
                "role": "user",
                "content": user_message
            })
            
            # List of models to try (primary + fallbacks)
            models_to_try = [self.model]
            
            # Add free fallbacks if the primary is a free model
            if self.model.endswith(':free'):
                fallbacks = [
                    "google/gemini-2.0-flash-exp:free",
                    "google/gemini-flash-1.5-8b:free",
                    "google/gemini-flash-1.5:free",
                    "mistralai/mistral-7b-instruct:free",
                    "qwen/qwen-2-7b-instruct:free"
                ]
                for fb in fallbacks:
                    if fb != self.model:
                        models_to_try.append(fb)

            last_exception = None
            for model_name in models_to_try:
                try:
                    logger.info(f"Trying model: {model_name}")
                    response = await self.client.chat.completions.create(
                        model=model_name,
                        messages=messages,
                        max_tokens=self.max_tokens,
                        temperature=self.temperature,
                    )
                    return response.choices[0].message.content
                except RateLimitError as e:
                    last_exception = e
                    logger.warning(f"Rate limit hit for {model_name}: {e}")
                    # If it's a per-minute limit, a small wait might help
                    await asyncio.sleep(2)
                    continue
                except APIStatusError as e:
                    last_exception = e
                    if e.status_code == 429:
                        logger.warning(f"429 Status code for {model_name}, trying next...")
                        await asyncio.sleep(2)
                        continue
                    else:
                        logger.error(f"API Error {e.status_code} with model {model_name}: {e}")
                        continue
                except Exception as e:
                    last_exception = e
                    logger.error(f"Unexpected error with model {model_name}: {e}")
                    continue
            
            # If we're here, all models failed
            logger.error(f"All models failed. Last error: {last_exception}")
            raise last_exception
            
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            raise

    def __init__(self):
        self.client = AsyncOpenAI(
            base_url=Config.OPENROUTER_BASE_URL,
            api_key=Config.OPENROUTER_API_KEY,
            timeout=120.0,
        )
        self.model = Config.OPENROUTER_MODEL
        self.max_tokens = Config.MAX_TOKENS
        self.temperature = Config.TEMPERATURE
    
    async def generate_practice(
        self,
        user_data: Dict,
        practice_type: str,
        duration: int,
        module_context: Optional[Dict] = None
    ) -> Dict:
        """
        Generate personalized yoga practice
        
        Args:
            user_data: User profile and preferences
            practice_type: Type of practice (asana, pranayama, meditation)
            duration: Practice duration in minutes
            module_context: Current module information
            
        Returns:
            Dictionary with practice content and metadata
        """
        from .prompts import PromptManager
        
        system_prompt = PromptManager.get_practice_generation_prompt()
        user_prompt = PromptManager.format_practice_request(
            user_data=user_data,
            practice_type=practice_type,
            duration=duration,
            module_context=module_context
        )
        
        response = await self.generate_response(
            system_prompt=system_prompt,
            user_message=user_prompt
        )
        
        # Parse response into structured format
        return self._parse_practice_response(response)
    
    async def generate_onboarding_response(
        self,
        user_message: str,
        onboarding_stage: str,
        user_data: Dict
    ) -> str:
        """
        Generate personalized onboarding response
        
        Args:
            user_message: User's message during onboarding
            onboarding_stage: Current stage of onboarding
            user_data: Collected user data so far
            
        Returns:
            AI-generated response
        """
        from .prompts import PromptManager
        
        system_prompt = PromptManager.get_onboarding_prompt()
        user_prompt = PromptManager.format_onboarding_message(
            user_message=user_message,
            stage=onboarding_stage,
            user_data=user_data
        )
        
        return await self.generate_response(
            system_prompt=system_prompt,
            user_message=user_prompt
        )
    
    async def generate_general_response(
        self,
        user_message: str,
        user_data: Dict
    ) -> str:
        """
        Generate response to general user messages
        
        Args:
            user_message: User's message
            user_data: User context data (profile)
            
        Returns:
            AI-generated response
        """
        from .prompts import PromptManager
        
        system_prompt = PromptManager.get_general_chat_prompt()
        
        # Add user profile to the message for context
        profile_context = PromptManager._format_user_data(user_data)
        full_user_message = f"ПРОФІЛЬ КОРИСТУВАЧА:\n{profile_context}\n\nПИТАННЯ: {user_message}"
        
        return await self.generate_response(
            system_prompt=system_prompt,
            user_message=full_user_message
        )
    
    async def generate_summary(
        self,
        practice_content: str
    ) -> str:
        """
        Generate a short summary of a completed practice
        
        Args:
            practice_content: Content of the practice to summarize
            
        Returns:
            Short summary (max 500 characters)
        """
        from .prompts import PromptManager
        
        system_prompt = PromptManager.get_practice_summary_prompt()
        user_prompt = f"Зроби короткий підсумок цієї практики (макс 500 символів):\n\n{practice_content}"
        
        return await self.generate_response(
            system_prompt=system_prompt,
            user_message=user_prompt
        )
    
    async def generate_insight(
        self,
        user_progress: Dict,
        practice_history: List[Dict],
        module_info: Dict
    ) -> str:
        """
        Generate personalized insight based on user progress
        
        Args:
            user_progress: User's progress data
            practice_history: Recent practice sessions
            module_info: Current module information
            
        Returns:
            Personalized insight message
        """
        from .prompts import PromptManager
        
        system_prompt = PromptManager.get_insight_generation_prompt()
        user_prompt = PromptManager.format_insight_request(
            user_progress=user_progress,
            practice_history=practice_history,
            module_info=module_info
        )
        
        return await self.generate_response(
            system_prompt=system_prompt,
            user_message=user_prompt
        )
    
    def _parse_practice_response(self, response: str) -> Dict:
        """
        Parse AI response into structured practice format
        
        Args:
            response: Raw AI response
            
        Returns:
            Structured practice dictionary
        """
        # For now, we treat the entire response as the content
        # In the future, we can add logic to parse sections like "WARMUP", "MAIN", etc.
        return {
            "content": response,
            "sections": [],
            "tips": [],
            "modifications": []
        }
