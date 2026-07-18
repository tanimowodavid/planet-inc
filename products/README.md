# Products Module

The **Products** module manages the e-commerce catalog, including product definitions, variants (SKUs), and categories. It features **semantic search via embeddings**, **soft delete** for data integrity, and **atomic transactions** for consistency.

## 🧠 Key Features & Logic

### 1. Soft Delete Implementation

To preserve historical records and maintain referential integrity:

- **Active Flag:** Products and variants use an `is_active` boolean instead of hard deletion.
- **Dual Managers:**
  - `objects` (ActiveManager): Returns only active items by default.
  - `all_objects` (Django's default Manager): Access all items including inactive ones (for admins).
- **Query Filtering:** API endpoints automatically filter by `is_active=True`, ensuring inactive products never appear to customers.
- **Data Preservation:** Deactivating a product keeps all historical data intact, essential for order history and auditing.

### 2. Product Embeddings & RAG

- **Vector Storage:** Each product stores a 1536-dimensional embedding using PostgreSQL's pgvector extension.
- **Semantic Search:** Embeddings enable the AI Assistant and storefront search to find contextually relevant products based on user queries, not just literal keyword matches.
- **Auto-Generation:** Embeddings are created automatically when a product is saved, combining name and description.
- **Search Endpoint Support:** The public variants listing endpoint now accepts a `search` query parameter and ranks results by semantic similarity using pgvector cosine distance.
- **Graceful Fallback:** If embedding generation fails, the API falls back to a simple case-insensitive product-name match so the experience remains usable.

### 3. Product Variants (SKUs)

- **Flexible Pricing:** Different variants of the same product can have distinct prices and stock levels.
- **Stock Management:** Each variant tracks its own inventory via `stock_quantity`.
- **Referential Protection:** Using `on_delete=models.PROTECT` prevents accidental deletion of products with active variants.

### 4. Slugs & Uniqueness

- **Auto-Generated Slugs:** Slugs are generated from product names and automatically slugified.
- **UUID Collision Handling:** If a slug collision occurs, a random 4-character hex suffix is appended to ensure uniqueness.
- **Consistency:** The slug-based routing ensures user-friendly, predictable URLs.

### 5. Atomic Transactions

- **Data Consistency:** Product creation and updates are wrapped in `transaction.atomic()` to ensure either all changes succeed or all rollback.
- **Variant Integrity:** If variant creation fails, the entire product creation is rolled back.

## 🛠 API Reference

| Endpoint                | Method      | Permission | Description                                                                              |
| ----------------------- | ----------- | ---------- | ---------------------------------------------------------------------------------------- |
| `/api/categories/`      | `POST`      | Admin      | Create a new category.                                                                   |
| `/api/products/`        | `POST`      | Admin      | Create a new product with embeddings.                                                    |
| `/api/products/<slug>/` | `PUT/PATCH` | Admin      | Update product details.                                                                  |
| `/api/products/`        | `GET`       | Public     | List active product variants; supports optional `search` for semantic product discovery. |
| `/api/products/<sku>/`  | `GET`       | Public     | Retrieve a specific variant by SKU.                                                      |

### Product Creation Example

```json
{
  "name": "Classic Bicycle",
  "description": "A sturdy 10-speed bicycle for outdoor adventures.",
  "category": [1, 2]
}
```

### Semantic Search Example

```http
GET /api/products/?search=lightweight bike for commuting
```

This returns the most semantically relevant variants, ordered by similarity score. If the embedding service is unavailable, the endpoint gracefully falls back to a basic text search over product names.

### Variant Response Example

```json
{
  "sku": "BIKE-001-RED-M",
  "variant_name": "Red, Medium",
  "price": "249.99",
  "stock_quantity": 15,
  "product": {
    "id": 1,
    "name": "Classic Bicycle",
    "slug": "classic-bicycle"
  }
}
```

## 🔒 Security & Integrity

- **Permissions:** Create/Update endpoints require Admin privileges; List/Detail are public.
- **Soft Delete Privacy:** Public endpoints only see active products via the custom manager.
- **Atomic Operations:** All database writes are protected against partial failures.
- **Referential Integrity:** Products with variants cannot be hard-deleted, preventing orphaned records.
