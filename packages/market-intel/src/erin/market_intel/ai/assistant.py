"""AI Research Assistant - Main assistant orchestrating all capabilities."""

import asyncio
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Any, AsyncIterator, Callable
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    pass

from erin.market_intel.ai.rag import RAGPipeline, RAGConfig, GenerationMode, RetrievalStrategy
from erin.market_intel.ai.tools import ToolRegistry, ToolExecutor, ApprovalManager, ToolDefinition, ToolCall, ToolSensitivity, SandboxProfile
from erin.market_intel.macro.news import NewsIngestionPipeline, NewsArticle, NewsCategory, NewsSource
from erin.market_intel.macro import NLPProcessor

logger = logging.getLogger(__name__)


class AssistantMode(str, Enum):
    CHAT = "CHAT"
    RESEARCH = "RESEARCH"
    ANALYSIS = "ANALYSIS"
    REPORT = "REPORT"
    TRADING = "TRADING"
    BACKTEST = "BACKTEST"


@dataclass
class ConversationMessage:
    """Single message in conversation."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    role: str = "user"  # user, assistant, system, tool
    content: str = ""
    tool_calls: List[Dict] = field(default_factory=list)
    tool_results: List[Dict] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    metadata: Dict = field(default_factory=dict)


@dataclass
class Conversation:
    """Conversation session."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str = ""
    mode: AssistantMode = AssistantMode.CHAT
    messages: List[ConversationMessage] = field(default_factory=list)
    context: Dict = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    def add_message(self, role: str, content: str, **kwargs) -> ConversationMessage:
        msg = ConversationMessage(role=role, content=content, **kwargs)
        self.messages.append(msg)
        self.updated_at = datetime.utcnow()
        return msg
    
    def get_history(self, limit: int = 20) -> List[ConversationMessage]:
        return self.messages[-limit:]


class AIAssistant:
    """Main AI Research Assistant for financial analysis."""
    
    def __init__(
        self,
        rag_config: 'RAGConfig' = None,
        tool_registry: 'ToolRegistry' = None,
        enable_tools: bool = True
    ):
        from erin.market_intel.ai.rag import RAGPipeline, RAGConfig
        from erin.market_intel.ai.tools import ToolRegistry, ToolExecutor, ApprovalManager
        
        self.rag_config = rag_config or RAGConfig()
        self.rag = RAGPipeline(self.rag_config)
        
        self.tool_registry = tool_registry or ToolRegistry()
        self.tool_executor = ToolExecutor(self.tool_registry) if enable_tools else None
        self.approval_manager = ApprovalManager(self.tool_executor) if enable_tools else None
        
        # Session management
        self.conversations: Dict[str, Conversation] = {}
        self.current_conversation: Optional[Conversation] = None
        
        # Callbacks
        self._on_message: Optional[Callable] = None
        self._on_tool_call: Optional[Callable] = None
        self._on_thinking: Optional[Callable] = None
    
    def create_conversation(self, user_id: str, mode: 'AssistantMode' = None) -> Conversation:
        """Create new conversation."""
        conv = Conversation(
            user_id=user_id,
            mode=mode or AssistantMode.CHAT
        )
        self.conversations[conv.id] = conv
        self.current_conversation = conv
        return conv
    
    def get_conversation(self, conv_id: str) -> Optional[Conversation]:
        return self.conversations.get(conv_id)
    
    def set_mode(self, mode: 'AssistantMode'):
        if self.current_conversation:
            self.current_conversation.mode = mode
    
    def register_callback(self, event: str, callback: Callable):
        if event == "on_message":
            self._on_message = callback
        elif event == "on_tool_call":
            self._on_tool_call = callback
        elif event == "on_thinking":
            self._on_thinking = callback
    
    async def chat(self, message: str, conv_id: str = None) -> str:
        """Main chat interface."""
        # Get or create conversation
        if conv_id:
            conv = self.get_conversation(conv_id)
        else:
            conv = self.current_conversation or self.create_conversation("default")
        
        if not conv:
            conv = self.create_conversation("default")
        
        # Add user message
        conv.add_message("user", message)
        
        # Process based on mode
        if conv.mode == AssistantMode.RESEARCH:
            response = await self._research_mode(conv, message)
        elif conv.mode == AssistantMode.ANALYSIS:
            response = await self._analysis_mode(conv, message)
        elif conv.mode == AssistantMode.REPORT:
            response = await self._report_mode(conv, message)
        elif conv.mode == AssistantMode.TRADING:
            response = await self._trading_mode(conv, message)
        elif conv.mode == AssistantMode.BACKTEST:
            response = await self._backtest_mode(conv, message)
        else:
            response = await self._chat_mode(conv, message)
        
        # Add assistant response
        conv.add_message("assistant", response)
        
        # Notify callback
        if self._on_message:
            await self._on_message(conv, response)
        
        return response
    
    async def _chat_mode(self, conv: Conversation, message: str) -> str:
        """General chat mode with RAG."""
        # Use RAG for knowledge retrieval
        result = await self.rag.query(message, GenerationMode.CHAT)
        
        # If tools enabled and query suggests tool use, execute tools
        if self.tool_executor and self._should_use_tools(message):
            tool_results = await self._execute_relevant_tools(message)
            # Would integrate tool results into response
        
        return result["answer"]
    
    async def _research_mode(self, conv: Conversation, message: str) -> str:
        """Deep research mode."""
        # Use RAG with analysis mode
        result = await self.rag.query(
            message,
            mode=GenerationMode.ANALYSIS,
            top_k=15
        )
        
        return result["answer"]
    
    async def _analysis_mode(self, conv: Conversation, message: str) -> str:
        """Financial analysis mode."""
        # Check if asking about specific ticker
        from erin.market_intel.macro import NLPProcessor
        nlp = NLPProcessor()
        tickers = await nlp.extract_tickers(message)
        
        if tickers:
            # Analyze specific tickers
            results = []
            for ticker in tickers[:3]:  # Limit to 3 tickers
                analysis = await self.rag.analyze_ticker(ticker, message)
                results.append(f"## {ticker}\n{analysis.get('analysis', 'No analysis available')}")
            
            return "\n\n".join(results)
        else:
            # General analysis using RAG
            result = await self.rag.query(message, mode=GenerationMode.ANALYSIS)
            return result["answer"]
    
    async def _report_mode(self, conv: Conversation, message: str) -> str:
        """Report generation mode."""
        # Extract topic and tickers
        from erin.market_intel.macro import NLPProcessor
        nlp = NLPProcessor()
        tickers = await nlp.extract_tickers(message)
        
        report = await self.rag.generate_report(
            topic=message,
            tickers=tickers if tickers else None
        )
        
        return report.get("report", "Unable to generate report")
    
    async def _trading_mode(self, conv: Conversation, message: str) -> str:
        """Trading assistance mode."""
        # Would use trading tools
        return "Trading mode: Would help with order placement, position management, risk checks"
    
    async def _backtest_mode(self, conv: Conversation, message: str) -> str:
        """Backtesting mode."""
        return "Backtest mode: Would run strategy backtest with given parameters"
    
    def _should_use_tools(self, message: str) -> bool:
        """Determine if message suggests tool use."""
        tool_keywords = [
            "price", "quote", "chart", "indicator", "backtest",
            "optimize", "var", "stress test", "monte carlo",
            "factor", "fundamental", "earnings", "news",
            "calendar", "optimize", "portfolio"
        ]
        return any(kw in message.lower() for kw in tool_keywords)
    
    async def _execute_relevant_tools(self, message: str) -> List[Dict]:
        """Execute relevant tools based on message."""
        # Would parse message and execute relevant tools
        return []
    
    async def analyze_ticker(self, ticker: str, question: str = None) -> Dict:
        """Analyze a specific ticker."""
        return await self.rag.analyze_ticker(ticker, question)
    
    async def generate_report(self, topic: str, tickers: List[str] = None) -> Dict:
        """Generate comprehensive report."""
        return await self.rag.generate_report(topic, tickers)
    
    async def run_backtest(self, strategy: str, symbols: List[str], start: date, end: date) -> Dict:
        """Run backtest."""
        if self.tool_executor:
            return await self.tool_executor.execute(
                "run_backtest",
                {"strategy": strategy, "symbols": symbols},
                "assistant", "assistant"
            )
        return {"error": "Tools not enabled"}
    
    async def optimize_portfolio(self, symbols: List[str], method: str = "max_sharpe") -> Dict:
        """Optimize portfolio."""
        if self.tool_executor:
            return await self.tool_executor.execute(
                "optimize_portfolio",
                {"symbols": symbols, "method": method},
                "assistant", "assistant"
            )
        return {"error": "Tools not enabled"}
    
    def get_tool_schemas(self) -> List[Dict]:
        """Get tool schemas for LLM function calling."""
        if self.tool_registry:
            return self.tool_registry.get_schemas()
        return []
    
    def get_available_tools(self) -> List[str]:
        if self.tool_registry:
            return [t.name for t in self.tool_registry.list_tools()]
        return []


class AssistantSession:
    """Manages assistant session state."""
    
    def __init__(self, assistant: AIAssistant, user_id: str):
        self.assistant = assistant
        self.user_id = user_id
        self.conversation = assistant.create_conversation(user_id)
    
    async def send(self, message: str) -> str:
        return await self.assistant.chat(message, self.conversation.id)
    
    def get_history(self, limit: int = 20) -> List:
        return self.conversation.get_history(limit)
    
    def set_mode(self, mode: 'AssistantMode'):
        self.assistant.set_mode(mode)


def create_ai_assistant(
    rag_config: 'RAGConfig' = None,
    tool_registry: 'ToolRegistry' = None,
    enable_tools: bool = True
) -> AIAssistant:
    return AIAssistant(rag_config, tool_registry, enable_tools)


def create_assistant_session(assistant: AIAssistant, user_id: str) -> AssistantSession:
    return AssistantSession(assistant, user_id)