from collections.abc import Callable

from fastapi import Body, FastAPI, HTTPException, Query, File, UploadFile
from fastapi.responses import FileResponse
from mysql.connector import Error as MySQLError
from mysql.connector import IntegrityError

import employee_queries
import file_operations
import json


app = FastAPI(title="Employee Management API")
MAX_UPLOAD_SIZE = 1 * 1024 * 1024  # 1 MB

EMPLOYEE_FIELDS = {"name", "email", "department", "salary"}


def validate_employee_data(data: dict, require_all_fields: bool = False) -> dict:
    """Check employee input and return a cleaned copy of the supplied fields."""
    unknown_fields = set(data) - EMPLOYEE_FIELDS
    if unknown_fields:
        field_names = ", ".join(sorted(unknown_fields))
        raise HTTPException(
            status_code=422,
            detail=f"Unknown employee field(s): {field_names}",
        )

    if require_all_fields:
        missing_fields = EMPLOYEE_FIELDS - set(data)
        if missing_fields:
            field_names = ", ".join(sorted(missing_fields))
            raise HTTPException(
                status_code=422,
                detail=f"Missing required field(s): {field_names}",
            )
    elif not data:
        raise HTTPException(
            status_code=422,
            detail="Provide at least one employee field to update.",
        )

    cleaned_data = {}
    for field in ("name", "email", "department"):
        if field in data:
            value = data[field]
            if not isinstance(value, str) or not value.strip():
                raise HTTPException(
                    status_code=422,
                    detail=f"{field} must be a non-empty string.",
                )

            cleaned_value = value.strip()
            if field == "email" and (
                "@" not in cleaned_value or "." not in cleaned_value.rsplit("@", 1)[-1]
            ):
                raise HTTPException(
                    status_code=422,
                    detail="email must be a valid email address.",
                )
            cleaned_data[field] = cleaned_value

    if "salary" in data:
        salary = data["salary"]
        if (
            isinstance(salary, bool)
            or not isinstance(salary, (int, float))
            or salary < 0
        ):
            raise HTTPException(
                status_code=422,
                detail="salary must be a non-negative number.",
            )
        cleaned_data["salary"] = salary

    return cleaned_data


def raise_database_error(error: MySQLError) -> None:
    """Return a safe HTTP error when a database operation fails."""
    raise HTTPException(
        status_code=503,
        detail="Database operation failed. Check that MySQL Server is running and the .env settings are correct.",
    ) from error



def run_file_operation(operation: Callable[..., object], *arguments: str) -> object:
    """Run a safe file operation and translate file errors to HTTP responses."""
    try:
        return operation(*arguments)

    except json.JSONDecodeError as error:
        raise HTTPException(
            status_code=400,
            detail="Invalid JSON format. Please check the JSON file syntax.",
        ) from error

    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error

    except FileNotFoundError as error:
        raise HTTPException(
            status_code=404,
            detail="File not found.",
        ) from error

    except FileExistsError as error:
        raise HTTPException(
            status_code=409,
            detail="A file with that name already exists.",
        ) from error

    except PermissionError as error:
        raise HTTPException(
            status_code=403,
            detail="The application does not have permission to access this file.",
        ) from error

    except OSError as error:
        raise HTTPException(
            status_code=500,
            detail="The file operation failed.",
        ) from error

@app.post("/employees", status_code=201)
def create_employee(employee_data: dict = Body(...)):
    """Validate and save a new employee."""
    cleaned_data = validate_employee_data(employee_data, require_all_fields=True)

    try:
        employee_id = employee_queries.add_employee(
            cleaned_data["name"],
            cleaned_data["email"],
            cleaned_data["department"],
            cleaned_data["salary"],
        )
        return {
            "id": employee_id,
            **cleaned_data,
        }
    except IntegrityError as error:
        if error.errno == 1062:
            raise HTTPException(
                status_code=409,
                detail="An employee with this email already exists.",
            ) from error
        raise_database_error(error)
    except MySQLError as error:
        raise_database_error(error)


@app.get("/employees")
def read_all_employees():
    """Return all employees."""
    try:
        return employee_queries.get_all_employees()
    except MySQLError as error:
        raise_database_error(error)


@app.get("/employees/search")
def find_employees(
    name: str | None = Query(default=None),
    department: str | None = Query(default=None),
):
    """Search by name, department, or both."""
    cleaned_name = name.strip() if name is not None else None
    cleaned_department = department.strip() if department is not None else None

    if not cleaned_name and not cleaned_department:
        raise HTTPException(
            status_code=422,
            detail="Provide a name or department search term.",
        )

    try:
        return employee_queries.search_employees(
            cleaned_name or None,
            cleaned_department or None,
        )
    except MySQLError as error:
        raise_database_error(error)


@app.get("/employees/{employee_id}")
def read_employee(employee_id: int):
    """Return one employee by ID."""
    try:
        employee = employee_queries.get_employee_by_id(employee_id)
    except MySQLError as error:
        raise_database_error(error)

    if employee is None:
        raise HTTPException(status_code=404, detail="Employee not found.")
    return employee


@app.patch("/employees/{employee_id}")
def edit_employee(employee_id: int, employee_data: dict = Body(...)):
    """Update the supplied fields for one employee."""
    cleaned_data = validate_employee_data(employee_data)

    try:
        employee_exists = employee_queries.update_employee(
            employee_id,
            cleaned_data,
        )
        if not employee_exists:
            raise HTTPException(status_code=404, detail="Employee not found.")
        return employee_queries.get_employee_by_id(employee_id)
    except IntegrityError as error:
        if error.errno == 1062:
            raise HTTPException(
                status_code=409,
                detail="An employee with this email already exists.",
            ) from error
        raise_database_error(error)
    except MySQLError as error:
        raise_database_error(error)


@app.delete("/employees/{employee_id}")
def remove_employee(employee_id: int):
    """Delete one employee by ID."""
    try:
        employee_was_deleted = employee_queries.delete_employee(employee_id)
    except MySQLError as error:
        raise_database_error(error)

    if not employee_was_deleted:
        raise HTTPException(status_code=404, detail="Employee not found.")
    return {"message": "Employee deleted successfully."}


@app.post("/files/text/{filename}", status_code=201)
def create_text_file(filename: str):
    """Create an empty text file inside the uploads folder."""
    run_file_operation(file_operations.create_text_file, filename)
    return {"message": "Text file created.", "filename": filename}




@app.put("/files/text/{filename}")
def write_text_file(filename: str, content: str = Body(..., embed=True)):
    """Create or replace a text file's complete contents."""
    character_count = run_file_operation(
        file_operations.write_text_file,
        filename,
        content,
    )
    return {"message": "Text file written.", "characters_written": character_count}


@app.post("/files/text/{filename}/append")
def append_text_file(filename: str, content: str = Body(..., embed=True)):
    """Append content to a text file."""
    character_count = run_file_operation(
        file_operations.append_text_file,
        filename,
        content,
    )
    return {"message": "Text file updated.", "characters_written": character_count}


@app.get("/files/text/{filename}")
def read_text_file(filename: str):
    """Return all text in a file."""
    content = run_file_operation(file_operations.read_text_file, filename)
    return {"filename": filename, "content": content}


@app.get("/files/text/{filename}/lines")
def read_text_file_lines(filename: str):
    """Return a text file as a list of lines."""
    lines = run_file_operation(file_operations.read_text_file_lines, filename)
    return {"filename": filename, "lines": lines}


@app.get("/files/text/{filename}/exists")
def check_text_file(filename: str):
    """Report whether a safe text filename exists."""
    file_exists = run_file_operation(file_operations.text_file_exists, filename)
    return {"filename": filename, "exists": file_exists}


@app.post("/files/text/{filename}/rename")
def rename_text_file(filename: str, new_filename: str = Query(...)):
    """Rename a text file within the uploads folder."""
    run_file_operation(
        file_operations.rename_text_file,
        filename,
        new_filename,
    )
    return {"message": "Text file renamed.", "filename": new_filename}


@app.post("/files/text/{filename}/copy")
def copy_text_file(filename: str, copy_filename: str = Query(...)):
    """Copy a text file within the uploads folder."""
    run_file_operation(
        file_operations.copy_text_file,
        filename,
        copy_filename,
    )
    return {"message": "Text file copied.", "filename": copy_filename}


@app.delete("/files/text/{filename}")
def delete_text_file(filename: str):
    """Delete a text file from the uploads folder."""
    run_file_operation(file_operations.delete_text_file, filename)
    return {"message": "Text file deleted.", "filename": filename}


@app.get("/files/text/{filename}/size")
def get_text_file_size(filename: str):
    """Return the text file size in bytes."""
    size_in_bytes = run_file_operation(file_operations.get_text_file_size, filename)
    return {"filename": filename, "size_bytes": size_in_bytes}


@app.get("/files/csv/{filename}")
def read_csv_records(filename: str):
    """Read CSV rows from the uploads folder as a list of dictionaries."""
    rows = run_file_operation(file_operations.read_csv_file, filename, file_operations.UPLOADS_FOLDER)
    return {"filename": filename, "rows": rows}


@app.post("/files/csv/import")
def import_csv_records(filename: str = Query(...)):
    """Read a CSV file and insert valid employee rows into MySQL."""
    summary = run_file_operation(file_operations.import_csv_to_mysql, filename)
    return summary


@app.post("/files/json/import")
def import_json_records(filename: str = Query(...)):
    """Read a JSON file and insert valid employee rows into MySQL."""
    summary = run_file_operation(file_operations.import_json_to_mysql, filename)
    return summary



@app.post("/files/csv/export")
def export_csv_records(filename: str = Query(...)):
    """Export all employee rows from MySQL to a CSV file in the reports folder."""
    summary = run_file_operation(file_operations.export_employees_to_csv, filename)
    return summary


@app.post("/files/json/export")
def export_json_records(filename: str = Query(...)):
    """Export employee records from MySQL to a JSON file."""
    summary = run_file_operation(
        file_operations.export_employees_to_json,
        filename,
    )
    return summary



@app.post("/files/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload a text file to the uploads folder."""

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No filename provided.",
        )

    try:
        file_path = file_operations.get_safe_file_path(
            file.filename,
            file_operations.UPLOADS_FOLDER,
            file_operations.UPLOAD_FILENAME_PATTERN,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    try:
        content = await file.read(MAX_UPLOAD_SIZE + 1)

        if len(content) > MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=413,
                detail="File is too large. Maximum allowed size is 1 MB.",
            )

        file_path.write_bytes(content)
    finally:
        await file.close()

    return {
        "filename": file.filename,
        "message": "File uploaded successfully.",
        "location": str(file_path),
        "size_bytes": len(content),
    }


@app.get("/files/download/{filename}")
def download_file(filename: str):
    """Download a report file from the reports folder."""

    try:
        file_path = file_operations.get_safe_file_path(
            filename,
            file_operations.REPORTS_FOLDER,
            file_operations.UPLOAD_FILENAME_PATTERN,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Report file not found.",
        )

    return FileResponse(
        path=file_path,
        filename=filename,
        media_type="application/octet-stream",
    )



@app.get("/files/reports")
def list_report_files():
    """List supported report files in the reports folder."""

    reports_folder = file_operations.REPORTS_FOLDER
    reports_folder.mkdir(parents=True, exist_ok=True)

    allowed_pattern = file_operations.UPLOAD_FILENAME_PATTERN

    files = [
        {
            "filename": file.name,
            "size_bytes": file.stat().st_size,
        }
        for file in reports_folder.iterdir()
        if file.is_file() and allowed_pattern.fullmatch(file.name)
    ]

    files.sort(key=lambda item: item["filename"].lower())

    return {
        "count": len(files),
        "files": files,
    }


@app.delete("/files/reports/{filename}")
def delete_report_file(filename: str):
    """Delete a report file from the reports folder."""

    try:
        file_path = file_operations.get_safe_file_path(
            filename,
            file_operations.REPORTS_FOLDER,
            file_operations.UPLOAD_FILENAME_PATTERN,
        )
    except ValueError as error:
        raise HTTPException(
            status_code=422,
            detail=str(error),
        ) from error

    if not file_path.is_file():
        raise HTTPException(
            status_code=404,
            detail="Report file not found.",
        )

    file_path.unlink()

    return {
        "filename": filename,
        "message": "Report file deleted successfully.",
    }

