# Docker Setup Guide

This guide provides instructions on how to set up and run the Music School platform using Docker and Docker Compose.

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed on your machine.
- [Docker Compose](https://docs.docker.com/compose/install/) installed on your machine.

## Getting Started

1.  **Clone the repository** (if you haven't already):

    ```bash
    git clone <repository-url>
    cd <repository-directory>
    ```

2.  **Build and start the containers**:

    ```bash
    docker-compose up --build
    ```

    This command will build the images for both the backend and frontend and start the containers. The `--build` flag ensures that the images are rebuilt if there are any changes to the Dockerfiles or dependencies.

3.  **Access the application**:

    - **Frontend**: [http://localhost:3000](http://localhost:3000)
    - **Backend API**: [http://localhost:8000](http://localhost:8000)
    - **Backend API Documentation (Swagger)**: [http://localhost:8000/docs](http://localhost:8000/docs)

## Configuration

- **Environment Variables**: You can modify the environment variables in the `docker-compose.yml` file.
    - `DATABASE_URL`: The URL for the database (default is SQLite in the backend container).
    - `VITE_API_BASE_URL`: The base URL for the backend API from the frontend perspective.
- **Volumes**:
    - The backend source code is mounted as a volume, allowing for live reloading during development.
    - The `uploads` directory is mounted as a volume to persist uploaded files.

## Common Commands

- **Stop the containers**:

    ```bash
    docker-compose down
    ```

- **View logs**:

    ```bash
    docker-compose logs -f
    ```

- **Run tests in the backend container**:

    ```bash
    docker-compose exec backend pytest
    ```

- **Access the backend container's shell**:

    ```bash
    docker-compose exec backend /bin/bash
    ```

- **Access the frontend container's shell**:

    ```bash
    docker-compose exec frontend /bin/sh
    ```

## Notes

- The default admin credentials are `admin` / `password123`.
- The system automatically handles database migrations and initial seeding upon startup.
