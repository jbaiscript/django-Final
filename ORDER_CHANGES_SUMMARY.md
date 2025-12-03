# Order Creation and Payment Processing Changes

## Summary of Changes

This document outlines the changes made to implement the requested functionality:
- Remove "card_number" requirement during order creation
- Allow users to choose between payment methods from `PaymentChoice` enum
- Only require card_number during payment processing, not during order creation
- For Cash on Delivery (COD), no card number should be required

## Files Modified

### 1. `products/serializers.py`

- **OrderSerializer**: Removed `card_number` field from order creation
- **PaymentSerializer**: Added custom validation to ensure card number is required for non-COD payments and not allowed for COD

### 2. `products/views.py`

- **OrderView.post()**: Removed card number validation during order creation, added payment method validation
- **CustomerOrderView.post()**: Removed card number validation during order creation, added payment method validation  
- **PaymentView.post()**: Enhanced payment processing logic to handle COD vs. card-based payments differently

## API Changes

### Order Creation (POST /orders/ and POST /orders/customer/)

**Before:**
```json
{
  "items": [
    {
      "product_id": 9,
      "quantity": 2
    }
  ],
  "payment": "Cash on Delivery",
  "card_number": "1234567890123456"
}
```

**After:**
```json
{
  "items": [
    {
      "product_id": 9,
      "quantity": 2
    }
  ],
  "payment": "Cash on Delivery"
}
```

### Payment Processing (POST /payment/)

**For COD (Cash on Delivery):**
```json
{
  "order_number": "12345-abcde",
  "amount": 150.00
  // No card_number required
}
```

**For Card-Based Payments:**
```json
{
  "order_number": "12345-abcde",
  "amount": 150.00,
  "card_number": "1234567890123456"
}
```

## Payment Methods Available

Users can choose from the following payment methods:
- Cash on Delivery (COD)
- Pay Maya
- G-Cash
- B.P.I (BPI)
- Go Tyme
- Others

## Validation Rules

1. **Order Creation:**
   - No card number required
   - Payment method must be one of the `PaymentChoice` options
   - Items must be specified

2. **Payment Processing:**
   - For COD: No card number required
   - For non-COD: 16-digit card number required
   - Amount must be at least the order total
   - Order number must be valid

## Benefits

- Separates order creation from payment processing
- Provides better security by not requiring card numbers upfront
- Supports multiple payment methods
- Clear validation rules based on payment type