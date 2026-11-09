# ADR 012: AI Research Assistant Architecture

## Status
Accepted

## Context
ERIN 2.0 needs an AI-powered research assistant that can:
- Answer financial questions using RAG over market data, news, and research
- Execute analytical tools (VaR, optimization, backtesting, factor models)
- Generate reports and analyses on tickers, sectors, and macro themes
- Maintain conversation context and tool-use history
- Operate within security boundaries (sandboxed tool execution, approval workflows)

## Decision
We will implement a modular AI Research Assistant with the following components:

1. **RAG Pipeline** - Retrieval-Augmented Generation over financial documents, news, and market data
2. **Tool Registry & Executor** - 15+ financial tools with sandboxed execution, approval workflows
3. **AI Assistant Orchestrator** - Multi-mode conversational agent (CHAT, RESEARCH, ANALYSIS, REPORT, TRADING, BACKTEST)
4. **Approval Manager** - Human-in-the-loop for HIGH/CRITICAL sensitivity tools
5. **Session Management** - Persistent conversations with tool-use history

## Consequences
- Enables natural-language financial research and analysis
- Provides audit trail for all tool executions
- Supports human-in-the-loop for sensitive operations
- Extensible tool registry for new analytical capabilities
- Integrates with existing ERIN data infrastructure (RAG, tools, market data)

## Implementation Status
- ✅ RAG Pipeline (rag.py)
- ✅ Tool Registry & Executor (tools.py)
- ✅ AI Assistant Orchestrator (assistant.py)
- ✅ Tool Definitions (15+ financial tools)
- ✅ Approval Manager for sensitive operations
- ✅ RAG Pipeline with Hybrid Retrieval
- ✅ Document Chunking & Embedding
- ✅ Vector Store + Keyword Retrieval (Hybrid)
- ✅ Generator with multiple modes (SUMMARY, ANALYSIS, REPORT, QA, FORECAST)
- ⏳ Phase 12: AI Research Assistant - **COMPLETE**