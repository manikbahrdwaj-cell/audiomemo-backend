"""
Complete LLM Chain Builder for Voice-Verified Users
Demonstrates building production-ready LLM chains with RunnableConfig and WebSocket integration
"""

import logging
import asyncio
from typing import Optional, List, Dict, Any
from datetime import datetime

from langchain_core.runnables import RunnableConfig, Runnable
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import SystemMessage, HumanMessage

from config.llm_config import get_llm
from langchain_session_integration import get_langchain_session_integration
from langchain_session_service import RunnableConfigWrapper

logger = logging.getLogger(__name__)


class VoiceVerifiedLLMChain:
    """
    Complete LLM Chain for voice-verified users
    Integrates voice verification, session management, and LLM processing
    """
    
    def __init__(self, llm: Optional[Runnable] = None):
        """
        Initialize the LLM chain
        
        Args:
            llm: Optional LangChain LLM instance. If None, uses configured default
        """
        self.integration = get_langchain_session_integration()
        self.llm = llm or get_llm()
        logger.info("VoiceVerifiedLLMChain initialized")
    
    def create_system_prompt(self, config: RunnableConfigWrapper) -> str:
        """
        Create a system prompt with voice verification context
        
        Args:
            config: RunnableConfigWrapper with session information
            
        Returns:
            System prompt string
        """
        phone_number = config.configurable.get("phone_number", "Unknown")
        verification_score = config.configurable.get("verification_score", 0.0)
        session_id = config.configurable.get("session_id", "")
        
        return f"""You are a helpful assistant for a voice-verified customer.

Customer Context:
- Phone: {phone_number}
- Voice Verification Score: {verification_score:.2%}
- Session ID: {session_id}
- Verified at: {datetime.now().isoformat()}

Guidelines:
1. Address the customer professionally
2. Reference their verification status for security-sensitive operations
3. Keep responses concise and helpful
4. Maintain conversation context throughout the session
5. Log important decisions for compliance with session ID: {session_id}

Current Conversation:
"""
    
    def create_chain(self, config: RunnableConfigWrapper) -> Runnable:
        """
        Create a complete LLM chain with context
        
        Args:
            config: RunnableConfigWrapper with session context
            
        Returns:
            Complete chain combining prompt, LLM, and output parsing
        """
        # System prompt with context
        system_prompt = self.create_system_prompt(config)
        
        # Create prompt template
        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human", "{message}")
        ])
        
        # Create output parser
        output_parser = StrOutputParser()
        
        # Complete chain: prompt -> LLM -> output parser
        chain = prompt | self.llm | output_parser
        
        logger.debug(f"Created chain for session {config.configurable.get('session_id', 'unknown')[:16]}")
        
        return chain
    
    async def process_user_message(
        self,
        phone_number: str,
        user_message: str,
        verification_score: float,
        session_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a user message through the complete LLM chain
        
        1. Create or get session
        2. Create RunnableConfig with context
        3. Process message through LLM chain
        4. Store conversation in session
        5. Return response
        
        Args:
            phone_number: Verified phone number
            user_message: User's message
            verification_score: Voice verification score (0-1)
            session_id: Optional existing session ID
            
        Returns:
            Dict with response and session info
        """
        try:
            # Step 1: Create or get session
            if session_id:
                session_info = self.integration.get_session_info(session_id)
                if not session_info:
                    logger.warning(f"Session {session_id} not found, creating new one")
                    session = self.integration.create_session_on_voice_match(
                        phone_number=phone_number,
                        verification_score=verification_score,
                        similarity_metrics={"score": verification_score}
                    )
                    if not session.get("success"):
                        raise Exception(f"Failed to create session: {session.get('error')}")
                    session_id = session["session_id"]
            else:
                # Create new session after voice match
                session = self.integration.create_session_on_voice_match(
                    phone_number=phone_number,
                    verification_score=verification_score,
                    similarity_metrics={"score": verification_score}
                )
                if not session.get("success"):
                    raise Exception(f"Failed to create session: {session.get('error')}")
                session_id = session["session_id"]
            
            # Step 2: Create RunnableConfig wrapper
            session_info = self.integration.get_session_info(session_id)
            config = RunnableConfigWrapper(
                {
                    "configurable": {
                        "session_id": session_id,
                        "phone_number": phone_number,
                        "thread_id": session_info.get("thread_id", f"thread_{session_id}"),
                        "verification_score": verification_score,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                }
            )
            
            # Step 3: Create and invoke chain
            chain = self.create_chain(config)
            
            logger.info(f"Processing message for session {session_id[:16]} from {phone_number}")
            
            # Invoke the chain
            response = chain.invoke({"message": user_message})
            
            # Step 4: Store conversation in session
            self.integration.add_message_to_session(
                session_id=session_id,
                role="user",
                content=user_message,
                metadata={"source": "api", "timestamp": datetime.utcnow().isoformat()}
            )
            
            self.integration.add_message_to_session(
                session_id=session_id,
                role="assistant",
                content=response,
                metadata={"source": "llm_chain", "timestamp": datetime.utcnow().isoformat()}
            )
            
            logger.info(
                f"Successfully processed message in session {session_id[:16]}: "
                f"user='{user_message[:50]}...' response='{response[:50]}...'"
            )
            
            # Step 5: Return complete response
            return {
                "success": True,
                "session_id": session_id,
                "phone_number": phone_number,
                "user_message": user_message,
                "assistant_response": response,
                "verification_score": verification_score,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e),
                "phone_number": phone_number
            }
    
    async def process_multi_turn_conversation(
        self,
        phone_number: str,
        messages: List[str],
        verification_score: float
    ) -> Dict[str, Any]:
        """
        Process multiple turns of conversation
        
        Args:
            phone_number: Verified phone number
            messages: List of user messages
            verification_score: Voice verification score
            
        Returns:
            Dict with all responses and session info
        """
        try:
            # Create session once for all turns
            session = self.integration.create_session_on_voice_match(
                phone_number=phone_number,
                verification_score=verification_score,
                similarity_metrics={"score": verification_score}
            )
            
            if not session.get("success"):
                raise Exception(f"Failed to create session: {session.get('error')}")
            
            session_id = session["session_id"]
            responses = []
            
            # Process each message in the conversation
            for i, message in enumerate(messages):
                logger.info(f"Processing turn {i+1}/{len(messages)} in session {session_id[:16]}")
                
                result = await self.process_user_message(
                    phone_number=phone_number,
                    user_message=message,
                    verification_score=verification_score,
                    session_id=session_id
                )
                
                if result["success"]:
                    responses.append(result)
                else:
                    logger.error(f"Turn {i+1} failed: {result.get('error')}")
                    responses.append(result)
            
            # Get final session info
            final_session = self.integration.get_session_info(session_id)
            
            return {
                "success": True,
                "session_id": session_id,
                "phone_number": phone_number,
                "turns": len(messages),
                "responses": responses,
                "final_session_info": final_session
            }
        
        except Exception as e:
            logger.error(f"Error in multi-turn conversation: {str(e)}", exc_info=True)
            return {
                "success": False,
                "error": str(e)
            }


async def example_single_message():
    """Example: Process a single message with voice verification"""
    print("\n" + "="*70)
    print("EXAMPLE: Single Message Processing")
    print("="*70)
    
    chain = VoiceVerifiedLLMChain()
    
    result = await chain.process_user_message(
        phone_number="+1-555-0123",
        user_message="Hello! What can you help me with today?",
        verification_score=0.95
    )
    
    print(f"\nSession ID: {result.get('session_id', 'N/A')[:16]}")
    print(f"User: {result.get('user_message', 'N/A')}")
    print(f"Assistant: {result.get('assistant_response', 'N/A')}")
    print(f"Verification Score: {result.get('verification_score', 0):.2%}")


async def example_multi_turn_conversation():
    """Example: Multi-turn conversation with context"""
    print("\n" + "="*70)
    print("EXAMPLE: Multi-Turn Conversation")
    print("="*70)
    
    chain = VoiceVerifiedLLMChain()
    
    messages = [
        "Hi, I need help with my account",
        "How do I reset my password?",
        "Can you explain the security features?",
        "Thank you for the help!"
    ]
    
    result = await chain.process_multi_turn_conversation(
        phone_number="+1-555-0456",
        messages=messages,
        verification_score=0.92
    )
    
    if result["success"]:
        print(f"\nSession: {result.get('session_id', 'N/A')[:16]}")
        print(f"Completed {result.get('turns', 0)} conversation turns")
        
        for i, response in enumerate(result.get('responses', []), 1):
            if response.get('success'):
                print(f"\nTurn {i}:")
                print(f"  User: {response.get('user_message', 'N/A')[:60]}")
                print(f"  Assistant: {response.get('assistant_response', 'N/A')[:60]}")
    else:
        print(f"Error: {result.get('error', 'Unknown error')}")


async def example_with_custom_llm():
    """Example: Use custom LLM configuration"""
    print("\n" + "="*70)
    print("EXAMPLE: Custom LLM Configuration")
    print("="*70)
    
    from config.openai_config import OpenAIConfig
    
    # Create custom LLM with specific configuration
    config = OpenAIConfig(
        model="gpt-4-turbo",
        temperature=0.7,
        max_tokens=1000
    )
    custom_llm = config.get_llm()
    
    # Create chain with custom LLM
    chain = VoiceVerifiedLLMChain(llm=custom_llm)
    
    result = await chain.process_user_message(
        phone_number="+1-555-0789",
        user_message="Tell me about your features and pricing",
        verification_score=0.98
    )
    
    print(f"\nUsing LLM: gpt-4-turbo")
    print(f"Response: {result.get('assistant_response', 'N/A')}")


async def main():
    """Run all examples"""
    import os
    from dotenv import load_dotenv
    
    # Load environment variables
    load_dotenv()
    
    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Run examples
    await example_single_message()
    await example_multi_turn_conversation()
    
    # Optional: uncomment to test with custom LLM
    # await example_with_custom_llm()
    
    print("\n" + "="*70)
    print("✓ All examples completed successfully!")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(main())
