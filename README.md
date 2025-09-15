
# Code Quality Intelligence Agent (CQIA)

## Overview
The **Code Quality Intelligence Agent (CQIA)** is an AI-powered system designed to analyze code repositories, 
detect quality issues, and provide actionable, developer-friendly insights. Unlike simple linters, CQIA goes deeper 
with structural understanding, multi-language support, and interactive Q&A capabilities.

## Features

### Core Features
- Analyze code repositories (local folders or GitHub URLs)
- Multi-language support (Python, JavaScript)
- Detect issues: security, performance, duplication, complexity, missing tests
- Generate reports with severity scoring
- Interactive Q&A interface

### Advanced Features (Super Stretch)
- RAG (Retrieval-Augmented Generation) for large codebases
- AST-based parsing for precise analysis
- Agentic workflows for reasoning & fix suggestions
- Automated severity scoring
- Developer visualizations: dependency graphs, hotspots, trends
- GitHub integration for PR reviews / CI checks

## Technologies Used
- **Python 3.11**
- **FastAPI** (Web API layer)
- **Typer** (CLI interface)
- **LangChain / LangGraph** (LLM orchestration)
- **OpenAI GPT models** (LLM reasoning)
- **FAISS** (Vector store for RAG)
- **Tree-sitter** (JavaScript parsing)
- **Python AST** (Python parsing)
- **ReportLab** (Reports)
- **Matplotlib / NetworkX** (Visualizations)
- **Redis + Celery** (Job queue)
- **GitHub API** (Integrations)

## System Architecture
The CQIA system is designed with modular, clean architecture. Below is a high-level view of components:

```
CLI / API <-> Agent Controller
             |
             v
       +-----------+
       | Analyzers | ---> Reporter
       +-----------+
             |
       +-----------+
       | AST Parser|
       +-----------+
             |
    +----------------+
    | FAISS / RAG    |
    +----------------+
             |
       Q&A Service
             |
   GitHub Integration
             |
   Visualization Dashboard
```

## Setup Instructions
1. Clone the repository
2. Install dependencies:  
   ```bash
   pip install -r requirements.txt
   ```
3. Run analysis:  
   ```bash
   cqia analyze <path-to-repo> --use-llm true
   ```
4. Generate reports:  
   ```bash
   cqia report
   ```
5. Ask questions:  
   ```bash
   cqia qa "Which files are most complex?"
   ```

### Deployment Options
- Local CLI
- FastAPI Web API
- Optional GitHub PR review bot

## Challenges & Solutions
- **Large codebases** → Solved using RAG and vector stores
- **Multi-language parsing** → Abstracted analyzer interface
- **Actionable insights** → Severity scoring + AI-generated explanations
- **Privacy concerns** → Configurable LLM usage, local embeddings

## Closing Notes
CQIA is a practical, intelligent tool for improving developer productivity and code quality.  
Its combination of static analysis, AI-powered reasoning, and developer-friendly reports make it a powerful assistant 
for modern software teams.
