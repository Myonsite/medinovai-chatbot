"""
AI Engine - Core AI processing for MedinovAI healthcare conversations
Handles OpenAI integration, RAG pipeline, and context-aware response generation
"""

from typing import Dict, List, Optional, Any

import structlog
import openai
from langchain.chains import ConversationalRetrievalChain
from langchain.memory import ConversationBufferMemory
from langchain.prompts import PromptTemplate

from utils.config import Settings
from retrieval.vector_store import VectorStore
from retrieval.document_processor import DocumentProcessor

logger = structlog.get_logger(__name__)


class AIEngine:
    """
    Core AI engine for healthcare conversation processing.
    Integrates OpenAI GPT models with RAG pipeline for accurate medical responses.
    """
    
    def __init__(self, settings: Settings):
        self.settings = settings
        self.vector_store: Optional[VectorStore] = None
        self.document_processor: Optional[DocumentProcessor] = None
        self.conversational_chain: Optional[ConversationalRetrievalChain] = None
        
        # AI configuration
        self.ai_config = settings.get_ai_config()
        
        # Initialize OpenAI client
        if settings.ai_provider == "openai":
            openai.api_key = self.ai_config["api_key"]
        
        # Healthcare-specific prompts
        self.system_prompts = self._load_healthcare_prompts()
        
        logger.info("AI engine initialized", provider=settings.ai_provider)
    
    async def initialize(self) -> None:
        """Initialize AI engine components."""
        try:
            # Initialize vector store for RAG
            if self.settings.rag_enabled:
                self.vector_store = VectorStore(self.settings)
                await self.vector_store.initialize()
                
                self.document_processor = DocumentProcessor(self.settings)
                await self.document_processor.initialize()
                
                # Initialize conversational retrieval chain
                await self._initialize_rag_chain()
            
            # Test AI model connection
            await self.health_check()
            
            logger.info("AI engine components initialized successfully")
            
        except Exception as e:
            logger.error("Failed to initialize AI engine", error=str(e))
            raise
    
    async def generate_response(
        self,
        conversation: Any,  # Conversation object
        user_message: Any,  # ConversationMessage object
        context: Dict[str, Any]
    ) -> str:
        """Generate AI response for healthcare conversation."""
        try:
            # Extract user input
            user_input = user_message.redacted_content or user_message.content
            
            # Build conversation context
            conversation_history = self._build_conversation_history(conversation)
            
            # Get relevant documents if RAG is enabled
            relevant_docs = []
            if self.settings.rag_enabled and self.vector_store:
                relevant_docs = await self.vector_store.similarity_search(
                    user_input, k=3
                )
            
            # Build prompt based on conversation type and context
            prompt = self._build_healthcare_prompt(
                user_input=user_input,
                conversation_history=conversation_history,
                relevant_docs=relevant_docs,
                context=context,
                language=conversation.language
            )
            
            # Generate response using OpenAI
            response = await self._generate_ai_response(prompt, conversation.language)
            
            # Post-process response for healthcare compliance
            processed_response = self._post_process_response(response, context)
            
            logger.info(
                "AI response generated successfully",
                conversation_id=conversation.id,
                user_input_length=len(user_input),
                response_length=len(processed_response)
            )
            
            return processed_response
            
        except Exception as e:
            logger.error(
                "Failed to generate AI response",
                conversation_id=conversation.id,
                error=str(e),
                exc_info=True
            )
            
            # Return fallback response
            return self._get_fallback_response(conversation.language)
    
    async def health_check(self) -> bool:
        """Health check for AI engine."""
        try:
            # Test AI model with simple prompt
            test_prompt = "Respond with 'OK' if you can process this message."
            
            if self.settings.ai_provider == "openai":
                response = await openai.ChatCompletion.acreate(
                    model=self.ai_config["model"],
                    messages=[{"role": "user", "content": test_prompt}],
                    max_tokens=10,
                    temperature=0
                )
                
                if "OK" in response.choices[0].message.content:
                    return True
            
            return False
            
        except Exception as e:
            logger.error("AI engine health check failed", error=str(e))
            return False
    
    async def _initialize_rag_chain(self) -> None:
        """Initialize the RAG conversational chain."""
        if not self.vector_store:
            return
        
        try:
            # Create memory for conversation history
            memory = ConversationBufferMemory(
                memory_key="chat_history",
                return_messages=True,
                output_key="answer"
            )
            
            # Create retrieval chain
            self.conversational_chain = ConversationalRetrievalChain.from_llm(
                llm=self._get_langchain_llm(),
                retriever=self.vector_store.get_retriever(),
                memory=memory,
                return_source_documents=True,
                verbose=self.settings.development_mode
            )
            
            logger.info("RAG conversational chain initialized")
            
        except Exception as e:
            logger.error("Failed to initialize RAG chain", error=str(e))
            raise
    
    def _get_langchain_llm(self):
        """Get LangChain LLM instance."""
        if self.settings.ai_provider == "openai":
            from langchain.llms import OpenAI
            return OpenAI(
                openai_api_key=self.ai_config["api_key"],
                model_name=self.ai_config["model"],
                temperature=self.ai_config["temperature"],
                max_tokens=self.ai_config["max_tokens"]
            )
        else:
            raise ValueError(f"Unsupported AI provider: {self.settings.ai_provider}")
    
    def _build_conversation_history(self, conversation: Any) -> List[Dict[str, str]]:
        """Build conversation history for context."""
        history = []
        
        # Get last 10 messages for context (limit for token management)
        recent_messages = conversation.messages[-10:] if len(conversation.messages) > 10 else conversation.messages
        
        for message in recent_messages:
            if message.type.value in ["user", "assistant"]:
                content = message.redacted_content or message.content
                history.append({
                    "role": "user" if message.type.value == "user" else "assistant",
                    "content": content
                })
        
        return history
    
    def _build_healthcare_prompt(
        self,
        user_input: str,
        conversation_history: List[Dict[str, str]],
        relevant_docs: List[str],
        context: Dict[str, Any],
        language: str = "en"
    ) -> List[Dict[str, str]]:
        """Build healthcare-specific prompt with context."""
        
        # Get system prompt for healthcare
        system_prompt = self.system_prompts.get(language, self.system_prompts["en"])
        
        # Add relevant documents to context if available
        context_info = ""
        if relevant_docs:
            context_info = "\n\nRelevant medical information:\n" + "\n".join(relevant_docs[:2])
        
        # Build user context information
        user_context = ""
        if context.get("user_profile"):
            profile = context["user_profile"]
            user_context = f"\nPatient context: {profile.get('age_group', '')}, {profile.get('conditions', '')}"
        
        # Construct messages
        messages = [
            {"role": "system", "content": system_prompt + context_info + user_context}
        ]
        
        # Add conversation history
        messages.extend(conversation_history)
        
        # Add current user input
        messages.append({"role": "user", "content": user_input})
        
        return messages
    
    async def _generate_ai_response(self, messages: List[Dict[str, str]], language: str) -> str:
        """Generate AI response using OpenAI."""
        if self.settings.ai_provider == "openai":
            try:
                response = await openai.ChatCompletion.acreate(
                    model=self.ai_config["model"],
                    messages=messages,
                    max_tokens=self.ai_config["max_tokens"],
                    temperature=self.ai_config["temperature"],
                    presence_penalty=0.1,
                    frequency_penalty=0.1,
                    user="medinovai_healthcare"  # For usage tracking
                )
                
                return response.choices[0].message.content.strip()
                
            except Exception as e:
                logger.error("OpenAI API error", error=str(e))
                raise
        
        else:
            raise ValueError(f"Unsupported AI provider: {self.settings.ai_provider}")
    
    def _post_process_response(self, response: str, context: Dict[str, Any]) -> str:
        """Post-process AI response for healthcare compliance."""
        
        # Remove any potential PHI that might have been generated
        processed_response = response
        
        # Add disclaimers for medical advice
        if self._contains_medical_advice(response):
            disclaimer = self._get_medical_disclaimer(context.get("language", "en"))
            processed_response += f"\n\n{disclaimer}"
        
        # Ensure appropriate tone and language
        processed_response = self._ensure_professional_tone(processed_response)
        
        return processed_response
    
    def _contains_medical_advice(self, response: str) -> bool:
        """Check if response contains medical advice requiring disclaimer."""
        medical_keywords = [
            "diagnose", "diagnosis", "treatment", "medication", "prescribe",
            "symptom", "condition", "disease", "therapy", "medical advice"
        ]
        
        response_lower = response.lower()
        return any(keyword in response_lower for keyword in medical_keywords)
    
    def _get_medical_disclaimer(self, language: str) -> str:
        """Get medical disclaimer in appropriate language."""
        disclaimers = {
            "en": "⚠️ This information is for educational purposes only and should not replace professional medical advice. Please consult with your healthcare provider for personalized medical guidance.",
            "es": "⚠️ Esta información es solo para fines educativos y no debe reemplazar el consejo médico profesional. Consulte con su proveedor de atención médica para obtener orientación médica personalizada.",
            "zh": "⚠️ 此信息仅供教育目的，不应替代专业医疗建议。请咨询您的医疗保健提供者以获得个性化的医疗指导。",
            "hi": "⚠️ यह जानकारी केवल शैक्षिक उद्देश्यों के लिए है और पेशेवर चिकित्सा सलाह का विकल्प नहीं होनी चाहिए। व्यक्तिगत चिकित्सा मार्गदर्शन के लिए कृपया अपने स्वास्थ्य सेवा प्रदाता से सलाह लें।"
        }
        
        return disclaimers.get(language, disclaimers["en"])
    
    def _ensure_professional_tone(self, response: str) -> str:
        """Ensure response maintains professional healthcare tone."""
        # Remove casual language, add empathy markers, etc.
        # This would include more sophisticated NLP processing in production
        return response
    
    def _get_fallback_response(self, language: str) -> str:
        """Get fallback response when AI fails."""
        fallbacks = {
            "en": "I apologize, but I'm having difficulty processing your request right now. Let me connect you with one of our healthcare specialists who can assist you better.",
            "es": "Me disculpo, pero tengo dificultades para procesar su solicitud en este momento. Permíteme conectarte con uno de nuestros especialistas en atención médica que puede ayudarte mejor.",
            "zh": "很抱歉，我现在处理您的请求有困难。让我为您联系我们的医疗保健专家，他们可以更好地为您提供帮助。",
            "hi": "मुझे खेद है, लेकिन मुझे अभी आपके अनुरोध को संसाधित करने में कठिनाई हो रही है। मुझे आपको हमारे स्वास्थ्य विशेषज्ञों में से किसी एक से जोड़ने दें जो आपकी बेहतर सहायता कर सकते हैं।"
        }
        
        return fallbacks.get(language, fallbacks["en"])
    
    def _load_healthcare_prompts(self) -> Dict[str, str]:
        """Load healthcare-specific system prompts."""
        return {
            "en": """You are MedinovAI, an AI healthcare assistant for myOnsite Healthcare. You provide helpful, accurate, and empathetic responses to healthcare-related questions while maintaining strict HIPAA compliance.

Core Guidelines:
- Always maintain a professional, caring, and empathetic tone
- Provide accurate medical information based on established guidelines
- Never diagnose medical conditions or prescribe treatments
- Always recommend consulting healthcare professionals for medical decisions
- Protect patient privacy and never request or store PHI unnecessarily
- If uncertain, escalate to human healthcare professionals
- Provide culturally sensitive and inclusive responses
- Focus on patient education and empowerment

Response Structure:
1. Acknowledge the patient's concern with empathy
2. Provide relevant, evidence-based information
3. Include appropriate medical disclaimers
4. Offer next steps or recommend professional consultation when needed
5. Maintain HIPAA compliance throughout

Remember: You are a healthcare assistant, not a replacement for professional medical care.""",

            "es": """Eres MedinovAI, un asistente de IA para el cuidado de la salud de myOnsite Healthcare. Proporcionas respuestas útiles, precisas y empáticas a preguntas relacionadas con la atención médica mientras mantienes estricto cumplimiento de HIPAA.

Pautas Principales:
- Siempre mantén un tono profesional, cariñoso y empático
- Proporciona información médica precisa basada en pautas establecidas
- Nunca diagnostiques condiciones médicas o prescribas tratamientos
- Siempre recomienda consultar a profesionales de la salud para decisiones médicas
- Protege la privacidad del paciente y nunca solicites o almacenes PHI innecesariamente
- Si no estás seguro, escala a profesionales de la salud humanos
- Proporciona respuestas culturalmente sensibles e inclusivas
- Enfócate en la educación y el empoderamiento del paciente""",

            "zh": """你是MedinovAI，myOnsite Healthcare的AI医疗助手。你提供有用、准确和富有同理心的医疗相关问题回答，同时严格遵守HIPAA合规性。

核心指导原则：
- 始终保持专业、关怀和富有同理心的语调
- 基于既定指南提供准确的医疗信息
- 从不诊断医疗状况或开处方
- 始终建议咨询医疗专业人员进行医疗决策
- 保护患者隐私，不必要地请求或存储PHI
- 如果不确定，升级到人类医疗专业人员
- 提供文化敏感和包容性的回应
- 专注于患者教育和赋权""",

            "hi": """आप MedinovAI हैं, myOnsite Healthcare के लिए एक AI स्वास्थ्य सहायक। आप HIPAA अनुपालन बनाए रखते हुए स्वास्थ्य संबंधी प्रश्नों के लिए सहायक, सटीक और सहानुभूतिपूर्ण उत्तर प्रदान करते हैं।

मुख्य दिशानिर्देश:
- हमेशा एक पेशेवर, देखभाल करने वाला और सहानुभूतिपूर्ण स्वर बनाए रखें
- स्थापित दिशानिर्देशों के आधार पर सटीक चिकित्सा जानकारी प्रदान करें
- कभी भी चिकित्सा स्थितियों का निदान न करें या उपचार निर्धारित न करें
- चिकित्सा निर्णयों के लिए हमेशा स्वास्थ्य पेशेवरों से सलाह लेने की सिफारिश करें
- रोगी की गोपनीयता की रक्षा करें और अनावश्यक रूप से PHI का अनुरोध या भंडारण न करें
- यदि अनिश्चित हों, तो मानव स्वास्थ्य पेशेवरों के पास भेज दें
- सांस्कृतिक रूप से संवेदनशील और समावेशी प्रतिक्रियाएं प्रदान करें
- रोगी शिक्षा और सशक्तिकरण पर ध्यान दें"""
        }
    
    async def cleanup(self) -> None:
        """Cleanup AI engine resources."""
        logger.info("Cleaning up AI engine...")
        
        if self.vector_store:
            await self.vector_store.cleanup()
        
        if self.document_processor:
            await self.document_processor.cleanup()
        
        logger.info("AI engine cleanup complete") 