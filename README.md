# Employee Management REST API

A REST API built with Python, FastAPI, and MySQL for managing employee records and working with text, CSV, and JSON files.

## Features

- Create, retrieve, update, delete, and search employee records.
- Validate employee fields and reject duplicate email addresses when the database enforces uniqueness.
- Create, read, write, append, rename, copy, and delete text files.
- Import employee data from CSV and JSON files and export employee reports to CSV and JSON.
- Upload supported `.txt`, `.csv`, and `.json` files up to 1 MB.
- List, download, and delete generated report files.
- Restrict filenames to safe characters and keep file operations within the `uploads/` and `reports/` folders.
- Explore and try the API through the automatically generated Swagger UI and ReDoc documentation.

## Technology

- Python 3.10 or later
- FastAPI
- MySQL
- `mysql-connector-python`
- Uvicorn
- `python-dotenv`
- `python-multipart`

## Project structure

```text
employee_api/
├── main.py                 # FastAPI app and routes
├── database.py             # MySQL connection setup
├── employee_queries.py     # Employee database operations
├── file_operations.py      # File, CSV, and JSON operations
├── requirements.txt
├── uploads/                # Uploaded input files and text files
└── reports/                # Generated CSV and JSON reports
```

The `uploads/` and `reports/` directories are created as needed by file operations. Files created through the API are stored locally in these directories.

## Requirements

- Python 3.10+
- A running MySQL Server
- Git (to clone the repository)

## Installation and setup

1. Clone the repository and enter the project directory:

   ```powershell
   git clone <YOUR_GITHUB_REPOSITORY_URL>
   cd employee_api
   ```

2. Create and activate a virtual environment:

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   If PowerShell prevents script activation, you can use the virtual environment's interpreter directly with `.venv\Scripts\python.exe`.

3. Install the dependencies:

   ```powershell
   python -m pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root:

   ```dotenv
   DB_HOST=localhost
   DB_USER=your_mysql_username
   DB_PASSWORD=your_mysql_password
   DB_NAME=employee_management
   ```

   `database.py` loads these settings from the project-root `.env` file. `DB_HOST`, `DB_USER`, and `DB_NAME` are required. Set `DB_PASSWORD` to the password for your MySQL user.

5. Create the database and employee table. For example, run this SQL in MySQL:

   ```sql
   CREATE DATABASE employee_management;
   USE employee_management;

   CREATE TABLE employees (
       id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
       name VARCHAR(255) NOT NULL,
       email VARCHAR(255) NOT NULL UNIQUE,
       department VARCHAR(255) NOT NULL,
       salary DECIMAL(12, 2) NOT NULL
   );
   ```

   The unique constraint on `email` enables duplicate-email prevention.

6. Start the development server from the project directory:

   ```powershell
   python -m uvicorn main:app --reload
   ```

   The server is available at `http://127.0.0.1:8000` by default.

## API documentation

With the server running, visit:

- Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- OpenAPI schema: [http://127.0.0.1:8000/openapi.json](http://127.0.0.1:8000/openapi.json)

## Endpoints

### Employees

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/employees` | Create an employee. Requires `name`, `email`, `department`, and `salary`. |
| `GET` | `/employees` | Return all employees. |
| `GET` | `/employees/search?name=...&department=...` | Search by name, department, or both. At least one search term is required. |
| `GET` | `/employees/{employee_id}` | Return one employee by ID. |
| `PATCH` | `/employees/{employee_id}` | Update one or more supplied employee fields. |
| `DELETE` | `/employees/{employee_id}` | Delete an employee by ID. |

Employee request bodies use JSON. The allowed fields are `name`, `email`, `department`, and `salary`. Text fields must be non-empty strings; email receives a basic format check; salary must be a non-negative number.

Example create request:

```json
{
  "name": "Jordan Lee",
  "email": "jordan.lee@example.com",
  "department": "Engineering",
  "salary": 85000
}
```

Example partial update:

```json
{
  "department": "Platform"
}
```

### Text files

Text files are stored in `uploads/`. Supply a filename ending in `.txt` and containing only letters, numbers, underscores, or hyphens before the extension.

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/files/text/{filename}` | Create an empty text file. |
| `PUT` | `/files/text/{filename}` | Create or replace a file's content. JSON body: `{"content":"..."}`. |
| `POST` | `/files/text/{filename}/append` | Append content. JSON body: `{"content":"..."}`. |
| `GET` | `/files/text/{filename}` | Read all file content. |
| `GET` | `/files/text/{filename}/lines` | Read content as a list of lines. |
| `GET` | `/files/text/{filename}/exists` | Check whether the file exists. |
| `GET` | `/files/text/{filename}/size` | Get the file size in bytes. |
| `POST` | `/files/text/{filename}/rename?new_filename=...` | Rename a text file. |
| `POST` | `/files/text/{filename}/copy?copy_filename=...` | Copy a text file. |
| `DELETE` | `/files/text/{filename}` | Delete a text file. |

### CSV and JSON

CSV and JSON import files must first be present in `uploads/`, either by uploading them or placing them there. Import endpoints take a `filename` query parameter.

| Method | Endpoint | Description |
| --- | --- | --- |
| `GET` | `/files/csv/{filename}` | Read CSV rows from `uploads/`. |
| `POST` | `/files/csv/import?filename=...` | Import valid CSV employee rows into MySQL. |
| `POST` | `/files/json/import?filename=...` | Import employee records from a JSON list into MySQL. |
| `POST` | `/files/csv/export?filename=...` | Export employees to a CSV file in `reports/`. |
| `POST` | `/files/json/export?filename=...` | Export employees to a JSON file in `reports/`. |

CSV files must have `name`, `email`, `department`, and `salary` columns. JSON files must contain a list of objects with those employee fields. Imports count rows with missing or invalid required values as invalid and skip duplicate rows when the database reports a duplicate key. Import responses include total, imported, invalid, and skipped row counts.

Example JSON import file:

```json
[
  {
    "name": "Jordan Lee",
    "email": "jordan.lee@example.com",
    "department": "Engineering",
    "salary": 85000
  }
]
```

Export filenames must end in `.csv` or `.json` as appropriate.

### Uploads and reports

| Method | Endpoint | Description |
| --- | --- | --- |
| `POST` | `/files/upload` | Upload a `.txt`, `.csv`, or `.json` file using multipart form field `file`. Maximum size: 1 MB. |
| `GET` | `/files/reports` | List supported report files and their sizes. |
| `GET` | `/files/download/{filename}` | Download a report from `reports/`. |
| `DELETE` | `/files/reports/{filename}` | Delete a report from `reports/`. |

## Responses and errors

The API returns FastAPI's standard JSON error responses. Common status codes include:

- `201` — Resource created.
- `400` — Malformed JSON file or missing upload filename.
- `404` — Employee or file not found.
- `409` — Duplicate employee email or a text-file destination already exists.
- `413` — Uploaded file exceeds 1 MB.
- `422` — Invalid employee input, filename, or file content.
- `503` — Database operation failed.

Other errors may be returned for filesystem permission or operation failures. Use `/docs` to inspect each endpoint's request and response schemas.

## Testing

The project has been manually exercised through Swagger UI and Postman. No automated test suite is currently included.

## Security notes

- Do not commit `.env`, database credentials, or other secrets.
- Use a unique email constraint in MySQL to enforce duplicate prevention reliably.
- The API does not implement authentication or authorization. Do not expose it to untrusted networks without adding access controls.
- Uploaded files are stored on the local filesystem; consider storage limits, access controls, and cleanup policies before deployment.

## Author

**Your Name**

GitHub: [Your GitHub Profile](https://github.com/)

Replace these placeholders with your author name and profile before publishing.
