import nest_asyncio
import asyncio
from llama_index.tools.mcp import BasicMCPClient, McpToolSpec
from llama_index.core.agent.workflow import FunctionAgent, ToolCallResult, ToolCall
from llama_index.core.workflow import Context
from llama_index.llms.ollama import Ollama
from llama_index.core import Settings
import json
from datetime import datetime
from typing import Dict, Any

# Configure LLM
llm = Ollama(model="llama3.2", request_timeout=120.0)
Settings.llm = llm

# System prompt for the HR assistant
SYSTEM_PROMPT = """\
You are an AI-powered HR Assistant for managing human resources operations.

You have access to comprehensive HR management tools that allow you to:
- Manage employee records (add, update, search, terminate)
- Handle organizational structure and departments
- Process leave requests and manage leave balances
- Update salaries and generate compensation reports
- Track performance reviews
- Generate analytics and dashboards

KEY TOOLS YOU SHOULD USE (USE THESE SIMPLIFIED TOOLS THAT ACCEPT NAMES):
- add_employee: Add new employees
  REQUIRED: first_name, last_name, email, department, position
  OPTIONAL: salary, phone, hire_date
- check_employee_leave_balance: Check leave balance by employee NAME (e.g., "John Doe")
- update_employee_salary: Update salary by employee NAME
- submit_leave_request: Submit leave request by employee NAME
- list_all_employees: Get a list of all active employees
- find_employees_by_department: Search employees by department
- generate_hr_dashboard: Get comprehensive HR metrics

IMPORTANT: For common operations, use the simplified tools above that accept employee names directly.
Only use these tools if you need employee IDs:
- get_leave_balance: Requires employee_id (e.g., "EMP00001")
- request_leave: Requires employee_id
- update_salary: Requires employee_id

CRITICAL RULES:
1. ALWAYS use the simplified tools (check_employee_leave_balance, update_employee_salary, submit_leave_request) when users provide employee names
2. NEVER call add_employee without ALL required fields (especially email)
3. If user doesn't provide email when adding an employee, ASK for it FIRST before calling any tool
4. If a tool returns an error about missing fields, inform the user clearly that the action FAILED
5. When users say "Check Sarah Johnson's leave balance", use check_employee_leave_balance("Sarah Johnson")
6. DO NOT try to pass employee names to tools that require employee_id

When interacting with users:
1. For adding employees, ALWAYS ensure you have: first_name, last_name, email, department, position
2. Always confirm sensitive operations before executing (like terminations or salary changes)
3. Provide clear, professional responses
4. When searching for employees, show relevant details
5. For reports, summarize key findings
6. If an operation fails, explicitly state it failed and why

Remember to maintain confidentiality and professionalism when handling employee data.
"""

# Context understanding prompts for different HR scenarios
CONTEXT_PROMPTS = {
    "employee_query": """
    The user is asking about employee information. Extract:
    - Employee name or ID if mentioned
    - What information they need (contact, position, department, etc.)
    - Whether they want to search or get specific details
    
    CRITICAL for add_employee: Ensure email is provided. If missing, ask for it first!
    """,
    
    "leave_request": """
    The user is dealing with leave management. Identify:
    - Who is requesting leave (employee name/ID)
    - Type of leave (annual, sick, personal, etc.)
    - Date range
    - Whether this is a new request, approval, or balance check
    """,
    
    "salary_compensation": """
    The user is asking about salary/compensation. Determine:
    - Specific employee or department-wide analysis
    - Whether they want to update salary or generate reports
    - Any filters or criteria mentioned
    """,
    
    "organizational": """
    The user is asking about organizational structure. Identify:
    - Department names mentioned
    - Whether they want org chart, department info, or transfers
    - Scope (entire company or specific department)
    """,
    
    "analytics": """
    The user wants reports or analytics. Determine:
    - Type of report (dashboard, turnover, diversity, etc.)
    - Time period
    - Specific departments or filters
    """
}

def interpret_query(query: str) -> Dict[str, Any]:
    """
    Interpret natural language query to determine intent and parameters.
    """
    query_lower = query.lower()
    
    # Employee management keywords
    if any(word in query_lower for word in ['add employee', 'new employee', 'hire', 'onboard']):
        # Check if email is mentioned
        has_email = '@' in query or '.com' in query_lower
        return {
            "intent": "add_employee", 
            "context": "employee_query",
            "has_email": has_email,
            "warning": None if has_email else "Email is required for adding employees"
        }
    elif any(word in query_lower for word in ['find', 'search', 'list employees', 'who works']):
        return {"intent": "search_employees", "context": "employee_query"}
    elif any(word in query_lower for word in ['terminate', 'fire', 'end employment']):
        return {"intent": "terminate_employee", "context": "employee_query"}
    
    # Leave management keywords
    elif any(word in query_lower for word in ['leave request', 'vacation', 'time off', 'pto']):
        if 'approve' in query_lower:
            return {"intent": "approve_leave", "context": "leave_request"}
        elif 'balance' in query_lower or 'remaining' in query_lower:
            return {"intent": "check_leave_balance", "context": "leave_request"}
        else:
            return {"intent": "request_leave", "context": "leave_request"}
    
    # Salary/compensation keywords
    elif any(word in query_lower for word in ['salary', 'pay', 'compensation', 'raise']):
        if 'update' in query_lower or 'change' in query_lower or 'increase' in query_lower:
            return {"intent": "update_salary", "context": "salary_compensation"}
        else:
            return {"intent": "compensation_report", "context": "salary_compensation"}
    
    # Organizational keywords
    elif any(word in query_lower for word in ['org chart', 'organization', 'hierarchy', 'reports to']):
        return {"intent": "org_chart", "context": "organizational"}
    elif any(word in query_lower for word in ['department', 'transfer']):
        return {"intent": "department_management", "context": "organizational"}
    
    # Analytics keywords
    elif any(word in query_lower for word in ['dashboard', 'metrics', 'report', 'analytics']):
        if 'turnover' in query_lower:
            return {"intent": "turnover_analysis", "context": "analytics"}
        else:
            return {"intent": "hr_dashboard", "context": "analytics"}
    
    # Performance management
    elif any(word in query_lower for word in ['performance', 'review', 'evaluation']):
        return {"intent": "performance_review", "context": "employee_query"}
    
    # Default
    return {"intent": "general_query", "context": "employee_query"}

def format_employee_info(employee: Dict[str, Any]) -> str:
    """Format employee information for display."""
    return f"""
**{employee.get('first_name', '')} {employee.get('last_name', '')}** ({employee.get('employee_id', '')})
- Email: {employee.get('email', 'N/A')}
- Department: {employee.get('department_name', 'N/A')}
- Position: {employee.get('position_title', 'N/A')}
- Manager: {employee.get('manager_name', 'N/A')}
- Status: {employee.get('employment_status', 'N/A')}
- Hire Date: {employee.get('hire_date', 'N/A')}
"""

def format_leave_balance(balance_data: Dict[str, Any]) -> str:
    """Format leave balance information."""
    if not balance_data.get('balances'):
        return "No leave balance data available."
    
    output = f"**Leave Balance for {balance_data['employee']} ({balance_data['year']})**\n\n"
    
    for balance in balance_data['balances']:
        output += f"**{balance['leave_type']}**\n"
        output += f"- Entitled: {balance['entitled_days']} days\n"
        output += f"- Used: {balance['used_days']} days\n"
        output += f"- Remaining: {balance['remaining_days']} days\n\n"
    
    if balance_data.get('pending_requests'):
        output += "\n**Pending Requests:**\n"
        for request in balance_data['pending_requests']:
            output += f"- {request['leave_type']}: {request['start_date']} to {request['end_date']} ({request['days_requested']} days)\n"
    
    return output

def format_dashboard(dashboard: Dict[str, Any]) -> str:
    """Format HR dashboard data."""
    stats = dashboard.get('employee_statistics', {})
    
    output = "**HR Dashboard Summary**\n\n"
    output += f"**Employee Statistics:**\n"
    output += f"- Total Employees: {stats.get('total', 0)}\n"
    output += f"- Active: {stats.get('active', 0)}\n"
    output += f"- Full-time: {stats.get('full_time', 0)}\n"
    output += f"- Part-time: {stats.get('part_time', 0)}\n"
    output += f"- Contractors: {stats.get('contractors', 0)}\n\n"
    
    if dashboard.get('department_distribution'):
        output += "**Department Distribution:**\n"
        for dept in dashboard['department_distribution']:
            output += f"- {dept['name']}: {dept['count']} employees\n"
    
    if dashboard.get('recent_activity'):
        activity = dashboard['recent_activity']
        output += f"\n**Recent Activity:**\n"
        output += f"- New hires (90 days): {activity.get('new_hires_90_days', 0)}\n"
        output += f"- Pending reviews: {activity.get('pending_performance_reviews', 0)}\n"
        output += f"- Pending leave requests: {activity.get('pending_leave_requests', 0)}\n"
    
    return output

async def get_agent(tools: McpToolSpec):
    """Create and return a FunctionAgent with the given tools."""
    tools = await tools.to_tool_list_async()
    agent = FunctionAgent(
        name="HRAgent",
        tools=tools,
        llm=llm,
        system_prompt=SYSTEM_PROMPT,
    )
    return agent

async def handle_user_message(
        message_content: str,
        agent: FunctionAgent,
        agent_context: Context,
        verbose: bool = False,
):
    """Handle a user message using the agent with context awareness."""
    # Interpret the query
    query_info = interpret_query(message_content)
    
    if verbose:
        print(f"\nInterpreted intent: {query_info['intent']}")
        if query_info.get('warning'):
            print(f"⚠️ WARNING: {query_info['warning']}")
    
    # Add context to the message if needed
    enhanced_message = message_content
    if query_info['context'] in CONTEXT_PROMPTS:
        enhanced_message = f"{CONTEXT_PROMPTS[query_info['context']]}\n\nUser query: {message_content}"
    
    handler = agent.run(enhanced_message, ctx=agent_context)
    
    async for event in handler.stream_events():
        if verbose and type(event) == ToolCall:
            print(f"🔧 Calling tool: {event.tool_name}")
            if event.tool_kwargs:
                print(f"   Parameters: {json.dumps(event.tool_kwargs, indent=2)}")
        elif verbose and type(event) == ToolCallResult:
            # Check for errors first
            if isinstance(event.tool_output, dict) and event.tool_output.get('success') == False:
                print(f"❌ Tool failed: {event.tool_output.get('error', 'Unknown error')}")
                if 'email' in event.tool_output.get('error', '').lower():
                    print("⚠️ IMPORTANT: Employee was NOT added. Please provide email address.")
            else:
                print(f"✅ Tool result received")
                # Format specific tool results for better display
                if isinstance(event.tool_output, dict):
                    if 'balances' in event.tool_output:
                        print(format_leave_balance(event.tool_output))
                    elif 'employee_statistics' in event.tool_output:
                        print(format_dashboard(event.tool_output))
                    elif isinstance(event.tool_output, list) and len(event.tool_output) > 0:
                        if 'employee_id' in event.tool_output[0]:
                            print(f"\nFound {len(event.tool_output)} employees:")
                            for emp in event.tool_output[:5]:  # Show first 5
                                print(format_employee_info(emp))

    response = await handler
    return str(response)

def print_help():
    """Print help information for the HR system."""
    print("""
📋 **HR Management System - Natural Language Commands**

**Employee Management:**
- "Add Sarah Johnson (sarah.johnson@company.com) to Engineering as Senior Developer with $120k salary"
- "List all employees"
- "Find all employees in Marketing department"
- "Search for employees hired in the last 6 months"
- "Show me John Smith's employee details"
  
⚠️ **IMPORTANT**: Email is REQUIRED when adding employees!

**Leave Management:**
- "Check Sarah Johnson's leave balance"  ← Now works with employee names!
- "Submit leave request for John Doe from Dec 20 to Dec 27"  ← Now works with names!
- "Approve leave request #45"
- "Show all pending leave requests"

**Salary & Compensation:**
- "Update John Doe's salary to $85,000 effective next month"  ← Now works with names!
- "Generate a compensation report for Engineering department"
- "Show average salaries by department"
- "Calculate total payroll for Q4"

**Organization & Structure:**
- "Show the org chart for Engineering"
- "Create a new department called Product Design"
- "Transfer Jane from Sales to Marketing"
- "Who reports to Michael Brown?"

**Analytics & Reports:**
- "Generate HR dashboard"
- "Analyze turnover for the last quarter"
- "Show diversity metrics"
- "List employees with upcoming anniversaries"

**Performance Management:**
- "Create a performance review for Sarah"
- "Show pending performance reviews"
- "List top performers this quarter"

💡 **Tips:**
- Use the simplified 'add employee' format: "Add [name] ([email]) to [department] as [position]"
- ⚠️ EMAIL IS REQUIRED - always include it when adding employees
- Departments and positions are created automatically if they don't exist
- If you forget the email, the employee will NOT be added

Type 'help' to see this message again.
Type 'exit' to quit.
""")

async def main():
    """Initialize MCP client and tool spec."""
    print("🚀 Starting HR Management System Client...")
    print("Connecting to MCP server at http://127.0.0.1:8000/sse\n")
    
    mcp_client = BasicMCPClient("http://127.0.0.1:8000/sse")
    mcp_tool = McpToolSpec(client=mcp_client)
    
    # Get the agent
    agent = await get_agent(mcp_tool)
    
    # Create the agent context
    agent_context = Context(agent)
    
    # Print available tools
    tools = await mcp_tool.to_tool_list_async()
    print(f"✅ Connected! Available HR tools: {len(tools)}\n")
    
    # Show help
    print_help()
    
    # Example queries to demonstrate
    print("\n💡 **Example queries to try:**")
    print("1. 'Generate HR dashboard'")
    print("2. 'List all employees'")
    print("3. 'Add Michael Brown (michael.brown@company.com) to Product as Product Manager with salary $115,000'")
    print("4. 'Find all employees in Engineering department'")
    print("5. 'Check Sarah Johnson's leave balance'  # Uses check_employee_leave_balance automatically")
    print("6. 'Update John Doe's salary to $100,000 effective next month'  # Uses update_employee_salary automatically")
    print("7. 'Submit leave request for Jane Smith from Dec 20 to Dec 27'  # Uses submit_leave_request automatically")
    print("\n⚠️ REMEMBER: Always include EMAIL when adding new employees!\n")
    
    # Main interaction loop
    while True:
        try:
            user_input = input("\n🤔 HR Assistant> ")
            
            if user_input.lower() == "exit":
                print("👋 Goodbye!")
                break
            
            if user_input.lower() == "help":
                print_help()
                continue
            
            print(f"\n👤 You: {user_input}")
            print("\n🤖 Processing...\n")
            
            response = await handle_user_message(user_input, agent, agent_context, verbose=True)
            print(f"\n💬 HR Assistant: {response}")
            
        except KeyboardInterrupt:
            print("\n\n👋 Goodbye!")
            break
        except Exception as e:
            print(f"\n❌ Error: {str(e)}")
            print("Please try rephrasing your request or type 'help' for examples.")

if __name__ == "__main__":
    # Enable nested async loops (needed for Jupyter notebooks)
    nest_asyncio.apply()
    
    # Run the main async function
    asyncio.run(main())