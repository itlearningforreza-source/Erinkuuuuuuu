"""ERIN Market Intelligence - AI Module."""

from erin.market_intel.ai.rag import (
    RAGPipeline,
    RAGConfig,
    RetrievalStrategy,
    GenerationMode,
    RetrievalResult,
    GenerationResult,
    DocumentChunk,
    DocumentChunker,
    VectorStore,
    EmbeddingProvider,
    KeywordRetriever,
    HybridRetriever,
    Generator,
    create_rag_pipeline,
    create_rag_config,
)

from erin.market_intel.ai.tools import (
    ToolRegistry,
    ToolExecutor,
    ApprovalManager,
    ToolDefinition,
    ToolCall,
    ToolSensitivity,
    SandboxProfile,
    create_tool_registry,
    create_tool_executor,
    create_approval_manager,
)

from erin.market_intel.ai.assistant import (
    AIAssistant,
    AssistantSession,
    AssistantMode,
    Conversation,
    ConversationMessage,
    create_ai_assistant,
    create_assistant_session,
)

__all__ = [
    # RAG
    "RAGPipeline",
    "RAGConfig",
    "RetrievalStrategy",
    "GenerationMode",
    "RetrievalResult",
    "GenerationResult",
    "DocumentChunk",
    "DocumentChunker",
    "VectorStore",
    "EmbeddingProvider",
    "KeywordRetriever",
    "HybridRetriever",
    "Generator",
    "create_rag_pipeline",
    "create_rag_config",
    
    # Tools
    "ToolRegistry",
    "ToolExecutor",
    "ApprovalManager",
    "ToolDefinition",
    "ToolCall",
    "ToolSensitivity",
    "SandboxProfile",
    "create_tool_registry",
    "create_tool_executor",
    "create_approval_manager",
    
    # Assistant
    "AIAssistant",
    "AssistantSession",
    "AssistantMode",
    "Conversation",
    "ConversationMessage",
    "create_ai_assistant",
    "create_assistant_session",
]