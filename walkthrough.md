# Fix File Upload Forwarding Issue

## Problem
The user reported that Nginx was not forwarding upload files to the application server, resulting in a `400 Bad Request` and Nginx buffering warnings.

## Root Cause Analysis
- **Nginx Buffering**: Nginx was buffering the large request body to a temporary file (`client_body_buffer_size` exceeded). While this is normal, it can cause issues if the upstream connection times out or if there are permission/disk issues, or if the double-buffering (Nginx -> Django) causes delays.
- **Protocol Mismatch**: Default `proxy_pass` uses HTTP 1.0. Using HTTP 1.1 with `Connection: keep-alive` (or clearing Connection header) is better for large streaming uploads.
- **Django Limit**: The `DATA_UPLOAD_MAX_MEMORY_SIZE` in Django might still be relevant if the request body overhead pushes it over 100MB.

## Changes Made

### 1. Update `nginx/nginx.conf`
Disabled request buffering (`proxy_request_buffering off`) to allow the file to be streamed directly to the backend. Enabled HTTP 1.1 for the proxy connection.

```nginx
    location / {
        proxy_pass http://web_app;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_request_buffering off;
        # ...
    }
```

### 2. Previous Changes (Retained)
- **`apps/cecad/views.py`**: Using UUID for temporary filenames to prevent collisions.
- **`comidanamesa/settings.py`**: `DATA_UPLOAD_MAX_MEMORY_SIZE` is set to 100MB (user reverted 200MB). *Note: If uploads still fail with 400, this limit may need to be increased slightly (e.g. 105MB) to account for multipart overhead.*

## Verification
- Nginx will now stream the upload directly to Gunicorn/Django.
- This should eliminate the Nginx temp file buffering warning and the delay associated with it.
- If the 400 error persists, it is definitely coming from Django (likely the size limit), and we will need to increase `DATA_UPLOAD_MAX_MEMORY_SIZE` slightly.
