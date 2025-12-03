# Soft Delete Functionality for Products

This document explains how to test and use the soft delete functionality for products in the Django application.

## How Soft Delete Works

Soft delete means that when a product is "deleted", it's not actually removed from the database. Instead, a `deleted_at` timestamp is added to mark it as deleted. This allows for:

- Recovery of accidentally deleted products
- Maintaining data integrity for related records
- Audit trail of deletions

## API Endpoints

### 1. Soft Delete a Product

**Endpoint:** `DELETE /api/product/{id}/`

**Description:** Performs a soft delete on a product. The product is not removed from the database, but marked as deleted.

**Example Request:**
```
DELETE /api/product/1/
Authorization: Bearer <your_token>
```

**Response:**
```json
{
    "message": "Product soft deleted successfully"
}
```

### 2. Retrieve Soft Deleted Products

**Endpoint:** `GET /api/products/deleted/`

**Description:** Retrieves all soft deleted products that belong to the authenticated user.

**Example Request:**
```
GET /api/products/deleted/
Authorization: Bearer <your_token>
```

**Response:**
```json
[
    {
        "id": 1,
        "name": "Product Name",
        "description": "Product Description",
        "price": "10.99",
        "stock": 5,
        "status": "Available",
        "user_id": 1,
        "store_owner": "username",
        "deleted_at": "2023-12-03T10:30:00Z"
    }
]
```

### 3. Restore a Soft Deleted Product

**Endpoint:** `POST /api/product/{id}/restore/`

**Description:** Restores a soft deleted product by removing the `deleted_at` timestamp.

**Example Request:**
```
POST /api/product/1/restore/
Authorization: Bearer <your_token>
```

**Response:**
```json
{
    "message": "Product restored successfully",
    "product": {
        "id": 1,
        "name": "Product Name",
        "description": "Product Description",
        "price": "10.99",
        "stock": 5,
        "status": "Available",
        "user_id": 1,
        "store_owner": "username",
        "deleted_at": null
    }
}
```

## Testing Soft Delete Functionality

### Test Scenarios

1. **Soft Delete Test**: Verify that products are soft deleted and not removed from the database
2. **Restore Test**: Verify that soft deleted products can be restored
3. **User Isolation Test**: Verify that users can only see their own deleted products
4. **Manager Behavior Test**: Verify that the default manager excludes soft deleted products
5. **Hard Delete Test**: Verify that hard delete (with soft=False) completely removes products

### Test Commands

To run the tests:

```bash
python manage.py test products
```

## Django Model Implementation

The Products model includes:

- `deleted_at` field to track when a product was soft deleted
- `SoftDeleteManager` as the default manager (excludes soft deleted products)
- `all_objects` manager to access all products (including soft deleted)
- `delete(soft=True)` method that handles both soft and hard delete
- `restore()` method to recover soft deleted products

## Backend Logic

### SoftDeleteManager
- `objects` (default): Returns only active (non-deleted) products
- `all_with_deleted()`: Returns all products including soft deleted ones
- `only_deleted()`: Returns only soft deleted products

### Class Methods
- `get_deleted_products_for_user(user)`: Returns soft deleted products for a specific user
- `objects_active()`: Returns only active (non-deleted) products