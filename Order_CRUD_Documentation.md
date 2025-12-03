# Order CRUD Operations Documentation

## 1. Create Order (POST)
To create a new order, send a POST request to `/api/orders/` with the following parameters:

**Endpoint:** `POST /api/orders/`

**Required Headers:**
- `Authorization: Bearer <your_token>` (after logging in)

**Request Body:**
```json
{
  "items": [
    {
      "product_id": 1,
      "quantity": 2
    },
    {
      "product_id": 3,
      "quantity": 1
    }
  ],
  "payment": "Cash on Delivery",
  "card_number": "1234567890123456"
}
```

**Parameters:**
- `items`: Array of objects containing `product_id` and `quantity`
- `payment`: Payment method ("Cash on Delivery", "Pay Maya", "G-Cash", "B.P.I", "Go Tyme", "Others")
- `card_number`: 16-digit card number (required field)

**Response:**
- On success: Returns the created order object with status 201 Created
- On error: Returns error details with appropriate status code (400, 404, etc.)

**Behavior:**
- Checks if the user is authenticated
- Verifies stock availability for all items
- Creates order items and reduces product stock
- Applies discounts automatically if it's a discount day for the seller
- Returns a complete order object with unique order number

## 2. Read Orders (GET)
There are two ways to read orders in the system:

**Endpoint 1: List all user's orders**
`GET /api/orders/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Response:**
- Returns an array of all orders belonging to the authenticated user, sorted by creation date (newest first)

**Endpoint 2: Get specific order details**
`GET /api/orders/{order_number}/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Parameters:**
- `order_number`: UUID of the specific order to retrieve

**Response:**
- Returns details of the specific order if it belongs to the authenticated user
- Includes order items, status, payment method, and other order details

**Response Example:**
```json
{
  "number": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2023-12-03T10:30:00Z",
  "updated_at": "2023-12-03T10:30:00Z",
  "status": "Pending",
  "payment": "Cash on Delivery",
  "is_paid": false,
  "order_items": [
    {
      "number": "550e8400-e29b-41d4-a716-446655440001",
      "quantity": 2,
      "created_at": "2023-12-03T10:30:00Z",
      "updated_at": "2023-12-03T10:30:00Z",
      "status": "Pending",
      "product": {
        "id": 1,
        "name": "Sample Product",
        "price": "15.99"
      },
      "sub_total": "31.98"
    }
  ],
  "total_amount": 31.98,
  "total_original_amount": 31.98,
  "total_discount_amount": 0.00
}
```

**Behavior:**
- Only returns orders that belong to the authenticated user
- Returns 404 if the order doesn't exist or doesn't belong to the user

## 3. Update Orders (PUT/PATCH)
To update an existing order, send a PUT or PATCH request to the following endpoint:

**Endpoint:** `PUT /api/orders/{order_number}/` or `PATCH /api/orders/{order_number}/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Parameters:**
- `order_number`: UUID of the order to update

**Request Body:**
```json
{
  "status": "On Delivery",
  "payment": "Pay Maya"
}
```

**Parameters (both optional for PATCH, at least one required):**
- `status`: New order status ("Cancelled", "Pending", "On Delivery")
- `payment`: New payment method ("Cash on Delivery", "Pay Maya", "G-Cash", "B.P.I", "Go Tyme", "Others")

**Response:**
- On success: Returns the updated order object with status 200 OK
- On error: Returns error details with appropriate status code

**Response Example:**
```json
{
  "number": "550e8400-e29b-41d4-a716-446655440000",
  "created_at": "2023-12-03T10:30:00Z",
  "updated_at": "2023-12-03T12:15:00Z",
  "status": "On Delivery",
  "payment": "Pay Maya",
  "user": 2,
  "order_items": [
    {
      "number": "550e8400-e29b-41d4-a716-446655440001",
      "quantity": 2,
      "created_at": "2023-12-03T10:30:00Z",
      "updated_at": "2023-12-03T10:30:00Z",
      "status": "On Delivery",
      "product": {
        "id": 1,
        "name": "Sample Product",
        "price": "15.99"
      },
      "sub_total": "31.98"
    }
  ],
  "total_amount": 31.98,
  "total_original_amount": 31.98,
  "total_discount_amount": 0.00
}
```

**Behavior:**
- Only allows updates to orders that belong to the authenticated user
- Only the `status` and `payment` fields can be updated (order items cannot be modified to maintain order integrity)
- PUT requires at least one of the updatable fields to be provided
- PATCH allows partial updates (only certain fields)
- Returns 404 if the order doesn't exist or doesn't belong to the user

## 4. Delete Order (DELETE)
To delete an order, send a DELETE request to the following endpoint:

**Endpoint:** `DELETE /api/orders/{order_number}/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Parameters:**
- `order_number`: UUID of the order to delete

**Response:**
- On success: Returns status 204 with message "Order deleted successfully"
- On error: Returns 404 if the order doesn't exist or doesn't belong to the authenticated user

**Behavior:**
- Only allows deletion of orders that belong to the authenticated user
- Permanently removes the order from the user's order history
- Does not restore the stock of the products in the deleted order