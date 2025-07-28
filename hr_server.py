import sqlite3
import argparse
from mcp.server.fastmcp import FastMCP
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
import json
import re

mcp = FastMCP('hr-management-system')

# Database connection management
def get_db_connection():
    conn = sqlite3.connect('hr_management.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the HR management database with all required tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Departments table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            parent_id INTEGER REFERENCES departments(id),
            manager_id INTEGER REFERENCES employees(id),
            budget DECIMAL(15,2),
            cost_center TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Positions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS positions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            department_id INTEGER REFERENCES departments(id),
            level TEXT,
            min_salary DECIMAL(10,2),
            max_salary DECIMAL(10,2),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Employees table (comprehensive)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id TEXT UNIQUE NOT NULL,
            first_name TEXT NOT NULL,
            last_name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            phone TEXT,
            date_of_birth DATE,
            gender TEXT,
            marital_status TEXT,
            address TEXT,
            city TEXT,
            state TEXT,
            country TEXT,
            postal_code TEXT,
            department_id INTEGER REFERENCES departments(id),
            position_id INTEGER REFERENCES positions(id),
            manager_id INTEGER REFERENCES employees(id),
            hire_date DATE NOT NULL,
            employment_status TEXT DEFAULT 'active',
            employment_type TEXT DEFAULT 'full-time',
            work_location TEXT DEFAULT 'office',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Salaries table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS salaries (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER REFERENCES employees(id),
            base_salary DECIMAL(10,2),
            bonus DECIMAL(10,2),
            commission DECIMAL(10,2),
            effective_date DATE,
            end_date DATE,
            currency TEXT DEFAULT 'USD',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Leave types
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leave_types (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            days_per_year INTEGER,
            carry_forward BOOLEAN DEFAULT FALSE,
            max_carry_forward INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Leave balances
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leave_balances (
            employee_id INTEGER REFERENCES employees(id),
            leave_type_id INTEGER REFERENCES leave_types(id),
            year INTEGER,
            entitled_days INTEGER,
            used_days DECIMAL(5,2) DEFAULT 0,
            carried_forward DECIMAL(5,2) DEFAULT 0,
            remaining_days DECIMAL(5,2),
            PRIMARY KEY (employee_id, leave_type_id, year)
        )
    ''')
    
    # Leave requests
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leave_requests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER REFERENCES employees(id),
            leave_type_id INTEGER REFERENCES leave_types(id),
            start_date DATE,
            end_date DATE,
            days_requested DECIMAL(5,2),
            reason TEXT,
            status TEXT DEFAULT 'pending',
            approved_by INTEGER REFERENCES employees(id),
            approved_date TIMESTAMP,
            comments TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Performance reviews
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS performance_reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            employee_id INTEGER REFERENCES employees(id),
            reviewer_id INTEGER REFERENCES employees(id),
            review_period_start DATE,
            review_period_end DATE,
            overall_rating INTEGER CHECK(overall_rating >= 1 AND overall_rating <= 5),
            goals_achieved TEXT,
            areas_of_improvement TEXT,
            accomplishments TEXT,
            next_review_date DATE,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Training programs
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS training_programs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            description TEXT,
            duration_hours INTEGER,
            is_mandatory BOOLEAN DEFAULT FALSE,
            department_specific INTEGER REFERENCES departments(id),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Employee training records
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS employee_training (
            employee_id INTEGER REFERENCES employees(id),
            training_id INTEGER REFERENCES training_programs(id),
            enrollment_date DATE,
            completion_date DATE,
            score DECIMAL(5,2),
            certificate_url TEXT,
            status TEXT DEFAULT 'enrolled',
            PRIMARY KEY (employee_id, training_id)
        )
    ''')
    
    # Audit log for compliance
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            entity_id INTEGER,
            old_values TEXT,
            new_values TEXT,
            ip_address TEXT,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Insert default leave types
    cursor.execute('''
        INSERT OR IGNORE INTO leave_types (name, days_per_year, carry_forward, max_carry_forward)
        VALUES 
            ('Annual Leave', 21, TRUE, 10),
            ('Sick Leave', 10, FALSE, 0),
            ('Personal Leave', 5, FALSE, 0),
            ('Maternity Leave', 90, FALSE, 0),
            ('Paternity Leave', 14, FALSE, 0),
            ('Bereavement Leave', 3, FALSE, 0)
    ''')
    
    conn.commit()
    conn.close()

# Helper functions
def validate_email(email: str) -> bool:
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def generate_employee_id() -> str:
    """Generate unique employee ID"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) as count FROM employees")
    count = cursor.fetchone()['count']
    conn.close()
    return f"EMP{str(count + 1).zfill(5)}"

def calculate_leave_days(start_date: str, end_date: str) -> float:
    """Calculate number of days between two dates"""
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    return (end - start).days + 1

def log_audit(action: str, entity_type: str, entity_id: int, old_values: dict = None, new_values: dict = None):
    """Log actions for audit trail"""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO audit_log (action, entity_type, entity_id, old_values, new_values)
        VALUES (?, ?, ?, ?, ?)
    ''', (action, entity_type, entity_id, 
          json.dumps(old_values) if old_values else None,
          json.dumps(new_values) if new_values else None))
    conn.commit()
    conn.close()

# Employee Management Tools
@mcp.tool()
def manage_employee(
    action: str,
    employee_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Comprehensive employee management - add, update, terminate, or reactivate employees.
    
    Args:
        action: One of 'add', 'update', 'terminate', 'reactivate'
        employee_data: Dictionary containing employee information
            For 'add': first_name, last_name, email (required), hire_date (required, use today if not specified)
                       Optional: phone, department_name, position_title, manager_name, salary
            For 'update': employee_id and fields to update
            For 'terminate': employee_id and termination_date
            For 'reactivate': employee_id
    
    Returns:
        Dictionary with success status and employee details
    
    Note: Department and position can be specified by name and will be created if they don't exist.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if action == 'add':
            # Validate required fields
            required = ['first_name', 'last_name', 'email']
            for field in required:
                if field not in employee_data or not employee_data[field]:
                    return {"success": False, "error": f"Missing required field: {field}"}
            
            # Validate email
            if not validate_email(employee_data['email']):
                return {"success": False, "error": "Invalid email format"}
            
            # Set hire_date to today if not provided
            if 'hire_date' not in employee_data or not employee_data['hire_date']:
                employee_data['hire_date'] = date.today().isoformat()
            
            # Generate employee ID
            employee_id = generate_employee_id()
            
            # Handle department by name
            department_id = None
            if 'department_name' in employee_data and employee_data['department_name']:
                cursor.execute('SELECT id FROM departments WHERE name = ?', (employee_data['department_name'],))
                dept = cursor.fetchone()
                if dept:
                    department_id = dept['id']
                else:
                    # Create department if it doesn't exist
                    cursor.execute('INSERT INTO departments (name) VALUES (?)', (employee_data['department_name'],))
                    department_id = cursor.lastrowid
            elif 'department_id' in employee_data:
                department_id = employee_data['department_id']
            
            # Handle position by title
            position_id = None
            if 'position_title' in employee_data and employee_data['position_title']:
                cursor.execute('SELECT id FROM positions WHERE title = ? AND (department_id = ? OR department_id IS NULL)', 
                              (employee_data['position_title'], department_id))
                pos = cursor.fetchone()
                if pos:
                    position_id = pos['id']
                else:
                    # Create position if it doesn't exist
                    cursor.execute('INSERT INTO positions (title, department_id) VALUES (?, ?)', 
                                  (employee_data['position_title'], department_id))
                    position_id = cursor.lastrowid
            elif 'position_id' in employee_data:
                position_id = employee_data['position_id']
            
            # Handle manager by name
            manager_id = None
            if 'manager_name' in employee_data and employee_data['manager_name']:
                # Try to find manager by full name
                manager_parts = employee_data['manager_name'].split()
                if len(manager_parts) >= 2:
                    cursor.execute('''
                        SELECT id FROM employees 
                        WHERE first_name = ? AND last_name = ? 
                        AND employment_status = 'active'
                    ''', (manager_parts[0], ' '.join(manager_parts[1:])))
                    manager = cursor.fetchone()
                    if manager:
                        manager_id = manager['id']
            elif 'manager_id' in employee_data:
                manager_id = employee_data['manager_id']
            
            # Insert employee
            cursor.execute('''
                INSERT INTO employees (
                    employee_id, first_name, last_name, email, phone,
                    date_of_birth, gender, marital_status, address, city,
                    state, country, postal_code, department_id, position_id,
                    manager_id, hire_date, employment_type, work_location
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                employee_id,
                employee_data['first_name'],
                employee_data['last_name'],
                employee_data['email'],
                employee_data.get('phone'),
                employee_data.get('date_of_birth'),
                employee_data.get('gender'),
                employee_data.get('marital_status'),
                employee_data.get('address'),
                employee_data.get('city'),
                employee_data.get('state'),
                employee_data.get('country', 'USA'),
                employee_data.get('postal_code'),
                department_id,
                position_id,
                manager_id,
                employee_data['hire_date'],
                employee_data.get('employment_type', 'full-time'),
                employee_data.get('work_location', 'office')
            ))
            
            emp_id = cursor.lastrowid
            
            # Add initial salary if provided
            if 'salary' in employee_data:
                cursor.execute('''
                    INSERT INTO salaries (employee_id, base_salary, effective_date)
                    VALUES (?, ?, ?)
                ''', (emp_id, employee_data['salary'], employee_data['hire_date']))
            
            # Initialize leave balances for current year
            current_year = datetime.now().year
            cursor.execute('SELECT id, days_per_year FROM leave_types')
            leave_types = cursor.fetchall()
            
            for leave_type in leave_types:
                # Pro-rate leave days based on hire date
                hire_date = datetime.strptime(employee_data['hire_date'], '%Y-%m-%d')
                if hire_date.year == current_year:
                    days_remaining = (date(current_year, 12, 31) - hire_date.date()).days
                    prorated_days = round((leave_type['days_per_year'] * days_remaining) / 365, 1)
                else:
                    prorated_days = leave_type['days_per_year']
                
                cursor.execute('''
                    INSERT INTO leave_balances (employee_id, leave_type_id, year, entitled_days, remaining_days)
                    VALUES (?, ?, ?, ?, ?)
                ''', (emp_id, leave_type['id'], current_year, prorated_days, prorated_days))
            
            conn.commit()
            log_audit('CREATE', 'employee', emp_id, None, employee_data)
            
            return {
                "success": True,
                "employee_id": employee_id,
                "message": f"Employee {employee_data['first_name']} {employee_data['last_name']} added successfully"
            }
        
        elif action == 'update':
            if 'employee_id' not in employee_data:
                return {"success": False, "error": "employee_id required for update"}
            
            # Get current employee data for audit
            cursor.execute('SELECT * FROM employees WHERE employee_id = ?', (employee_data['employee_id'],))
            current = cursor.fetchone()
            if not current:
                return {"success": False, "error": "Employee not found"}
            
            # Build update query
            update_fields = []
            values = []
            for field, value in employee_data.items():
                if field != 'employee_id' and field in ['first_name', 'last_name', 'email', 'phone',
                                                         'department_id', 'position_id', 'manager_id',
                                                         'employment_status', 'work_location']:
                    update_fields.append(f"{field} = ?")
                    values.append(value)
            
            if update_fields:
                values.append(employee_data['employee_id'])
                cursor.execute(f'''
                    UPDATE employees 
                    SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE employee_id = ?
                ''', values)
                
                conn.commit()
                log_audit('UPDATE', 'employee', current['id'], dict(current), employee_data)
                
                return {"success": True, "message": "Employee updated successfully"}
            
            return {"success": False, "error": "No valid fields to update"}
        
        elif action == 'terminate':
            if 'employee_id' not in employee_data:
                return {"success": False, "error": "employee_id required for termination"}
            
            cursor.execute('''
                UPDATE employees 
                SET employment_status = 'terminated', updated_at = CURRENT_TIMESTAMP
                WHERE employee_id = ?
            ''', (employee_data['employee_id'],))
            
            # End current salary record
            if 'termination_date' in employee_data:
                cursor.execute('''
                    UPDATE salaries 
                    SET end_date = ?
                    WHERE employee_id = (SELECT id FROM employees WHERE employee_id = ?)
                    AND end_date IS NULL
                ''', (employee_data['termination_date'], employee_data['employee_id']))
            
            conn.commit()
            log_audit('TERMINATE', 'employee', employee_data['employee_id'], None, employee_data)
            
            return {"success": True, "message": "Employee terminated successfully"}
        
        elif action == 'reactivate':
            if 'employee_id' not in employee_data:
                return {"success": False, "error": "employee_id required for reactivation"}
            
            cursor.execute('''
                UPDATE employees 
                SET employment_status = 'active', updated_at = CURRENT_TIMESTAMP
                WHERE employee_id = ?
            ''', (employee_data['employee_id'],))
            
            conn.commit()
            log_audit('REACTIVATE', 'employee', employee_data['employee_id'], None, None)
            
            return {"success": True, "message": "Employee reactivated successfully"}
        
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
            
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

@mcp.tool()
def search_employees(
    criteria: Dict[str, Any]
) -> List[Dict[str, Any]]:
    """
    Advanced employee search with multiple filters.
    
    Args:
        criteria: Search criteria dictionary
            - name: Search by first or last name (partial match)
            - department: Department name or ID
            - position: Position title (partial match)
            - status: Employment status (active, terminated, on_leave)
            - manager: Manager's name or employee_id
            - hire_date_from: Employees hired after this date
            - hire_date_to: Employees hired before this date
            - location: Work location
    
    Returns:
        List of employee records matching criteria
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    query = '''
        SELECT 
            e.employee_id,
            e.first_name,
            e.last_name,
            e.email,
            e.phone,
            e.employment_status,
            e.hire_date,
            d.name as department_name,
            p.title as position_title,
            m.first_name || ' ' || m.last_name as manager_name,
            s.base_salary as current_salary
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        LEFT JOIN positions p ON e.position_id = p.id
        LEFT JOIN employees m ON e.manager_id = m.id
        LEFT JOIN (
            SELECT employee_id, base_salary
            FROM salaries
            WHERE end_date IS NULL
        ) s ON e.id = s.employee_id
        WHERE 1=1
    '''
    
    params = []
    
    if criteria.get('name'):
        query += " AND (e.first_name LIKE ? OR e.last_name LIKE ?)"
        name_pattern = f"%{criteria['name']}%"
        params.extend([name_pattern, name_pattern])
    
    if criteria.get('department'):
        if isinstance(criteria['department'], int):
            query += " AND e.department_id = ?"
            params.append(criteria['department'])
        else:
            query += " AND d.name LIKE ?"
            params.append(f"%{criteria['department']}%")
    
    if criteria.get('position'):
        query += " AND p.title LIKE ?"
        params.append(f"%{criteria['position']}%")
    
    if criteria.get('status'):
        query += " AND e.employment_status = ?"
        params.append(criteria['status'])
    
    if criteria.get('manager'):
        if criteria['manager'].startswith('EMP'):
            query += " AND m.employee_id = ?"
            params.append(criteria['manager'])
        else:
            query += " AND (m.first_name LIKE ? OR m.last_name LIKE ?)"
            manager_pattern = f"%{criteria['manager']}%"
            params.extend([manager_pattern, manager_pattern])
    
    if criteria.get('hire_date_from'):
        query += " AND e.hire_date >= ?"
        params.append(criteria['hire_date_from'])
    
    if criteria.get('hire_date_to'):
        query += " AND e.hire_date <= ?"
        params.append(criteria['hire_date_to'])
    
    if criteria.get('location'):
        query += " AND e.work_location = ?"
        params.append(criteria['location'])
    
    cursor.execute(query, params)
    
    results = []
    for row in cursor.fetchall():
        results.append(dict(row))
    
    conn.close()
    return results

# Organizational Structure Tools
@mcp.tool()
def get_org_chart(
    department_id: Optional[int] = None,
    include_all_levels: bool = True
) -> Dict[str, Any]:
    """
    Generate organizational hierarchy chart.
    
    Args:
        department_id: Specific department ID (None for entire organization)
        include_all_levels: Whether to include all subordinate levels
    
    Returns:
        Hierarchical organization structure
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    def build_hierarchy(manager_id=None, dept_id=None):
        if dept_id:
            cursor.execute('''
                SELECT 
                    e.id, e.employee_id, e.first_name, e.last_name,
                    p.title, d.name as department
                FROM employees e
                LEFT JOIN positions p ON e.position_id = p.id
                LEFT JOIN departments d ON e.department_id = d.id
                WHERE e.department_id = ? AND e.employment_status = 'active'
                AND (e.manager_id = ? OR (? IS NULL AND e.manager_id IS NULL))
            ''', (dept_id, manager_id, manager_id))
        else:
            cursor.execute('''
                SELECT 
                    e.id, e.employee_id, e.first_name, e.last_name,
                    p.title, d.name as department
                FROM employees e
                LEFT JOIN positions p ON e.position_id = p.id
                LEFT JOIN departments d ON e.department_id = d.id
                WHERE e.employment_status = 'active'
                AND (e.manager_id = ? OR (? IS NULL AND e.manager_id IS NULL))
            ''', (manager_id, manager_id))
        
        employees = cursor.fetchall()
        
        org_structure = []
        for emp in employees:
            emp_dict = {
                "employee_id": emp['employee_id'],
                "name": f"{emp['first_name']} {emp['last_name']}",
                "position": emp['title'],
                "department": emp['department']
            }
            
            if include_all_levels:
                subordinates = build_hierarchy(emp['id'], dept_id if dept_id else None)
                if subordinates:
                    emp_dict["reports"] = subordinates
            
            org_structure.append(emp_dict)
        
        return org_structure
    
    org_chart = build_hierarchy(None, department_id)
    
    # Get department info if specified
    if department_id:
        cursor.execute('SELECT name FROM departments WHERE id = ?', (department_id,))
        dept = cursor.fetchone()
        result = {
            "department": dept['name'] if dept else "Unknown",
            "structure": org_chart
        }
    else:
        result = {"organization": org_chart}
    
    conn.close()
    return result

@mcp.tool()
def manage_department(
    action: str,
    department_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Create, update, merge, or close departments.
    
    Args:
        action: One of 'create', 'update', 'merge', 'close'
        department_data: Department information
            For 'create': name, parent_id (optional), manager_id, budget
            For 'update': department_id and fields to update
            For 'merge': source_id, target_id
            For 'close': department_id
    
    Returns:
        Operation result
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        if action == 'create':
            if 'name' not in department_data:
                return {"success": False, "error": "Department name required"}
            
            cursor.execute('''
                INSERT INTO departments (name, parent_id, manager_id, budget, cost_center)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                department_data['name'],
                department_data.get('parent_id'),
                department_data.get('manager_id'),
                department_data.get('budget'),
                department_data.get('cost_center')
            ))
            
            dept_id = cursor.lastrowid
            conn.commit()
            log_audit('CREATE', 'department', dept_id, None, department_data)
            
            return {"success": True, "department_id": dept_id, "message": "Department created successfully"}
        
        elif action == 'update':
            if 'department_id' not in department_data:
                return {"success": False, "error": "department_id required"}
            
            update_fields = []
            values = []
            for field in ['name', 'parent_id', 'manager_id', 'budget', 'cost_center']:
                if field in department_data:
                    update_fields.append(f"{field} = ?")
                    values.append(department_data[field])
            
            if update_fields:
                values.append(department_data['department_id'])
                cursor.execute(f'''
                    UPDATE departments 
                    SET {', '.join(update_fields)}, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                ''', values)
                
                conn.commit()
                return {"success": True, "message": "Department updated successfully"}
            
            return {"success": False, "error": "No fields to update"}
        
        elif action == 'merge':
            if 'source_id' not in department_data or 'target_id' not in department_data:
                return {"success": False, "error": "source_id and target_id required"}
            
            # Move all employees from source to target department
            cursor.execute('''
                UPDATE employees 
                SET department_id = ?
                WHERE department_id = ?
            ''', (department_data['target_id'], department_data['source_id']))
            
            # Update positions
            cursor.execute('''
                UPDATE positions 
                SET department_id = ?
                WHERE department_id = ?
            ''', (department_data['target_id'], department_data['source_id']))
            
            # Delete source department
            cursor.execute('DELETE FROM departments WHERE id = ?', (department_data['source_id'],))
            
            conn.commit()
            log_audit('MERGE', 'department', department_data['source_id'], 
                     {'source': department_data['source_id']}, 
                     {'target': department_data['target_id']})
            
            return {"success": True, "message": "Departments merged successfully"}
        
        else:
            return {"success": False, "error": f"Unknown action: {action}"}
            
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

# Leave Management Tools
@mcp.tool()
def request_leave(
    employee_id: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    reason: str = ""
) -> Dict[str, Any]:
    """
    Submit a leave request.
    
    Args:
        employee_id: Employee ID
        leave_type: Type of leave (e.g., 'Annual Leave', 'Sick Leave')
        start_date: Start date (YYYY-MM-DD)
        end_date: End date (YYYY-MM-DD)
        reason: Reason for leave
    
    Returns:
        Request submission result
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get employee and leave type IDs
        cursor.execute('SELECT id FROM employees WHERE employee_id = ?', (employee_id,))
        emp = cursor.fetchone()
        if not emp:
            return {"success": False, "error": "Employee not found"}
        
        cursor.execute('SELECT id FROM leave_types WHERE name = ?', (leave_type,))
        leave = cursor.fetchone()
        if not leave:
            return {"success": False, "error": "Invalid leave type"}
        
        # Calculate days requested
        days_requested = calculate_leave_days(start_date, end_date)
        
        # Check leave balance
        year = datetime.strptime(start_date, '%Y-%m-%d').year
        cursor.execute('''
            SELECT remaining_days 
            FROM leave_balances 
            WHERE employee_id = ? AND leave_type_id = ? AND year = ?
        ''', (emp['id'], leave['id'], year))
        
        balance = cursor.fetchone()
        if not balance or balance['remaining_days'] < days_requested:
            return {"success": False, "error": "Insufficient leave balance"}
        
        # Create leave request
        cursor.execute('''
            INSERT INTO leave_requests (
                employee_id, leave_type_id, start_date, end_date,
                days_requested, reason, status
            ) VALUES (?, ?, ?, ?, ?, ?, 'pending')
        ''', (emp['id'], leave['id'], start_date, end_date, days_requested, reason))
        
        request_id = cursor.lastrowid
        conn.commit()
        
        return {
            "success": True,
            "request_id": request_id,
            "message": f"Leave request submitted for {days_requested} days",
            "remaining_balance": balance['remaining_days'] - days_requested
        }
        
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

@mcp.tool()
def approve_leave(
    request_id: int,
    approver_id: str,
    action: str = "approve",
    comments: str = ""
) -> Dict[str, Any]:
    """
    Approve or reject leave requests.
    
    Args:
        request_id: Leave request ID
        approver_id: Approver's employee ID
        action: 'approve' or 'reject'
        comments: Optional comments
    
    Returns:
        Approval result
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get approver ID
        cursor.execute('SELECT id FROM employees WHERE employee_id = ?', (approver_id,))
        approver = cursor.fetchone()
        if not approver:
            return {"success": False, "error": "Approver not found"}
        
        # Get leave request details
        cursor.execute('''
            SELECT lr.*, e.first_name, e.last_name, lt.name as leave_type
            FROM leave_requests lr
            JOIN employees e ON lr.employee_id = e.id
            JOIN leave_types lt ON lr.leave_type_id = lt.id
            WHERE lr.id = ?
        ''', (request_id,))
        
        request = cursor.fetchone()
        if not request:
            return {"success": False, "error": "Leave request not found"}
        
        if request['status'] != 'pending':
            return {"success": False, "error": f"Request already {request['status']}"}
        
        if action == 'approve':
            # Update request status
            cursor.execute('''
                UPDATE leave_requests 
                SET status = 'approved', approved_by = ?, approved_date = CURRENT_TIMESTAMP,
                    comments = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (approver['id'], comments, request_id))
            
            # Update leave balance
            year = datetime.strptime(request['start_date'], '%Y-%m-%d').year
            cursor.execute('''
                UPDATE leave_balances 
                SET used_days = used_days + ?,
                    remaining_days = remaining_days - ?
                WHERE employee_id = ? AND leave_type_id = ? AND year = ?
            ''', (request['days_requested'], request['days_requested'], 
                  request['employee_id'], request['leave_type_id'], year))
            
            message = f"Leave request approved for {request['first_name']} {request['last_name']}"
        
        else:  # reject
            cursor.execute('''
                UPDATE leave_requests 
                SET status = 'rejected', approved_by = ?, approved_date = CURRENT_TIMESTAMP,
                    comments = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            ''', (approver['id'], comments, request_id))
            
            message = f"Leave request rejected for {request['first_name']} {request['last_name']}"
        
        conn.commit()
        log_audit(action.upper(), 'leave_request', request_id, None, {'comments': comments})
        
        return {"success": True, "message": message}
        
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

@mcp.tool()
def get_leave_balance(
    employee_id: str,
    year: Optional[int] = None
) -> Dict[str, Any]:
    """
    Check leave balances for an employee.
    
    Args:
        employee_id: Employee ID
        year: Year (defaults to current year)
    
    Returns:
        Leave balance details
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    if not year:
        year = datetime.now().year
    
    # Get employee
    cursor.execute('SELECT id, first_name, last_name FROM employees WHERE employee_id = ?', (employee_id,))
    emp = cursor.fetchone()
    if not emp:
        return {"success": False, "error": "Employee not found"}
    
    # Get leave balances
    cursor.execute('''
        SELECT 
            lt.name as leave_type,
            lb.entitled_days,
            lb.used_days,
            lb.carried_forward,
            lb.remaining_days
        FROM leave_balances lb
        JOIN leave_types lt ON lb.leave_type_id = lt.id
        WHERE lb.employee_id = ? AND lb.year = ?
    ''', (emp['id'], year))
    
    balances = []
    for row in cursor.fetchall():
        balances.append(dict(row))
    
    # Get pending requests
    cursor.execute('''
        SELECT 
            lt.name as leave_type,
            lr.start_date,
            lr.end_date,
            lr.days_requested
        FROM leave_requests lr
        JOIN leave_types lt ON lr.leave_type_id = lt.id
        WHERE lr.employee_id = ? AND lr.status = 'pending'
        AND strftime('%Y', lr.start_date) = ?
    ''', (emp['id'], str(year)))
    
    pending = []
    for row in cursor.fetchall():
        pending.append(dict(row))
    
    conn.close()
    
    return {
        "employee": f"{emp['first_name']} {emp['last_name']}",
        "year": year,
        "balances": balances,
        "pending_requests": pending
    }

# Compensation & Benefits Tools
@mcp.tool()
def update_salary(
    employee_id: str,
    new_salary: float,
    effective_date: str,
    bonus: Optional[float] = None,
    reason: str = ""
) -> Dict[str, Any]:
    """
    Update employee salary with history tracking.
    
    Args:
        employee_id: Employee ID
        new_salary: New base salary
        effective_date: Effective date (YYYY-MM-DD)
        bonus: Optional bonus amount
        reason: Reason for salary change
    
    Returns:
        Update result
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get employee
        cursor.execute('SELECT id FROM employees WHERE employee_id = ?', (employee_id,))
        emp = cursor.fetchone()
        if not emp:
            return {"success": False, "error": "Employee not found"}
        
        # End current salary record
        cursor.execute('''
            UPDATE salaries 
            SET end_date = date(?, '-1 day')
            WHERE employee_id = ? AND end_date IS NULL
        ''', (effective_date, emp['id']))
        
        # Insert new salary record
        cursor.execute('''
            INSERT INTO salaries (employee_id, base_salary, bonus, effective_date)
            VALUES (?, ?, ?, ?)
        ''', (emp['id'], new_salary, bonus, effective_date))
        
        conn.commit()
        log_audit('SALARY_UPDATE', 'employee', emp['id'], None, 
                 {'new_salary': new_salary, 'reason': reason})
        
        return {
            "success": True,
            "message": f"Salary updated to {new_salary} effective {effective_date}"
        }
        
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

@mcp.tool()
def generate_compensation_report(
    filters: Dict[str, Any] = {}
) -> Dict[str, Any]:
    """
    Generate salary analysis and compensation reports.
    
    Args:
        filters: Optional filters
            - department: Department name or ID
            - position: Position title
            - date: Report date (defaults to current)
    
    Returns:
        Compensation analysis report
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Base query for salary statistics
    query = '''
        SELECT 
            d.name as department,
            p.title as position,
            COUNT(DISTINCT e.id) as employee_count,
            AVG(s.base_salary) as avg_salary,
            MIN(s.base_salary) as min_salary,
            MAX(s.base_salary) as max_salary,
            SUM(s.base_salary) as total_payroll,
            AVG(s.bonus) as avg_bonus
        FROM employees e
        JOIN salaries s ON e.id = s.employee_id
        LEFT JOIN departments d ON e.department_id = d.id
        LEFT JOIN positions p ON e.position_id = p.id
        WHERE e.employment_status = 'active'
        AND s.end_date IS NULL
    '''
    
    params = []
    
    if filters.get('department'):
        if isinstance(filters['department'], int):
            query += " AND e.department_id = ?"
            params.append(filters['department'])
        else:
            query += " AND d.name = ?"
            params.append(filters['department'])
    
    if filters.get('position'):
        query += " AND p.title LIKE ?"
        params.append(f"%{filters['position']}%")
    
    # Group by department and position
    query += " GROUP BY d.name, p.title"
    
    cursor.execute(query, params)
    
    report_data = []
    total_payroll = 0
    total_employees = 0
    
    for row in cursor.fetchall():
        report_data.append(dict(row))
        total_payroll += row['total_payroll'] or 0
        total_employees += row['employee_count']
    
    # Get salary distribution
    cursor.execute('''
        SELECT 
            CASE 
                WHEN base_salary < 50000 THEN 'Under 50k'
                WHEN base_salary < 75000 THEN '50k-75k'
                WHEN base_salary < 100000 THEN '75k-100k'
                WHEN base_salary < 150000 THEN '100k-150k'
                ELSE 'Over 150k'
            END as salary_range,
            COUNT(*) as count
        FROM salaries s
        JOIN employees e ON s.employee_id = e.id
        WHERE e.employment_status = 'active' AND s.end_date IS NULL
        GROUP BY salary_range
    ''')
    
    salary_distribution = []
    for row in cursor.fetchall():
        salary_distribution.append(dict(row))
    
    conn.close()
    
    return {
        "summary": {
            "total_employees": total_employees,
            "total_payroll": total_payroll,
            "average_salary": total_payroll / total_employees if total_employees > 0 else 0
        },
        "by_department_position": report_data,
        "salary_distribution": salary_distribution,
        "generated_at": datetime.now().isoformat()
    }

# Analytics & Reporting Tools
@mcp.tool()
def generate_hr_dashboard() -> Dict[str, Any]:
    """
    Generate comprehensive HR metrics dashboard.
    
    Returns:
        Dashboard with key HR metrics
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Employee statistics
    cursor.execute('''
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN employment_status = 'active' THEN 1 ELSE 0 END) as active,
            SUM(CASE WHEN employment_status = 'terminated' THEN 1 ELSE 0 END) as terminated,
            SUM(CASE WHEN employment_type = 'full-time' THEN 1 ELSE 0 END) as full_time,
            SUM(CASE WHEN employment_type = 'part-time' THEN 1 ELSE 0 END) as part_time,
            SUM(CASE WHEN employment_type = 'contractor' THEN 1 ELSE 0 END) as contractors
        FROM employees
    ''')
    employee_stats = dict(cursor.fetchone())
    
    # Department distribution
    cursor.execute('''
        SELECT d.name, COUNT(e.id) as count
        FROM departments d
        LEFT JOIN employees e ON d.id = e.department_id AND e.employment_status = 'active'
        GROUP BY d.name
    ''')
    dept_distribution = []
    for row in cursor.fetchall():
        dept_distribution.append(dict(row))
    
    # Recent hires (last 90 days)
    cursor.execute('''
        SELECT COUNT(*) as new_hires
        FROM employees
        WHERE hire_date >= date('now', '-90 days')
    ''')
    new_hires = cursor.fetchone()['new_hires']
    
    # Upcoming reviews
    cursor.execute('''
        SELECT COUNT(DISTINCT e.id) as pending_reviews
        FROM employees e
        LEFT JOIN performance_reviews pr ON e.id = pr.employee_id
        WHERE e.employment_status = 'active'
        AND (pr.id IS NULL OR pr.next_review_date <= date('now', '+30 days'))
    ''')
    pending_reviews = cursor.fetchone()['pending_reviews']
    
    # Leave metrics
    cursor.execute('''
        SELECT 
            COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_leaves,
            COUNT(CASE WHEN status = 'approved' AND start_date >= date('now') THEN 1 END) as upcoming_leaves
        FROM leave_requests
    ''')
    leave_metrics = dict(cursor.fetchone())
    
    # Gender diversity
    cursor.execute('''
        SELECT gender, COUNT(*) as count
        FROM employees
        WHERE employment_status = 'active' AND gender IS NOT NULL
        GROUP BY gender
    ''')
    gender_diversity = []
    for row in cursor.fetchall():
        gender_diversity.append(dict(row))
    
    # Average tenure
    cursor.execute('''
        SELECT AVG(julianday('now') - julianday(hire_date)) / 365 as avg_tenure_years
        FROM employees
        WHERE employment_status = 'active'
    ''')
    avg_tenure = cursor.fetchone()['avg_tenure_years']
    
    conn.close()
    
    return {
        "employee_statistics": employee_stats,
        "department_distribution": dept_distribution,
        "recent_activity": {
            "new_hires_90_days": new_hires,
            "pending_performance_reviews": pending_reviews,
            "pending_leave_requests": leave_metrics['pending_leaves'],
            "upcoming_leaves": leave_metrics['upcoming_leaves']
        },
        "diversity_metrics": {
            "gender_distribution": gender_diversity,
            "average_tenure_years": round(avg_tenure, 1) if avg_tenure else 0
        },
        "generated_at": datetime.now().isoformat()
    }

@mcp.tool()
def analyze_turnover(
    department_id: Optional[int] = None,
    period: str = "year"
) -> Dict[str, Any]:
    """
    Analyze employee turnover rates and patterns.
    
    Args:
        department_id: Specific department (None for all)
        period: Analysis period ('month', 'quarter', 'year')
    
    Returns:
        Turnover analysis report
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Calculate date range
    if period == "month":
        date_from = date.today() - timedelta(days=30)
    elif period == "quarter":
        date_from = date.today() - timedelta(days=90)
    else:  # year
        date_from = date.today() - timedelta(days=365)
    
    # Base query
    base_where = " WHERE 1=1"
    params = []
    
    if department_id:
        base_where += " AND department_id = ?"
        params.append(department_id)
    
    # Get termination data
    cursor.execute(f'''
        SELECT 
            COUNT(*) as terminations,
            strftime('%Y-%m', updated_at) as month
        FROM employees
        {base_where}
        AND employment_status = 'terminated'
        AND updated_at >= ?
        GROUP BY month
    ''', params + [date_from.isoformat()])
    
    monthly_terminations = {}
    total_terminations = 0
    for row in cursor.fetchall():
        monthly_terminations[row['month']] = row['terminations']
        total_terminations += row['terminations']
    
    # Get average headcount
    cursor.execute(f'''
        SELECT COUNT(*) as active_count
        FROM employees
        {base_where}
        AND employment_status = 'active'
    ''', params)
    current_headcount = cursor.fetchone()['active_count']
    
    # Calculate turnover rate
    avg_headcount = current_headcount + (total_terminations / 2)  # Simple average
    if period == "month":
        periods = 1
    elif period == "quarter":
        periods = 3
    else:  # year
        periods = 12
    
    annual_turnover_rate = (total_terminations / avg_headcount / periods * 12 * 100) if avg_headcount > 0 else 0
    
    # Get reasons if tracked (would need additional field in real implementation)
    # For now, we'll analyze by department
    cursor.execute('''
        SELECT 
            d.name as department,
            COUNT(e.id) as terminations
        FROM employees e
        LEFT JOIN departments d ON e.department_id = d.id
        WHERE e.employment_status = 'terminated'
        AND e.updated_at >= ?
        GROUP BY d.name
    ''', [date_from.isoformat()])
    
    by_department = []
    for row in cursor.fetchall():
        by_department.append(dict(row))
    
    conn.close()
    
    return {
        "period": period,
        "date_range": {
            "from": date_from.isoformat(),
            "to": date.today().isoformat()
        },
        "summary": {
            "total_terminations": total_terminations,
            "current_headcount": current_headcount,
            "annual_turnover_rate": round(annual_turnover_rate, 1)
        },
        "monthly_trend": monthly_terminations,
        "by_department": by_department
    }

# Performance Management Tools
@mcp.tool()
def create_performance_review(
    employee_id: str,
    reviewer_id: str,
    period_start: str,
    period_end: str
) -> Dict[str, Any]:
    """
    Initiate performance review process.
    
    Args:
        employee_id: Employee being reviewed
        reviewer_id: Reviewer's employee ID
        period_start: Review period start date
        period_end: Review period end date
    
    Returns:
        Review creation result
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        # Get employee and reviewer IDs
        cursor.execute('SELECT id FROM employees WHERE employee_id = ?', (employee_id,))
        emp = cursor.fetchone()
        if not emp:
            return {"success": False, "error": "Employee not found"}
        
        cursor.execute('SELECT id FROM employees WHERE employee_id = ?', (reviewer_id,))
        reviewer = cursor.fetchone()
        if not reviewer:
            return {"success": False, "error": "Reviewer not found"}
        
        # Create review
        cursor.execute('''
            INSERT INTO performance_reviews (
                employee_id, reviewer_id, review_period_start, review_period_end
            ) VALUES (?, ?, ?, ?)
        ''', (emp['id'], reviewer['id'], period_start, period_end))
        
        review_id = cursor.lastrowid
        conn.commit()
        
        return {
            "success": True,
            "review_id": review_id,
            "message": "Performance review initiated"
        }
        
    except Exception as e:
        conn.rollback()
        return {"success": False, "error": str(e)}
    finally:
        conn.close()

# Simple wrapper tools for better LLM understanding
@mcp.tool()
def add_employee(
    first_name: str,
    last_name: str,
    email: str,
    department: str,
    position: str,
    salary: Optional[float] = None,
    phone: Optional[str] = None,
    hire_date: Optional[str] = None
) -> Dict[str, Any]:
    """
    Add a new employee to the company. Simple interface for adding employees.
    
    Args:
        first_name: Employee's first name
        last_name: Employee's last name  
        email: Employee's email address
        department: Department name (will be created if doesn't exist)
        position: Position/job title (will be created if doesn't exist)
        salary: Starting salary (optional)
        phone: Phone number (optional)
        hire_date: Hire date YYYY-MM-DD (optional, defaults to today)
    
    Returns:
        Success status and employee ID
    
    Example:
        add_employee("John", "Doe", "john.doe@company.com", "Engineering", "Software Engineer", 85000)
    """
    employee_data = {
        'first_name': first_name,
        'last_name': last_name,
        'email': email,
        'department_name': department,
        'position_title': position,
        'phone': phone,
        'hire_date': hire_date
    }
    
    if salary:
        employee_data['salary'] = salary
        
    return manage_employee('add', employee_data)

@mcp.tool()
def list_all_employees() -> List[Dict[str, Any]]:
    """
    List all active employees in the company.
    
    Returns:
        List of all active employees with their details
    """
    return search_employees({'status': 'active'})

@mcp.tool()
def find_employees_by_department(department: str) -> List[Dict[str, Any]]:
    """
    Find all employees in a specific department.
    
    Args:
        department: Department name
    
    Returns:
        List of employees in the department
    """
    return search_employees({'department': department})

@mcp.tool()
def check_employee_leave_balance(
    employee_name: str,
    year: Optional[int] = None
) -> Dict[str, Any]:
    """
    Check leave balance for an employee by their name.
    
    Args:
        employee_name: Full name of the employee (e.g., "John Doe" or "Sarah Johnson")
        year: Year to check balance for (defaults to current year)
    
    Returns:
        Leave balance details including all leave types and remaining days
    
    Example:
        check_employee_leave_balance("Sarah Johnson")
        check_employee_leave_balance("John Doe", 2024)
    """
    # Search for employee by name
    name_parts = employee_name.strip().split(' ', 1)
    if len(name_parts) < 2:
        return {"success": False, "error": "Please provide both first and last name"}
    
    first_name = name_parts[0]
    last_name = name_parts[1]
    
    # Search for the employee
    employees = search_employees({'name': first_name})
    
    # Filter by exact name match
    matching_employees = [
        emp for emp in employees 
        if emp['first_name'].lower() == first_name.lower() 
        and emp['last_name'].lower() == last_name.lower()
    ]
    
    if not matching_employees:
        return {"success": False, "error": f"Employee '{employee_name}' not found"}
    
    if len(matching_employees) > 1:
        return {
            "success": False, 
            "error": f"Multiple employees found with name '{employee_name}'. Please use employee ID.",
            "employees": [{"id": emp['employee_id'], "name": f"{emp['first_name']} {emp['last_name']}", 
                          "department": emp.get('department_name', 'N/A')} for emp in matching_employees]
        }
    
    # Get leave balance using employee_id
    employee = matching_employees[0]
    return get_leave_balance(employee['employee_id'], year)

@mcp.tool()
def update_employee_salary(
    employee_name: str,
    new_salary: float,
    effective_date: str,
    bonus: Optional[float] = None,
    reason: str = ""
) -> Dict[str, Any]:
    """
    Update salary for an employee by their name.
    
    Args:
        employee_name: Full name of the employee (e.g., "John Doe")
        new_salary: New base salary amount
        effective_date: Date when new salary takes effect (YYYY-MM-DD)
        bonus: Optional bonus amount
        reason: Reason for salary change
    
    Returns:
        Success status and updated salary details
    
    Example:
        update_employee_salary("John Doe", 95000, "2024-01-01", reason="Annual raise")
    """
    # Search for employee by name
    name_parts = employee_name.strip().split(' ', 1)
    if len(name_parts) < 2:
        return {"success": False, "error": "Please provide both first and last name"}
    
    first_name = name_parts[0]
    last_name = name_parts[1]
    
    # Search for the employee
    employees = search_employees({'name': first_name})
    
    # Filter by exact name match
    matching_employees = [
        emp for emp in employees 
        if emp['first_name'].lower() == first_name.lower() 
        and emp['last_name'].lower() == last_name.lower()
    ]
    
    if not matching_employees:
        return {"success": False, "error": f"Employee '{employee_name}' not found"}
    
    if len(matching_employees) > 1:
        return {
            "success": False, 
            "error": f"Multiple employees found with name '{employee_name}'. Please use employee ID.",
            "employees": [{"id": emp['employee_id'], "name": f"{emp['first_name']} {emp['last_name']}", 
                          "department": emp.get('department_name', 'N/A')} for emp in matching_employees]
        }
    
    # Update salary using employee_id
    employee = matching_employees[0]
    return update_salary(employee['employee_id'], new_salary, effective_date, bonus, reason)

@mcp.tool()
def submit_leave_request(
    employee_name: str,
    leave_type: str,
    start_date: str,
    end_date: str,
    reason: str = ""
) -> Dict[str, Any]:
    """
    Submit a leave request for an employee by their name.
    
    Args:
        employee_name: Full name of the employee (e.g., "John Doe")
        leave_type: Type of leave (e.g., "Annual Leave", "Sick Leave", "Personal Leave")
        start_date: Start date of leave (YYYY-MM-DD)
        end_date: End date of leave (YYYY-MM-DD)
        reason: Reason for leave (optional)
    
    Returns:
        Success status and leave request details
    
    Example:
        submit_leave_request("Sarah Johnson", "Annual Leave", "2024-12-20", "2024-12-27", "Holiday vacation")
    """
    # Search for employee by name
    name_parts = employee_name.strip().split(' ', 1)
    if len(name_parts) < 2:
        return {"success": False, "error": "Please provide both first and last name"}
    
    first_name = name_parts[0]
    last_name = name_parts[1]
    
    # Search for the employee
    employees = search_employees({'name': first_name})
    
    # Filter by exact name match
    matching_employees = [
        emp for emp in employees 
        if emp['first_name'].lower() == first_name.lower() 
        and emp['last_name'].lower() == last_name.lower()
    ]
    
    if not matching_employees:
        return {"success": False, "error": f"Employee '{employee_name}' not found"}
    
    if len(matching_employees) > 1:
        return {
            "success": False, 
            "error": f"Multiple employees found with name '{employee_name}'. Please use employee ID.",
            "employees": [{"id": emp['employee_id'], "name": f"{emp['first_name']} {emp['last_name']}", 
                          "department": emp.get('department_name', 'N/A')} for emp in matching_employees]
        }
    
    # Submit leave request using employee_id
    employee = matching_employees[0]
    return request_leave(employee['employee_id'], leave_type, start_date, end_date, reason)

# Initialize database when module loads
init_db()

if __name__ == "__main__":
    # Start the server
    print("🚀 Starting HR Management System MCP Server...")
    
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--server_type", type=str, default="sse", choices=["sse", "stdio"]
    )
    
    args = parser.parse_args()
    mcp.run(args.server_type)