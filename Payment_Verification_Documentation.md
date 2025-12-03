# Payment Verification Documentation

## Overview
The payment system now includes a verification feature that allows users to mark an order as paid when the correct payment amount is provided. The system supports multiple payment methods including Cash on Delivery (COD) and card-based payments.

## Payment Methods
The system supports the following payment methods:
- Cash on Delivery (COD)
- Pay Maya
- G-Cash
- B.P.I (BPI)
- Go Tyme
- Others

## Payment Verification (POST)
To verify payment for an order, send a POST request to `/api/payment/`:

**Endpoint:** `POST /api/payment/`

**Required Headers:**
- `Authorization: Bearer <your_token>` (after logging in)

### For Cash on Delivery (COD):
```json
{
  "order_number": "550e8400-e29b-41d4-a716-446655440000",
  "amount": 31.98
  // No card_number required for COD
}
```

### For Card-Based Payments:
```json
{
  "order_number": "550e8400-e29b-41d4-a716-446655440000",
  "amount": 31.98,
  "card_number": "1234567890123456"
}
```

**Parameters:**
- `order_number`: The UUID of the order to verify payment for (required)
- `amount`: The amount being paid (required, must be >= order total)
- `card_number`: 16-digit card number (required for non-COD payments, should not be provided for COD)

**Response:**
- On success: Returns success message with status 200 OK
- On error: Returns error details with appropriate status code

**Response Example (Success):**
```json
{
  "message": "Payment processed successfully",
  "order_number": "550e8400-e29b-41d4-a716-446655440000",
  "total_amount": 31.98,
  "is_paid": true,
  "payment_method": "Cash on Delivery"
}
```

**Response Example (Error - Amount Too Low):**
```json
{
  "error": "Payment amount is less than order total. Required: 31.98, Provided: 30.00"
}
```

**Response Example (Error - Missing Card Number for Card-Based Payment):**
```json
{
  "error": "Card number is required for Pay Maya"
}
```

**Response Example (Error - Card Number Provided for COD):**
```json
{
  "error": "Card number is not required for Cash on Delivery"
}
```

**Behavior:**
- Only allows payment verification for orders that belong to the authenticated user
- Compares the provided amount against the order's total_amount property (payment must be >= order total)
- For COD payments: No card number required
- For card-based payments: 16-digit card number required and validated
- Updates the order's `is_paid` field to `true` when payment is verified
- Optionally updates status from "Pending" to "On Delivery" when paid
- Returns 404 if the order doesn't exist or doesn't belong to the user
- Returns 400 if the payment amount doesn't match the order total, or if card number requirements aren't met

## Order Model Changes
- Added `is_paid` boolean field to the Order model
- Default value is `False` for new orders
- Added `PaymentChoice` TextChoices for different payment methods
- When payment is verified, the field is set to `True` and order status may be updated

## Integration with Orders
- Payment status is now returned as part of order details
- Orders can be filtered or queried based on their payment status
- The payment verification endpoint ensures payment integrity by comparing amounts
- Order creation no longer requires card number information - this is only needed during payment processing