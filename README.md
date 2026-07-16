# Toy store

A Django-based e-commerce backend built as my last project during the alx prodev backend engineering program. The project demonstrates building production-ready APIs, worker-based background processing, semantic product search, and secure payment integration.

## ALX ProDev Backend Engineering Brief Overview

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

---
