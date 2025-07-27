# MCP SQLite Demo

A demonstration of Model Context Protocol (MCP) with a SQLite server and LlamaIndex client integration.

## Overview

This project showcases how to build and use an MCP server that exposes SQLite database operations as tools, and connect to it using a LlamaIndex-based client with Ollama LLM support.

### Components

- **server.py**: MCP server that provides SQL tools for managing a SQLite database
- **client.py**: LlamaIndex client that connects to the MCP server and uses Ollama for natural language interactions

## Features

- MCP server with SQLite integration
- Tool-based database operations (add_data, read_data)
- Natural language interface using LlamaIndex and Ollama
- Async support for both server and client

## Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) installed and running
- llama3.2 model (or another model that supports tool calling)

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd local-client
```

2. Create a virtual environment:
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Pull the required Ollama model:
```bash
ollama pull llama3.2
```

## Usage

### Starting the MCP Server

In one terminal, start the MCP server:

```bash
python server.py --server_type=sse
```

The server will start on `http://127.0.0.1:8000` and create a SQLite database (`demo.db`) with a `people` table.

### Running the Client

In another terminal, run the client:

```bash
python client.py
```

The client will:
1. Connect to the MCP server
2. Display available tools
3. Start an interactive session where you can use natural language to interact with the database

### Example Interactions

```
Enter your message: Add a person named John Doe who is 30 years old and works as an Engineer
Agent: Data has been successfully added to the database.

Enter your message: Show me all people in the database
Agent: Here are all the people in the database:
1. John Doe, 30 years old, Engineer
```

## Database Schema

The SQLite database contains a `people` table with the following schema:

- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `name`: TEXT NOT NULL
- `age`: INTEGER NOT NULL
- `profession`: TEXT NOT NULL

## Available Tools

### add_data
Adds new data to the people table using a SQL INSERT query.

Example:
```sql
INSERT INTO people (name, age, profession) VALUES ('Alice Smith', 25, 'Developer')
```

### read_data
Reads data from the people table using a SQL SELECT query.

Example:
```sql
SELECT * FROM people WHERE age > 25
```

## Troubleshooting

### ModuleNotFoundError
If you encounter module import errors, ensure all dependencies are installed:
```bash
pip install -r requirements.txt
```

### Ollama Model Error
If you get an error about the model not supporting tools, ensure you're using a model that supports function calling (like llama3.2, mistral, or qwen2.5-coder).

### Connection Issues
Ensure the MCP server is running before starting the client.

## License

MIT License