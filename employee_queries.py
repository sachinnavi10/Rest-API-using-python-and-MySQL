from database import get_connection


def add_employee(name: str, email: str, department: str, salary: float) -> int:
    """Insert one employee and return the ID MySQL assigned to the row."""
    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()
        query = """
            INSERT INTO employees (name, email, department, salary)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (name, email, department, salary))
        connection.commit()
        return cursor.lastrowid
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def get_all_employees() -> list[dict]:
    """Return every employee as a list of dictionaries."""
    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)
        cursor.execute("SELECT id, name, email, department, salary FROM employees")
        return cursor.fetchall()
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def get_employee_by_id(employee_id: int) -> dict | None:
    """Return one employee, or None when that ID does not exist."""
    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)
        query = """
            SELECT id, name, email, department, salary
            FROM employees
            WHERE id = %s
        """
        cursor.execute(query, (employee_id,))
        return cursor.fetchone()
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def update_employee(employee_id: int, employee_details: dict) -> bool:
    """Update supplied employee columns and report whether the ID exists."""
    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()
        assignments = ", ".join(
            f"{column} = %s" for column in employee_details
        )
        values = tuple(employee_details.values()) + (employee_id,)
        query = f"UPDATE employees SET {assignments} WHERE id = %s"
        cursor.execute(query, values)
        connection.commit()

        if cursor.rowcount > 0:
            return True

        cursor.execute("SELECT id FROM employees WHERE id = %s", (employee_id,))
        return cursor.fetchone() is not None
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def delete_employee(employee_id: int) -> bool:
    """Delete an employee and report whether a row was removed."""
    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor()
        cursor.execute("DELETE FROM employees WHERE id = %s", (employee_id,))
        connection.commit()
        return cursor.rowcount > 0
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()


def search_employees(name: str | None, department: str | None) -> list[dict]:
    """Find employees whose name or department contains the supplied text."""
    connection = get_connection()
    cursor = None

    try:
        cursor = connection.cursor(dictionary=True)
        conditions = []
        values = []

        if name is not None:
            conditions.append("name LIKE %s")
            values.append(f"%{name}%")

        if department is not None:
            conditions.append("department LIKE %s")
            values.append(f"%{department}%")

        query = """
            SELECT id, name, email, department, salary
            FROM employees
            WHERE
        """ + " AND ".join(conditions)
        cursor.execute(query, tuple(values))
        return cursor.fetchall()
    finally:
        if cursor is not None:
            cursor.close()
        connection.close()
