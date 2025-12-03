# Discount System Documentation

## Overview
The discount system allows approved sellers to create special discount days where they offer a percentage discount on their products. The system also tracks discount day statistics and integrates with the order system to apply discounts automatically.

## 1. DiscountDay Model Features
The `DiscountDay` model includes the following fields and features:

- `seller`: The user (seller) who created the discount day
- `date`: The date when the discount is active
- `discount_percentage`: The percentage discount to apply (e.g., 10.00 for 10%)
- `is_active`: Boolean field to indicate if the discount day is active
- `created_at`: Timestamp of when the discount day was created

**Key Features:**
- Uniqueness constraint ensuring one discount day per seller per date
- Automatic discount application to order items created on discount dates
- Integration with the order system to track discounted sales

## 2. Create Discount Day (POST)
To create a new discount day, send a POST request to `/api/discount-day/`:

**Endpoint:** `POST /api/discount-day/`

**Required Headers:**
- `Authorization: Bearer <your_token>` (after logging in)

**Request Body:**
```json
{
  "date": "2023-12-25",
  "discount_percentage": 15.00,
  "is_active": true
}
```

**Parameters:**
- `date`: The date for the discount day (format: YYYY-MM-DD) - required
- `discount_percentage`: The discount percentage to apply (e.g., 15.00 for 15%) - required
- `is_active`: Whether the discount day is active (true/false) - optional, defaults to true

**Response:**
- On success: Returns the created discount day object with status 201 Created
- On error: Returns error details with appropriate status code

**Response Example:**
```json
{
  "id": 1,
  "seller": 2,
  "date": "2023-12-25",
  "discount_percentage": "15.00",
  "created_at": "2023-12-03T10:30:00Z",
  "is_active": true
}
```

**Behavior:**
- Only authenticated sellers can create discount days
- The `seller` field is automatically populated with the authenticated user
- A seller cannot create multiple discount days for the same date
- The discount percentage is applied to eligible orders on the specified date

## 3. Read Discount Days (GET)
The system supports multiple ways to read discount days:

**Endpoint 1: List all discount days**
`GET /api/discount-day/`

**Required Headers:**
- No authentication required (public endpoint)

**Response:**
- Returns an array of all discount days ordered by date (newest first)

**Response Example:**
```json
[
  {
    "id": 1,
    "seller": 2,
    "date": "2023-12-25",
    "discount_percentage": "15.00",
    "created_at": "2023-12-03T10:30:00Z",
    "is_active": true
  },
  {
    "id": 2,
    "seller": 3,
    "date": "2023-12-20",
    "discount_percentage": "10.00",
    "created_at": "2023-12-01T09:15:00Z",
    "is_active": true
  }
]
```

**Endpoint 2: Get specific discount day details**
`GET /api/discount-day/{pk}/`

**Required Headers:**
- `Authorization: Bearer <your_token>` (only the seller can view their own discount day)

**Parameters:**
- `pk`: Primary key (ID) of the specific discount day to retrieve

**Response:**
- Returns details of the specific discount day

**Response Example:**
```json
{
  "id": 1,
  "seller": 2,
  "date": "2023-12-25",
  "discount_percentage": "15.00",
  "created_at": "2023-12-03T10:30:00Z",
  "is_active": true
}
```

**Behavior:**
- Public endpoint returns all discount days
- Individual discount day endpoint requires authentication and ownership (only the seller can access their discount day)

## 4. Update Discount Day (PATCH)
To update an existing discount day, send a PATCH request to the following endpoint:

**Endpoint:** `PATCH /api/discount-day/{pk}/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Parameters:**
- `pk`: Primary key (ID) of the discount day to update

**Request Body:**
```json
{
  "discount_percentage": 20.00,
  "is_active": false
}
```

**Parameters (all optional):**
- `date`: The new date for the discount day (format: YYYY-MM-DD) - cannot be in the past
- `discount_percentage`: The new discount percentage
- `is_active`: Whether the discount day is active

**Response:**
- On success: Returns the updated discount day object with status 200 OK
- On error: Returns error details with appropriate status code

**Response Example:**
```json
{
  "id": 1,
  "seller": 2,
  "date": "2023-12-25",
  "discount_percentage": "20.00",
  "created_at": "2023-12-03T10:30:00Z",
  "is_active": false
}
```

**Behavior:**
- Only allows updates to discount days that belong to the authenticated seller
- Date cannot be changed to a past date
- PATCH allows partial updates (only certain fields)
- Returns 404 if the discount day doesn't exist or doesn't belong to the seller

## 5. Delete Discount Day (DELETE)
To delete a discount day, send a DELETE request to the following endpoint:

**Endpoint:** `DELETE /api/discount-day/{pk}/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Parameters:**
- `pk`: Primary key (ID) of the discount day to delete

**Response:**
- On success: Returns status 204 with message "Discount day deleted successfully"
- On error: Returns error details with appropriate status code

**Behavior:**
- Only allows deletion of discount days that belong to the authenticated seller
- Permanently removes the discount day from the seller's schedule
- Returns 404 if the discount day doesn't exist or doesn't belong to the seller

## 6. Seller Discount Statistics (GET)
The discount system includes comprehensive statistics functionality accessible through the SellerStatsView:

**Endpoint:** `GET /api/seller/stats/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Query Parameters:**
- `type`: Either "discount" (default) or "non-discount"
- `date`: For "discount" type, specifies a specific date to get stats for
- `start_date` and `end_date`: For "non-discount" type, specifies the date range
- `view`: Either "products" for detailed product info or "stats" for summary

**Response (for discount type - all discount days):**
```json
{
  "stats_type": "discount_days",
  "discount_day_stats": [
    {
      "discount_day_id": 1,
      "date": "2023-12-25",
      "discount_percentage": "15.00",
      "total_items_sold": 5,
      "total_profit": 120.50,
      "total_original_revenue": 142.50,
      "total_discount_amount": 22.00
    }
  ],
  "summary": {
    "total_discount_days": 1,
    "total_items_sold_during_discount_days": 5,
    "total_profit_from_discount_days": 120.50,
    "total_discount_given": 22.00
  }
}
```

**Response (for specific discount day):**
```json
{
  "discount_day_id": 1,
  "date": "2023-12-25",
  "discount_percentage": "15.00",
  "total_items_sold": 5,
  "total_profit": 120.50,
  "total_original_revenue": 142.50,
  "total_discount_amount": 22.00
}
```

**Response (for non-discount type):**
```json
{
  "stats_type": "non_discount_days",
  "stats": {
    "total_items_sold": 15,
    "total_profit": 300.00
  }
}
```

**Behavior:**
- Accessible only to authenticated sellers
- Provides detailed analytics on discount day performance
- Shows revenue comparison between original prices and discounted prices
- Allows comparison of discount vs. non-discount day performance
- Supports filtering by specific dates or date ranges

## Integration with Orders
When customers purchase products on discount days, the system automatically applies the discount and tracks:
- The original price of the product
- The discount percentage applied
- The final price after discount
- The total discount amount given

This information is reflected in the order details and contributes to the discount statistics available to sellers.