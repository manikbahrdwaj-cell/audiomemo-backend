"""
LangChain RunnableConfig Integration Examples
Demonstrates how to use RunnableConfig with chains and graphs after voice verification

This module shows practical examples of:
1. Creating chains with RunnableConfig
2. Using session data in prompts
3. Processing messages through LangChain
4. Integrating with LangGraph
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime

from langchain_core.runnables import RunnableConfig, Runnable
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from langchain_session_integration import get_langchain_session_integration

logger = logging.getLogger(__name__)


class VoiceVerifiedChatChain:
    """
    Example chain that uses voice verification context
    """
    
    def __init__(self):
        """Initialize the chat chain"""
        self.integration = get_langchain_session_integration()
    
    def create_system_prompt_with_context(
        self,
        config: RunnableConfig
    ) -> str:
        """
        Create a system prompt that includes voice verification context
        
        Args:
            config: RunnableConfig with session information
            
        Returns:
            System prompt string
        """
        phone_number = config.configurable.get("phone_number", "Unknown")
        verification_score = config.configurable.get("verification_score", 0.0)
        session_id = config.configurable.get("session_id", "")
        
        system_prompt = f"""You are a helpful assistant for a voice-verified customer.

Customer Context:
- Phone: {phone_number}
- Voice Verification Score: {verification_score:.2%}
- Session ID: {session_id}
- Verified at: {datetime.now().isoformat()}

Guidelines:
- Address the customer by their phone number if context is needed
- Reference their verification status for security-sensitive operations
- Keep responses concise and professional
- Log important decisions with the session ID for compliance

Current Conversation:
"""
        return system_prompt
    
    def create_chat_prompt(
        self,
        config: RunnableConfig,
        include_history: bool = True
    ) -> ChatPromptTemplate:
        """
        Create a chat prompt template with context
        
        Args:
            config: RunnableConfig with session information
            include_history: Whether to include conversation history
            
        Returns:
            ChatPromptTemplate
        """
        system_prompt = self.create_system_prompt_with_context(config)
        
        messages = [
            ("system", system_prompt),
            ("placeholder", "{chat_history}") if include_history else None,
            ("human", "{message}")
        ]
        
        # Filter out None values
        messages = [m for m in messages if m is not None]
        
        return ChatPromptTemplate.from_messages(messages)
    
    def get_conversation_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> str:
        """
        Retrieve formatted conversation history from session
        
        Args:
            session_id: The LangChain session ID
            limit: Maximum number of turns to retrieve
            
        Returns:
            Formatted conversation history string
        """
        try:
            session_info = self.integration.get_session_info(session_id)
            
            if not session_info:
                return ""
            
            history_str = ""
            conversation = session_info.get("conversation_history", [])[-limit:]
            
            for msg in conversation:
                role = msg.get("role", "unknown").upper()
                content = msg.get("content", "")
                history_str += f"{role}: {content}\n"
            
            return history_str
        
        except Exception as e:
            logger.warning(f"Failed to retrieve conversation history: {str(e)}")
            return ""
    
    def create_chain(
        self,
        config: RunnableConfig,
        llm: Optional[Runnable] = None
    ) -> Runnable:
        """
        Create a chat chain with RunnableConfig context
        
        Args:
            config: RunnableConfig with session information
            llm: Language model to use (if None, uses OpenAI GPT-4)
            
        Returns:
            Runnable chain
        """
        # Use provided LLM or default to GPT-4
        if llm is None:
            try:
                from langchain_openai import ChatOpenAI
                llm = ChatOpenAI(
                    model="gpt-4",
                    temperature=config.configurable.get("temperature", 0.7)
                )
            except ImportError:
                logger.warning("OpenAI not available, using mock for testing")
                llm = None
        
        # Create prompt with context
        prompt = self.create_chat_prompt(config)
        
        # Create output parser
        output_parser = StrOutputParser()
        
        # Build chain
        if llm:
            chain = prompt | llm | output_parser
        else:
            # Mock chain for testing
            chain = prompt | (lambda x: "Mock response: " + str(x))
        
        return chain
    
    async def process_message(
        self,
        session_id: str,
        user_message: str,
        config: RunnableConfig,
        llm: Optional[Runnable] = None
    ) -> str:
        """
        Process a user message through the chain
        
        Args:
            session_id: LangChain session ID
            user_message: User's message
            config: RunnableConfig with session information
            llm: Language model to use
            
        Returns:
            Assistant's response
        """
        try:
            # Create chain
            chain = self.create_chain(config, llm)
            
            # Get conversation history
            chat_history = self.get_conversation_history(session_id)
            
            # Prepare input
            input_data = {
                "message": user_message,
                "chat_history": chat_history
            }
            
            # Invoke chain
            response = await chain.ainvoke(input_data, config=config)
            
            # Add messages to session
            self.integration.add_message_to_session(
                session_id=session_id,
                role="user",
                content=user_message,
                metadata={"source": "websocket"}
            )
            
            self.integration.add_message_to_session(
                session_id=session_id,
                role="assistant",
                content=response,
                metadata={"source": "langchain_chain"}
            )
            
            logger.info(
                f"Processed message in session {session_id[:16]}: "
                f"user='{user_message[:50]}...' assistant='{response[:50]}...'"
            )
            
            return response
        
        except Exception as e:
            logger.error(f"Error processing message: {str(e)}", exc_info=True)
            raise


class VoiceVerifiedChatWebSocketHandler:
    """
    WebSocket handler that integrates chat chains with sessions
    """
    
    def __init__(self):
        """Initialize the handler"""
        self.chat_chain = VoiceVerifiedChatChain()
        self.integration = get_langchain_session_integration()
    
    async def handle_chat_with_llm(
        self,
        connection: 'ClientConnection',
        message: Dict[str, Any],
        llm: Optional[Runnable] = None
    ) -> Dict[str, Any]:
        """
        Handle chat messages with LLM processing
        
        Args:
            connection: WebSocket connection
            message: Incoming message dict
            llm: Language model to use
            
        Returns:
            Response dict
        """
        try:
            # Get session info from connection
            session_id = connection.metadata.get("langchain_session_id")
            phone_number = connection.metadata.get("verified_phone")
            
            if not session_id:
                return {
                    "status": "error",
                    "message": "No active session"
                }
            
            # Extract user message
            user_message = message.get("content", "").strip()
            if not user_message:
                return {
                    "status": "error",
                    "message": "Empty message"
                }
            
            # Get session info for config
            session_info = self.integration.get_session_info(session_id)
            
            # Create RunnableConfig
            config = RunnableConfig(
                run_name=f"voice_chat_{phone_number}",
                tags=["voice_verified", "websocket"],
                configurable={
                    "session_id": session_id,
                    "thread_id": session_info.get("thread_id", ""),
                    "phone_number": phone_number,
                    "verification_score": session_info.get("verification_score", 0.0),
                    "temperature": message.get("temperature", 0.7),
                    "source": "websocket"
                }
            )
            
            # Process message
            response = await self.chat_chain.process_message(
                session_id=session_id,
                user_message=user_message,
                config=config,
                llm=llm
            )
            
            return {
                "status": "success",
                "session_id": session_id,
                "phone_number": phone_number,
                "user_message": user_message,
                "assistant_response": response,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            logger.error(f"Error in chat handler: {str(e)}", exc_info=True)
            return {
                "status": "error",
                "message": f"Processing error: {str(e)}"
            }


# ============================================================================
# LANGGRAPH INTEGRATION EXAMPLE
# ============================================================================

class VoiceVerifiedAgentGraph:
    """
    Example LangGraph agent that uses voice verification context
    """
    
    def __init__(self):
        """Initialize the agent graph"""
        self.integration = get_langchain_session_integration()
    
    def create_agent_config(
        self,
        session_id: str,
        phone_number: str,
        verification_score: float
    ) -> RunnableConfig:
        """
        Create a RunnableConfig for the agent graph
        
        Args:
            session_id: LangChain session ID
            phone_number: Verified phone number
            verification_score: Voice verification score
            
        Returns:
            RunnableConfig for graph execution
        """
        session_info = self.integration.get_session_info(session_id)
        
        return RunnableConfig(
            run_name=f"agent_{phone_number}",
            tags=["agent", "voice_verified"],
            configurable={
                "session_id": session_id,
                "thread_id": session_info.get("thread_id", ""),
                "phone_number": phone_number,
                "verification_score": verification_score,
                "verified": True,
                "source": "websocket"
            }
        )
    
    def create_system_prompt(
        self,
        config: RunnableConfig
    ) -> str:
        """
        Create system prompt for agent with context
        
        Args:
            config: RunnableConfig with agent context
            
        Returns:
            System prompt string
        """
        phone_number = config.configurable.get("phone_number", "Unknown")
        verification_score = config.configurable.get("verification_score", 0.0)
        session_id = config.configurable.get("session_id", "")
        
        prompt = f"""You are an intelligent agent helping a voice-verified customer.

CUSTOMER CONTEXT:
- Phone: {phone_number}
- Verification Score: {verification_score:.2%}
- Session: {session_id}
- Status: Voice Verified
- Timestamp: {datetime.now().isoformat()}

AVAILABLE ACTIONS:
- answer_question: Answer customer questions
- retrieve_account_info: Get account information
- process_request: Handle customer requests
- escalate_to_human: Escalate if needed

RULES:
- Always acknowledge voice verification status
- Use session ID for all logging
- Be professional and helpful
- Ask for clarification if needed
- Escalate complex issues to human agents

CONVERSATION:"""
        return prompt


# ============================================================================
# EXAMPLE USAGE
# ============================================================================

async def example_process_chat_message():
    """Example: Process a chat message with RunnableConfig"""
    
    print("\n" + "="*70)
    print("Example: Process Chat Message with RunnableConfig")
    print("="*70)
    
    # Setup
    integration = get_langchain_session_integration()
    
    # Create a session (simulating successful voice verification)
    session_result = integration.create_session_on_voice_match(
        phone_number="+1-555-0100",
        verification_score=0.95,
        similarity_metrics={"cosine_similarity": 0.95}
    )
    
    if not session_result['success']:
        print(f"Failed to create session: {session_result.get('error')}")
        return
    
    session_id = session_result['session_id']
    print(f"✓ Created session: {session_id[:16]}")
    
    # Create RunnableConfig
    config = RunnableConfig(
        run_name="example_chat",
        configurable={
            "session_id": session_id,
            "thread_id": session_result['thread_id'],
            "phone_number": "+1-555-0100",
            "verification_score": 0.95,
            "temperature": 0.7
        }
    )
    
    print(f"✓ Created RunnableConfig with thread: {config.configurable['thread_id'][:16]}")
    
    # Create chat chain
    chat_chain = VoiceVerifiedChatChain()
    user_message = "Hello, I need help with my account."
    
    print(f"✓ User message: {user_message}")
    
    # Add messages to session
    integration.add_message_to_session(
        session_id=session_id,
        role="user",
        content=user_message,
        metadata={"source": "example"}
    )
    
    integration.add_message_to_session(
        session_id=session_id,
        role="assistant",
        content="Hi! I'm here to help with your account. What can I help you with today?",
        metadata={"source": "example"}
    )
    
    print("✓ Added messages to session")
    
    # Get session info
    session_info = integration.get_session_info(session_id)
    if session_info:
        print(f"✓ Session info retrieved:")
        print(f"  - Status: {session_info.get('status')}")
        print(f"  - Messages: {session_info.get('conversation_turns', 0)}")
    
    print("\n✓ Example complete!")


def example_runnableconfig_creation():
    """Example: Create RunnableConfig for chains"""
    
    print("\n" + "="*70)
    print("Example: RunnableConfig Creation")
    print("="*70)
    
    # Create RunnableConfig for a voice-verified user
    config = RunnableConfig(
        run_name="example_verified_user",
        tags=["voice_verified", "chat"],
        configurable={
            "session_id": "lg_session_12345",
            "thread_id": "thread_abc123",
            "phone_number": "+1-555-0123",
            "verification_score": 0.92,
            "temperature": 0.7,
            "max_tokens": 500,
            "source": "websocket",
            "client_id": "client_xyz"
        }
    )
    
    print("✓ Created RunnableConfig:")
    print(f"  - Run Name: {config.run_name}")
    print(f"  - Tags: {config.tags}")
    print(f"  - Configurable Keys: {list(config.configurable.keys())}")
    print(f"  - Session: {config.configurable['session_id']}")
    print(f"  - Thread: {config.configurable['thread_id']}")
    print(f"  - User: {config.configurable['phone_number']}")


def example_system_prompt_with_context():
    """Example: Create system prompt with context"""
    
    print("\n" + "="*70)
    print("Example: System Prompt with Context")
    print("="*70)
    
    config = RunnableConfig(
        configurable={
            "session_id": "lg_session_abc123",
            "phone_number": "+1-555-0123",
            "verification_score": 0.88
        }
    )
    
    chain = VoiceVerifiedChatChain()
    system_prompt = chain.create_system_prompt_with_context(config)
    
    print("✓ System Prompt:")
    print("-" * 70)
    print(system_prompt)
    print("-" * 70)


if __name__ == "__main__":
    print("LangChain RunnableConfig Integration Examples")
    print("=" * 70)
    
    # Run synchronous examples
    example_runnableconfig_creation()
    example_system_prompt_with_context()
    
    # Run async example
    import asyncio
    asyncio.run(example_process_chat_message())
