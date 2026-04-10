# Task Manager Assignment

This is a compact full-stack Task Manager built to satisfy the requirements in `full_stack_assignment.pdf`.

## Stack

- Backend: Python standard library HTTP server with a small REST API
- Frontend: HTML, CSS, and vanilla JavaScript
- Storage: File-based persistence using `data/tasks.json`

## Project Structure

```text
task-manager-assignment/
|-- app.py
|-- Dockerfile
|-- docker-compose.yml
|-- README.md
|-- data/
|   `-- tasks.json
`-- static/
    |-- app.js
    |-- index.html
    `-- styles.css
```

## Features

- Display all tasks
- Add a new task with validation
- Mark a task as completed or pending
- Delete a task
- Show loading, empty, and error states
- Return clear JSON responses from the API
- Bonus features included:
  - Filter tasks by all, pending, or completed
  - Edit an existing task title
  - Persist tasks after refresh

## Run Locally

1. Open a terminal in this folder:

```powershell
cd C:\Users\ns190\Downloads\CongnitiveLoad-Detection-main\task-manager-assignment
```

2. Start the app:

```powershell
python app.py
```

3. Open:

```text
http://127.0.0.1:8000
```

If port `8000` is already in use, run it on another port:

```powershell
$env:PORT=8123
python app.py
```

## Run With Docker

Build and run with Docker:

```powershell
docker build -t task-manager-assignment .
docker run -p 8000:8000 task-manager-assignment
```

Or with Docker Compose:

```powershell
docker compose up --build
```

## API Endpoints

- `GET /tasks` returns all tasks
- `GET /tasks?status=pending` returns incomplete tasks
- `GET /tasks?status=completed` returns completed tasks
- `POST /tasks` creates a task
- `PATCH /tasks/:id` updates `title` and/or `completed`
- `DELETE /tasks/:id` deletes a task

## Example Payloads

Create a task:

```json
{
  "title": "Finish the frontend integration"
}
```

Update a task:

```json
{
  "completed": true
}
```

Rename a task:

```json
{
  "title": "Review API validation responses"
}
```

## Validation and Error Handling

- Rejects empty task titles on create and update
- Rejects malformed JSON requests
- Rejects invalid `completed` values when they are not boolean
- Returns clear JSON error messages for missing routes and missing tasks

## Submission Notes

- The solution intentionally stays small to match the assignment scope.
- The backend uses only Python standard library modules, so it runs without package installation.
- The UI is more polished than the minimum requirement, but the implementation still stays lightweight and readable.

## Assumptions and Trade-offs

- Used Python standard library so the project can run without installing packages in this environment.
- Kept the architecture intentionally small to match the assignment scope.
- Added title editing and filtering because they are listed as optional bonus items and fit naturally without adding complexity.
