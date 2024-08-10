# IDMC Helix Server 2.0

[![Build Status](https://github.com/idmc-labs/helix-server/actions/workflows/test_runner.yml/badge.svg)](https://github.com/idmc-labs/helix-server/actions)
[![Maintainability](https://api.codeclimate.com/v1/badges/2322f4f0041caffe4742/maintainability)](https://codeclimate.com/github/idmc-labs/helix-server/maintainability)
[![Test Coverage](https://api.codeclimate.com/v1/badges/2322f4f0041caffe4742/test_coverage)](https://codeclimate.com/github/idmc-labs/helix-server/test_coverage)

## Table of Contents
1. [Overview](#overview)
2. [Architecture](#architecture)
3. [Quick Start Guide](#quick-start-guide)
4. [Configuration](#configuration)
5. [Development](#development)
6. [Deployment](#deployment)
7. [API Documentation](#api-documentation)
8. [Database Schema](#database-schema)
9. [User Groups and Authorization Details](#user-groups-and-authorization-details)
10. [Testing](#testing)
11. [Management Commands](#management-commands)
12. [Troubleshooting](#troubleshooting)
13. [Performance and Scaling](#performance-and-scaling)
14. [Contributing](#contributing)

## Overview

Helix Server 2.0 is a modular Django application designed to manage and process various data related to crises, countries, and entries. The project integrates with GraphQL, Redis, AWS S3, and Sentry, and uses environment variables for configuration.

### Main Features
- User authentication and role management
- RESTful and GraphQL APIs for data access
- Modular architecture for maintainability
- Docker support for easy deployment
- Integration with Redis, AWS S3, and Sentry

## Architecture

The Helix Server is structured into several key directories:
- **apps/**: Contains various Django applications, each responsible for a specific domain (e.g., users, contact, crisis).
- **helix/**: Contains core application code, including settings, URLs, and GraphQL schema definitions.
- **deploy/**: Contains deployment scripts and configurations.
- **fixtures/**: Contains JSON files for seeding the database with initial data.
- **utils/**: Contains utility functions and classes used across the application.

### Architectural Patterns
- **Modular Architecture**: The application is structured into multiple Django apps, each encapsulating its functionality, which promotes maintainability and scalability.
- **RESTful and GraphQL APIs**: The application exposes both RESTful and GraphQL APIs, allowing for flexible data retrieval and manipulation.

## Quick Start Guide

1. **Initialize environment**: 
   Create a `.env` file in the project folder. For development, a blank file is fine.

2. **Start the application**:
   ```bash
   docker-compose up
   ```

3. **Initialize database**:
   ```bash
   ./init.sh
   ```

4. **Seed database**:
   ```bash
   docker-compose exec server python manage.py save_users_dummy
   docker-compose exec server python manage.py create_dummy_users
   docker-compose exec server python manage.py loadtestdata <model_names> --count 2
   ```

5. **Access GraphQL interface**: Navigate to `localhost:9000/graphiql`.

## Configuration

The project uses environment variables for configuration. A sample environment file is provided as `.env-sample`. Key configuration options include:
- `DATABASE_URL`: Database connection string
- `SECRET_KEY`: Secret key for Django
- `DEBUG`: Boolean to enable/disable debug mode

For production and staging environments, refer to the `secrets-sample.yml` file for additional configuration options.

## Development

To set up the development environment:

1. Clone the repository:
   ```bash
   git clone https://github.com/idmc-labs/helix-server.git
   cd helix-server
   ```

2. Install dependencies:
   ```bash
   poetry install
   ```

3. Run the development server:
   ```bash
   python manage.py runserver
   ```

## Deployment

### Using Docker Compose

1. Build the Docker containers:
   ```bash
   docker-compose build
   ```

2. Start the services:
   ```bash
   docker-compose up -d
   ```

### Using AWS Copilot

1. Initialize the Copilot application:
   ```bash
   copilot app init --domain idmcdb.org
   copilot init
   ```

2. Deploy the application:
   ```bash
   copilot svc deploy -e ENV
   ```

3. Update the pipeline:
   ```bash
   copilot pipeline update
   ```

### Setup S3 buckets

Create appropriate buckets with required policies based on the `.env`:

```bash
sh deploy/scripts/s3_bucket_setup.sh
```

## API Documentation

### GraphQL API
- **Endpoint**: `/graphql`
- **Interface**: `/graphiql`

To generate a fresh GraphQL schema:
```bash
python manage.py graphql_schema --out schema.graphql
```

### RESTful API Examples

#### User API
- **Endpoint**: `/api/users/`
- **Methods**: 
  - `GET`: List all users
  - `POST`: Create a new user

#### Authentication API
- **Endpoint**: `/api/auth/login/`
- **Methods**: 
  - `POST`: Authenticate user

## Database Schema

Located at `/docs/helix-server-db-schema.sql`, this document offers a detailed description of the Helix Server's database structure. Key features include:

- Overview of the database purpose and design
- Comprehensive list of tables with their primary keys and important fields
- Explanation of key relationships between tables
- Summary of key features in the database schema (e.g., use of UUIDs, versioning system)
- Notes on specific design choices and capabilities

This document is crucial for developers working on database-related tasks or trying to understand the data structure of the Helix Server.

## User Groups and Authorization Details

Located at `/docs/user_groups_auth.md`, this document provides a detailed overview of the user group structure and associated permissions within the Helix Server. Key features include:

- Comprehensive list of user groups (e.g., ADMIN, DIRECTORS_OFFICE, MONITORING_EXPERT)
- Detailed permissions for each user group
- Overview of content types and modules that permissions apply to
- Explanation of different permission types (e.g., can add, can change, can delete)

This document is essential for understanding the role-based access control implemented in the system.

## Testing

To run tests, use the following command:
```bash
pytest
```

Ensure that the test database is set up correctly in your environment variables.

## Management Commands

### Populate figure `Calculation Logic`
```bash
python manage.py populate_calculation_logic_field
```

### Update Household Size and AHHS data
```bash
python manage.py update_ahhs_2024 update_ahhs.csv
```

### Force Update GIDD Data (for local development only)
```bash
python manage.py force_update_gidd_data
```

### Enable two-factor authentication for admin user
```bash
python manage.py addstatictoken -t 123456 "admin@idmcdb.org"
```

### Populate pre-2016 conflict and disaster data for GIDD
```bash
python manage.py update_pre_2016_gidd_data.py old_conflict_data.csv old_disaster_data.csv
```

### Populate IDPs SADD estimates table
```bash
python manage.py update_idps_sadd_estimates idps_sadd_estimates.csv
```

## Troubleshooting

### Common Issues
- **Database connection errors**: Check your `DATABASE_URL` in the environment variables.
- **Docker build failures**: Ensure Docker is running and you have the correct permissions.
- **GraphQL errors**: Check the schema definitions and ensure all required fields are provided.
- **Redis connection issues**: Ensure the Redis service is running and the connection details are correct in the `.env` file.

## Performance and Scaling

The application is designed to handle a growing user base. Key performance considerations include:
- **Caching**: Use Redis for caching frequently accessed data.
- **Database Optimization**: Use indexing on frequently queried fields and query optimization techniques.
- **Load Balancing**: Use a load balancer to distribute traffic across multiple instances.
- **Monitoring**: Use Sentry for error tracking and monitoring.

## Contributing

1. Fork the repository and create your branch from `main`.
2. Ensure your code follows the project's coding standards.
3. Write clear, concise commit messages.
4. Include tests for any new features or bug fixes.
5. Submit a pull request with a detailed description of your changes.

For more detailed information on specific aspects of the project, please refer to the individual documentation files in the repository.
