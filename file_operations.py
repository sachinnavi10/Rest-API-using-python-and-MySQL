from mysql.connector import IntegrityError
import csv
import json
import re
import shutil
from pathlib import Path

import employee_queries


UPLOADS_FOLDER = Path(__file__).resolve().parent / "uploads"
REPORTS_FOLDER = Path(__file__).resolve().parent / "reports"
TEXT_FILENAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}\.txt")
CSV_FILENAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}\.csv")
UPLOAD_FILENAME_PATTERN = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}\.(txt|csv|json)"
)
JSON_FILENAME_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_-]{0,99}\.json")


def get_safe_file_path(filename: str, folder: Path, pattern: re.Pattern[str]) -> Path:
    """Return a safe file path inside a known folder."""
    if not pattern.fullmatch(filename):
        raise ValueError(
            f"Filename must use letters, numbers, underscores, or hyphens and end with {pattern.pattern.split('.')[-1]}."
        )

    folder.mkdir(parents=True, exist_ok=True)
    file_path = (folder / filename).resolve()
    if file_path.parent != folder.resolve():
        raise ValueError("The requested file must stay inside the allowed folder.")
    return file_path


def get_text_file_path(filename: str) -> Path:
    """Return a safe path for a simple .txt filename inside uploads."""
    return get_safe_file_path(filename, UPLOADS_FOLDER, TEXT_FILENAME_PATTERN)


def create_text_file(filename: str) -> None:
    """Create a new empty text file without overwriting an existing file."""
    file_path = get_text_file_path(filename)
    with file_path.open("x", encoding="utf-8"):
        pass


def write_text_file(filename: str, content: str) -> int:
    """Create or replace a text file and return the number of characters written."""
    file_path = get_text_file_path(filename)
    with file_path.open("w", encoding="utf-8") as text_file:
        return text_file.write(content)


def append_text_file(filename: str, content: str) -> int:
    """Append text to a file and return the number of characters written."""
    file_path = get_text_file_path(filename)
    with file_path.open("a", encoding="utf-8") as text_file:
        return text_file.write(content)


def read_text_file(filename: str) -> str:
    """Return the complete contents of a text file."""
    file_path = get_text_file_path(filename)
    with file_path.open("r", encoding="utf-8") as text_file:
        return text_file.read()


def read_text_file_lines(filename: str) -> list[str]:
    """Return a text file as a list of lines without newline characters."""
    file_path = get_text_file_path(filename)
    with file_path.open("r", encoding="utf-8") as text_file:
        return [line.rstrip("\r\n") for line in text_file]


def text_file_exists(filename: str) -> bool:
    """Check whether a text file exists in the uploads folder."""
    file_path = get_text_file_path(filename)
    try:
        file_path.stat()
    except FileNotFoundError:
        return False
    return True


def rename_text_file(filename: str, new_filename: str) -> None:
    """Rename a text file without replacing an existing destination."""
    source_path = get_text_file_path(filename)
    destination_path = get_text_file_path(new_filename)
    if destination_path.exists():
        raise FileExistsError(new_filename)
    source_path.rename(destination_path)


def copy_text_file(filename: str, copy_filename: str) -> None:
    """Copy a text file without replacing an existing destination."""
    source_path = get_text_file_path(filename)
    destination_path = get_text_file_path(copy_filename)
    if destination_path.exists():
        raise FileExistsError(copy_filename)
    shutil.copyfile(source_path, destination_path)


def delete_text_file(filename: str) -> None:
    """Delete a text file by its safe name inside the uploads folder."""
    file_path = get_text_file_path(filename)
    file_path.unlink()


def get_text_file_size(filename: str) -> int:
    """Return the size of a text file in bytes."""
    file_path = get_text_file_path(filename)
    return file_path.stat().st_size


def get_csv_file_path(filename: str, folder: Path = UPLOADS_FOLDER) -> Path:
    """Return a safe path for a simple .csv filename inside a folder."""
    return get_safe_file_path(filename, folder, CSV_FILENAME_PATTERN)


def read_csv_file(filename: str, folder: Path = UPLOADS_FOLDER) -> list[dict[str, str]]:
    """Read a CSV file and return each row as a dictionary."""
    file_path = get_csv_file_path(filename, folder)
    with file_path.open("r", encoding="utf-8", newline="") as csv_file:
        rows = list(csv.DictReader(csv_file))

    if not rows:
        return []

    required_fields = {"name", "email", "department", "salary"}
    missing_fields = required_fields - set(rows[0].keys())
    if missing_fields:
        field_names = ", ".join(sorted(missing_fields))
        raise ValueError(f"CSV file is missing required columns: {field_names}")

    return rows

def get_json_file_path(
    filename: str,
    folder: Path = UPLOADS_FOLDER,
) -> Path:
    """Return a safe path for a JSON file inside an allowed folder."""
    return get_safe_file_path(filename, folder, JSON_FILENAME_PATTERN)

def read_json_file(filename: str) -> list[dict]:
    """Read a JSON file containing a list of employee records."""
    file_path = get_json_file_path(filename, UPLOADS_FOLDER)

    with file_path.open("r", encoding="utf-8") as json_file:
        data = json.load(json_file)

    if not isinstance(data, list):
        raise ValueError("JSON file must contain a list of employee records.")

    if not all(isinstance(row, dict) for row in data):
        raise ValueError("Every JSON record must be an object.")

    return data

def import_json_to_mysql(filename: str) -> dict:
    """Import valid employee records from JSON into MySQL."""
    records = read_json_file(filename)

    imported_count = 0
    invalid_rows = 0
    skipped_count = 0

    for row in records:
        required_values = [
            row.get("name"),
            row.get("email"),
            row.get("department"),
            row.get("salary"),
        ]

        if any(
            value is None or str(value).strip() == ""
            for value in required_values
        ):
            invalid_rows += 1
            continue

        try:
            salary_value = float(row["salary"])

            if salary_value < 0:
                invalid_rows += 1
                continue
        except (TypeError, ValueError):
            invalid_rows += 1
            continue

        try:
            employee_queries.add_employee(
                row["name"].strip(),
                row["email"].strip(),
                row["department"].strip(),
                salary_value,
            )
            imported_count += 1

        except IntegrityError as error:
            if error.errno == 1062:
                skipped_count += 1
            else:
                raise

    return {
        "filename": filename,
        "total_rows": len(records),
        "imported_rows": imported_count,
        "invalid_rows": invalid_rows,
        "skipped_rows": skipped_count,
    }



def import_csv_to_mysql(filename: str) -> dict:
    """Import valid employee rows from a CSV file into MySQL."""
    rows = read_csv_file(filename, UPLOADS_FOLDER)

    imported_count = 0
    invalid_rows = 0
    skipped_count = 0

    for row in rows:
        required_values = [
            row.get("name"),
            row.get("email"),
            row.get("department"),
            row.get("salary"),
        ]

        if any(
            value is None or str(value).strip() == ""
            for value in required_values
        ):
            invalid_rows += 1
            continue

        try:
            salary_value = float(row["salary"])
            if salary_value < 0:
                invalid_rows += 1
                continue
        except (TypeError, ValueError):
            invalid_rows += 1
            continue

        try:
            employee_queries.add_employee(
                row["name"].strip(),
                row["email"].strip(),
                row["department"].strip(),
                salary_value,
            )
            imported_count += 1

        except IntegrityError as error:
            if error.errno == 1062:
                skipped_count += 1
            else:
                raise

    return {
        "filename": filename,
        "total_rows": len(rows),
        "imported_rows": imported_count,
        "invalid_rows": invalid_rows,
        "skipped_rows": skipped_count,
    }


def export_employees_to_csv(filename: str) -> dict:
    """Export employee records from MySQL into a CSV file inside reports."""
    records = employee_queries.get_all_employees()

    file_path = get_csv_file_path(filename, REPORTS_FOLDER)

    with file_path.open("w", encoding="utf-8", newline="") as csv_file:
        writer = csv.DictWriter(
            csv_file,
            fieldnames=["id", "name", "email", "department", "salary"],
        )
        writer.writeheader()
        writer.writerows(records)

    return {
        "filename": filename,
        "rows_written": len(records),
        "location": str(file_path),
    }


def export_employees_to_json(filename: str) -> dict:
    """Export all employee records from MySQL to a JSON file."""
    records = employee_queries.get_all_employees()

    file_path = get_json_file_path(filename, REPORTS_FOLDER)

    with file_path.open("w", encoding="utf-8") as json_file:
        json.dump(records, json_file, indent=4, default=str)

    return {
        "filename": filename,
        "rows_written": len(records),
        "location": str(file_path),
    }
