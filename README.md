# MCP LlamaIndex SQLite Bridge

A comprehensive demonstration of Model Context Protocol (MCP) with SQLite integration and LlamaIndex client, featuring both a simple demo and a full-featured HR Management System.

## Overview

This project showcases how to build and use MCP servers that expose database operations as tools, connected via LlamaIndex-based clients with Ollama LLM support. It includes:

1. **Simple Demo** - Basic SQLite server with simple people table
2. **HR Management System** - Advanced natural language HR system with employee management, leave tracking, compensation, and analytics

### Components

#### Simple Demo:
- **server.py**: Basic MCP server with SQL tools for a simple people database
- **client.py**: LlamaIndex client for natural language database interactions

#### HR Management System:
- **hr_server.py**: Advanced MCP server with comprehensive HR tools
- **hr_client.py**: Sophisticated client with context-aware natural language processing
- **HR_USAGE_GUIDE.md**: Detailed documentation with examples

## Features

### Core Features
- MCP server architecture with SQLite integration
- Natural language interface using LlamaIndex and Ollama
- Async support for both server and client
- Tool-based approach for database operations

### HR Management System Features
- **Employee Management**: Add, update, search, and manage employee records
- **Leave Management**: Request, approve, and track employee leave balances
- **Compensation**: Salary updates, compensation reports, and payroll analytics
- **Organization Structure**: Org charts, department management, and transfers
- **Analytics**: HR dashboards, turnover analysis, and diversity metrics
- **Performance Reviews**: Create and track performance evaluations
- **Audit Trail**: Complete logging of all HR actions for compliance

## Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) installed and running
- llama3.2 model (or another model that supports tool calling)

## ⚠️ Critical Requirements

### Email is REQUIRED When Adding Employees
The HR system **requires an email address** when adding new employees. Commands without email will fail.

❌ **WRONG**: `Add John Doe to Engineering as Developer`  
✅ **CORRECT**: `Add John Doe (john.doe@company.com) to Engineering as Developer`

Without email, you'll see: `❌ Tool failed: Missing required field: email`

## Installation

1. Clone this repository:
```bash
git clone https://github.com/ELISHA1994/mcp-llama-sqlite-bridge.git
cd mcp-llama-sqlite-bridge
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

### Option 1: Simple Demo

#### Starting the Simple Server
```bash
python server.py --server_type=sse
```

#### Running the Simple Client
```bash
python client.py
```

### Option 2: HR Management System

#### Starting the HR Server
```bash
python hr_server.py --server_type=sse
```

#### Running the HR Client
```bash
python hr_client.py
```

The client will:
1. Connect to the MCP server
2. Display available tools
3. Start an interactive session where you can use natural language to interact with the database

### Example Interactions

#### Simple Demo:
```
Enter your message: Add a person named John Doe who is 30 years old and works as an Engineer
Agent: Data has been successfully added to the database.

Enter your message: Show me all people in the database
Agent: Here are all the people in the database:
1. John Doe, 30 years old, Engineer
```

#### HR Management System:

⚠️ **IMPORTANT: Email is REQUIRED when adding employees!**

```
HR Assistant> Add Sarah Johnson (sarah.johnson@company.com) to Engineering as Senior Developer with $105,000 salary

🔧 Calling tool: add_employee
✅ Employee added successfully!
- Employee ID: EMP00001
- Name: Sarah Johnson

HR Assistant> 

🔧 Calling tool: check_employee_leave_balance
   Parameters: {
     "employee_name": "Sarah Johnson"
   }
✅ Tool result received
**Leave Balance for Sarah Johnson (2024)**
- Annual Leave: 21 days remaining
- Sick Leave: 10 days remaining

HR Assistant> Generate HR dashboard

🔧 Calling tool: generate_hr_dashboard
**HR Dashboard Summary**
- Total Employees: 45
- Active: 42
- Departments: Engineering (15), Sales (10), Marketing (8)...
```

### Natural Language Examples

#### Employee Management

**Adding Employees (Email Required!):**
```
"Add Elisha Bello (elisha.bello@company.com) to Engineering as Senior Software Engineer with salary $420,000"
"Hire John Doe (john.doe@company.com) as Marketing Manager starting January 15, 2024"
"Onboard Alice Chen (alice.chen@company.com) to Sales as Account Executive, phone: 555-0123"
```

**Searching & Listing:**
```
"List all employees"
"Find all employees in Engineering department"
"Show me employees hired in the last 6 months"
"Who reports to John Smith?"
"Search for Senior Engineers"
```

**Updates & Changes:**
```
"Update John Doe's phone number to 555-9876"
"Transfer Sarah Johnson from Engineering to Product Management"
"Change Michael Brown's manager to Jennifer Wilson"
"Update Emily Davis's salary to $95,000 effective next month"  ← Uses name directly!
```

#### Leave Management

```
"Check Sarah Johnson's leave balance"  ← Uses employee name directly!
"Submit leave request for John Doe from Dec 20 to Dec 27"  ← Uses name!
"Approve leave request #45"
"Show all pending leave requests"
"How many vacation days does Michael Brown have left?"  ← Uses name!
```

#### Compensation & Benefits

```
"Generate compensation report for Engineering department"
"Show average salaries by position"
"Calculate total payroll for Q4 2024"
"List employees eligible for salary review"
"Compare department salary ranges"
```

#### Organization & Analytics

```
"Show org chart for Engineering department"
"Generate HR dashboard"
"Analyze turnover for last quarter"
"Show diversity metrics"
"List employees with upcoming work anniversaries"
"Who are the top performers this quarter?"
```

#### Performance Management

```
"Create performance review for Sarah Johnson"
"Show pending performance reviews"
"Update performance rating for John Doe to 'Exceeds Expectations'"
"List employees due for annual review"
```

For more examples, try the interactive help in the HR client by typing 'help'.

## Database Schema

### Simple Demo Schema

The `demo.db` contains a `people` table:
- `id`: INTEGER PRIMARY KEY AUTOINCREMENT
- `name`: TEXT NOT NULL
- `age`: INTEGER NOT NULL
- `profession`: TEXT NOT NULL

### HR Management System Schema

The `hr_management.db` contains multiple interconnected tables:
- **employees**: Comprehensive employee records
- **departments**: Organizational units and hierarchy
- **positions**: Job titles and salary ranges
- **salaries**: Compensation history
- **leave_types**: Various leave categories
- **leave_balances**: Employee leave entitlements
- **leave_requests**: Leave request tracking
- **performance_reviews**: Performance evaluations
- **training_programs**: Training catalog
- **employee_training**: Training completion records
- **audit_log**: Compliance and audit trail

## Available Tools

### Simple Demo Tools
- **add_data**: Add records using SQL INSERT
- **read_data**: Query records using SQL SELECT

### HR Management Tools

#### Simplified Tools (Use These - They Accept Employee Names!)
- **add_employee**: Add new employees (EMAIL REQUIRED!)
- **check_employee_leave_balance**: Check leave balance by employee NAME
- **update_employee_salary**: Update salary by employee NAME  
- **submit_leave_request**: Submit leave request by employee NAME
- **list_all_employees**: Get all active employees
- **find_employees_by_department**: Search by department

#### Advanced Tools (Require Employee IDs)
- **manage_employee**: Add, update, terminate employees (requires employee_id)
- **search_employees**: Advanced employee search with filters
- **get_org_chart**: Generate organizational hierarchy
- **request_leave**: Submit leave requests (requires employee_id)
- **approve_leave**: Process leave approvals
- **get_leave_balance**: Check leave balances (requires employee_id)
- **update_salary**: Manage compensation (requires employee_id)
- **generate_hr_dashboard**: Comprehensive HR metrics
- **analyze_turnover**: Turnover analytics
- **calculate_compensation_metrics**: Salary statistics
- **record_performance_review**: Performance evaluations
- And many more...

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

### Employee Not Added Issue
If your command to add an employee doesn't work:
- **Check for email**: Email is REQUIRED. Without it, the employee won't be saved.
- **Look for error messages**: "❌ Tool failed: Missing required field: email"
- **Correct format**: `Add Name (email@company.com) to Department as Position`
- Always include email: firstname.lastname@company.com

### Tool Expects Employee ID Error
If you get errors when using employee names:
- **Use the simplified tools**: check_employee_leave_balance, update_employee_salary, submit_leave_request
- **These accept names directly**: "Check John Doe's leave balance"
- **Don't use**: get_leave_balance, update_salary, request_leave with names
- The simplified tools handle name-to-ID lookup automatically

## License

MIT License