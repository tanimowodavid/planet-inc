# Planet Inc

A Django-based e-commerce backend built as part of the ALX ProDev Backend Engineering program. The project demonstrates building production-ready APIs, worker-based background processing, semantic product search, and secure payment integration.

## ProDev Backend Engineering Brief Overview

The ALX ProDev Backend program is a project-driven training focused on practical backend engineering skills and best practices.

- **Major learnings:** building maintainable APIs, deploying services with containers, and designing resilient background jobs.
- **Key technologies covered:** Python, Django, Django REST Framework, GraphQL, Docker, CI/CD pipelines.
- **Important backend concepts:** Database design and migrations, asynchronous programming (Celery/workers), caching strategies (e.g., Redis), testing, DevOps basic....
- **Challenges & solutions:** handling concurrent updates to inventory (solved with `select_for_update()` and sorted locking), ensuring idempotent background tasks, and integrating third-party payment flows (Paystack) with safe callback verification.
- **Best practices & takeaways:** A fast API is nice. A predictable API is better. A fast + predictable API gets you the “wow” reactions.

## Project Overview

- Apps: `address`, `ai_assistant`, `carts`, `orders`, `products`, `users`, and core project settings in `planet_core`.
  > each app has its own readme for api list and proper documentation.
- Features: product embeddings (pgvector), RAG-enabled AI assistant, Paystack payment integration, Celery background workers, and soft-delete for catalog items.

## Technologies Used

- Django: For building a scalable backend framework.
- PostgreSQL: As the relational database for optimized performance.
- JWT: For secure user authentication.
- drt_spectacular: To document and test APIs.
- Celery: Background workers
- Paystack API: Payment processing

## Quickstart (Docker)

This repository is dockerized. The recommended workflow is to use `docker-compose` for development.

1. Copy or create a `.env` file with required secrets:

```bash
cp .env.example .env
```

2. Build and start services:

```bash
docker-compose up --build -d
```

3. Run migrations inside the web container:

```bash
docker-compose exec web python manage.py migrate
```

4. Seed test data (a management command exists in the `products` app):

```bash
# from project root
docker-compose exec web python manage.py seed
```

Note: the seed command is located at `products/management/command/seed.py` in this repository.

## Background Workers

- Celery is used for asynchronous tasks (e.g., `process_order_payment` in `orders/tasks.py`).
- Ensure a running broker (Redis/RabbitMQ) and start workers using the command above or via your `docker-compose` service.

## Payment Integration

- Paystack is used for payment initialization and verification (`orders/services.py`).
- Ensure `PAYSTACK_SECRET_KEY` is set in your environment; amounts are sent to Paystack in the smallest currency unit (e.g., kobo).

## Testing

This project includes comprehensive test coverage using **pytest** and **pytest-django**. Tests are organized by app and cover models, views, serializers, and API endpoints.

### Test Structure

Each Django app contains a `tests.py` file with organized test classes:

- **Model Tests**: Test model creation, validation, relationships, and custom methods
- **Serializer Tests**: Test data serialization and validation (where applicable)
- **API Tests**: Test endpoints, permissions, status codes, and response data
- **Integration Tests**: Test workflows involving multiple components

### Running Tests

#### Prerequisites

Install pytest and related dependencies:

```bash
pip install pytest pytest-django pytest-cov
```

Or if using the provided `requirements.txt`:

```bash
pip install -r requirements.txt
```

#### Run All Tests

```bash
pytest
```

### Docker Testing

To run tests inside the Docker container:

```bash
docker-compose exec web pytest
docker-compose exec web pytest --cov=. carts/
docker-compose exec web pytest -v users/tests.py::UserRegistrationTests
```

---
