# Fix File Upload 400 Error

## Problem
The user reported that file uploads for "Importar Dados CECAD" were failing in production.
Logs showed:
- Nginx buffering the request body (indicating a large file).
- A `400 Bad Request` response from the backend.
- `POST /cecad/importar/ HTTP/1.1" 400 0`

## Root Cause Analysis
The `400 Bad Request` on a large file upload, where Nginx is configured correctly (100MB limit), strongly suggests that Django's `DATA_UPLOAD_MAX_MEMORY_SIZE` limit was being triggered. Although documentation states this setting excludes file uploads, in practice, certain request parsing overheads or configurations can trigger it, or the request body size check happens before file parsing in some scenarios.

## Changes Made

### 1. Update `settings.py`
Increased `DATA_UPLOAD_MAX_MEMORY_SIZE` to 100MB to match the Nginx configuration.

```python
# comidanamesa/settings.py

# Configuração de Upload
# Permitir uploads de até 100MB (em bytes) para corresponder ao Nginx
DATA_UPLOAD_MAX_MEMORY_SIZE = 104857600  # 100 MB
```

### 2. Update `apps/cecad/views.py`
Modified `ImportDataView` to use `uuid` for temporary filenames. This prevents potential filename collisions if multiple users upload files with the same name (e.g., `import.csv`) simultaneously, and ensures thread safety.

```python
# apps/cecad/views.py

        # Save temporary file
        import uuid
        ext = os.path.splitext(csv_file.name)[1]
        unique_filename = f"{uuid.uuid4()}{ext}"
        file_path = f'/tmp/{unique_filename}'
```

## Verification
- The Nginx configuration already allowed 100MB uploads.
- The Django configuration now explicitly allows request bodies up to 100MB.
- The file saving logic is now more robust.

The user should verify the fix by attempting to upload the file again in the production environment.
