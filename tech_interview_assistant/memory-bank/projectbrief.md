# Project Brief: Tech Interview Assistant

## Project Overview
The Tech Interview Assistant is a multi-agent system built with LangChain and LangGraph designed to help candidates prepare for data science technical interviews. It automates the collection, solution generation, and retrieval of technical interview questions, providing high-quality solutions with reflection capabilities.

## Core Objectives
1. Automate the collection of data science interview questions from various sources
2. Generate high-quality solutions to these questions using LLM-based solvers
3. Improve solutions through reflection and error detection
4. Store questions and solutions in a vector database for efficient retrieval
5. Enable semantic search to find similar questions and solutions
6. Provide a comprehensive system for technical interview preparation

## Target Users
- Data science job candidates preparing for technical interviews
- Students learning data science concepts through practice problems
- Educators looking for quality solutions to technical questions
- Professionals seeking to refresh their technical knowledge

## Key Features
1. **Email Question Collection**: Automatically extracts questions from subscribed newsletters in Gmail
2. **Solution Generation**: Creates high-quality solutions using LLM-based solvers
3. **Solution Reflection**: Improves solutions through reflection and error detection
4. **Vector Database Storage**: Stores questions and solutions for semantic search
5. **Hybrid Retrieval**: Combines BM25 and vector search for better results
6. **Web Scraping**: Collects questions and solutions from web pages
7. **Job Tracking**: Monitors job runs and metrics for incremental processing

## Project Scope
### In Scope
- Processing questions from email sources (particularly interviewquery.com)
- Generating Python-based solutions for data science questions
- Storing and retrieving questions and solutions
- Web scraping for additional questions
- Command-line interface for system interaction
- Incremental updates to process new emails

### Out of Scope (Future Enhancements)
- Real-time mock interview simulation
- User interface beyond command-line
- Integration with additional learning resources
- Personalized learning paths
- Performance analytics and improvement suggestions

## Success Criteria
1. Successfully extract questions from email sources
2. Generate technically accurate and complete solutions
3. Improve solutions through reflection
4. Enable efficient retrieval of similar questions
5. Support incremental processing of new questions
6. Provide a usable command-line interface

This project aims to create a comprehensive system that streamlines technical interview preparation by automating the collection, solution generation, and retrieval of data science interview questions.
