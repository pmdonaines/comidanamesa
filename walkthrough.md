# Docker Compose Walkthrough

I have configured the project to run with Docker Compose, Nginx, and PostgreSQL.

## Prerequisites
- Docker
- Docker Compose

## How to Run

1.  **Create `.env` file**:
    Copy the example file and adjust values if needed.
    ```bash
    cp .env.docker.example .env
    ```

2.  **Build and Run**:
    ```bash
    docker compose up --build
    ```

3.  **Access the Application**:
    The application will be available at [http://localhost](http://localhost).

## Configuration Details

- **Django**: Runs on port 8000 internally, exposed via Nginx on port 80.
- **PostgreSQL**: Database service, data persisted in `postgres_data` volume.
- **Nginx**: Serves static/media files and proxies requests to Django.

## Initial Setup

The database migrations and a default superuser are created automatically when the container starts.

**Default credentials:**
- Username: `admin`
- Password: `admin`
- Email: `admin@localhost`

> [!WARNING]
> Change the default password immediately in production!

## Auto-start on Boot

To ensure the application starts automatically when the system reboots:

1.  **Enable Docker Service**:
    Ensure the Docker daemon is configured to start on boot.
    ```bash
    sudo systemctl enable docker
    ```

2.  **Restart Policy**:
    The services in `docker-compose.yml` are configured with `restart: always`, so they will start automatically when the Docker daemon starts.

## Maintenance

- **Migrations**:
    ```bash
    docker compose exec web uv run python manage.py migrate
    ```
- **Create Superuser**:
    ```bash
    docker compose exec web uv run python manage.py createsuperuser
    ```
- **Associate Criteria to Validations** (run after importing families):
    ```bash
    docker compose exec web uv run python manage.py associar_criterios
    ```
- **Verify Scoring**:
    ```bash
    docker compose exec web uv run python manage.py verificar_pontuacao
    ```
