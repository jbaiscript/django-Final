# Comments CRUD Operations Documentation

## Overview
The Django application now includes a generic comment system that allows users to create comments on various models (products, orders, etc.) using Django's contenttypes framework.

## Important: Commenting Policy
**For Product Comments**: Users can only comment on products they have previously purchased. The system verifies purchase history before allowing a product comment.

## 1. Create Comment (POST)
To create a new comment, send a POST request to `/api/comments/`:

**Endpoint:** `POST /api/comments/`

**Required Headers:**
- `Authorization: Bearer <your_token>` (after logging in)

**Request Body:**
```json
{
  "text": "This is my comment",
  "content_type": "product",
  "object_id": 1,
  "parent": null
}
```

**Parameters:**
- `text`: The comment text (required)
- `content_type`: The model name the comment is associated with (e.g., "product", "order") - required
- `object_id`: The ID of the object being commented on (required)
- `parent`: ID of the parent comment if this is a reply (optional)

**Response:**
- On success: Returns the created comment object with status 201 Created
- On error: Returns error details with appropriate status code

**Response Example:**
```json
{
  "id": 1,
  "user": {
    "id": 2,
    "username": "john_doe",
    "email": "john@example.com",
    "first_name": "",
    "last_name": "",
    "role": "customer",
    "is_seller_approved": false,
    "date_joined": "2023-12-03T10:00:00Z"
  },
  "text": "This is my comment",
  "created_at": "2023-12-03T10:30:00Z",
  "updated_at": "2023-12-03T10:30:00Z",
  "parent": null,
  "replies": [],
  "content_type": 10,
  "object_id": 1
}
```

**Behavior:**
- Creates a new comment associated with the authenticated user
- The `user` field is automatically populated with the authenticated user
- For products: Verifies that the user has purchased the product before allowing the comment
- Links the comment to a specific object using content_type and object_id
- Allows for nested replies using the parent field

**Error Response (for product comments without purchase):**
```json
{
  "text": "You can only comment on products you have purchased.",
  "content_type": "product",
  "object_id": 1
}
```

## 2. Read Comments (GET)
To read comments, use the GET endpoint with optional query parameters:

**Endpoint:** `GET /api/comments/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Query Parameters (Optional):**
- `content_type`: Filter comments by model name (e.g., "product")
- `object_id`: Filter comments by object ID (e.g., 1)

**Response:**
- Returns an array of comments
- If content_type and object_id are provided: returns comments for that specific object
- If no parameters provided: returns all comments by the authenticated user

**Response Example:**
```json
[
  {
    "id": 1,
    "user": {
      "id": 2,
      "username": "john_doe",
      "email": "john@example.com",
      "first_name": "",
      "last_name": "",
      "role": "customer",
      "is_seller_approved": false,
      "date_joined": "2023-12-03T10:00:00Z"
    },
    "text": "This is my comment",
    "created_at": "2023-12-03T10:30:00Z",
    "updated_at": "2023-12-03T10:30:00Z",
    "parent": null,
    "replies": [
      {
        "id": 2,
        "user": {
          "id": 3,
          "username": "jane_smith",
          ...
        },
        "text": "This is a reply to the original comment",
        "created_at": "2023-12-03T10:35:00Z",
        "updated_at": "2023-12-03T10:35:00Z",
        "parent": 1,
        "replies": [],
        "content_type": 10,
        "object_id": 1
      }
    ],
    "content_type": 10,
    "object_id": 1
  }
]
```

## 3. Read Single Comment (GET)
To retrieve a specific comment:

**Endpoint:** `GET /api/comments/{pk}/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Parameters:**
- `pk`: Primary key (ID) of the comment to retrieve

**Response:**
- Returns a single comment object with status 200 OK
- Only returns comments created by the authenticated user

## 4. Update Comment (PUT/PATCH)
To update an existing comment:

**Endpoint:** `PUT /api/comments/{pk}/` or `PATCH /api/comments/{pk}/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Parameters:**
- `pk`: Primary key (ID) of the comment to update

**Request Body:**
```json
{
  "text": "Updated comment text"
}
```

**Response:**
- On success: Returns the updated comment object with status 200 OK
- On error: Returns error details with appropriate status code

**Behavior:**
- Only allows updates to comments created by the authenticated user
- The user field cannot be changed (it's read-only)
- PATCH allows partial updates (only certain fields)
- PUT requires all required fields to be provided

## 5. Delete Comment (DELETE)
To delete a comment:

**Endpoint:** `DELETE /api/comments/{pk}/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Parameters:**
- `pk`: Primary key (ID) of the comment to delete

**Response:**
- On success: Returns status 204 (No Content)
- On error: Returns error details with appropriate status code

**Behavior:**
- Only allows deletion of comments created by the authenticated user
- Permanently removes the comment and all its replies
- Returns 404 if the comment doesn't exist or wasn't created by the user

## Usage Examples

### Adding a comment to a product
```
POST /api/comments/
{
  "text": "This product looks great!",
  "content_type": "product",
  "object_id": 5
}
```

### Adding a reply to an existing comment
```
POST /api/comments/
{
  "text": "I agree with your comment",
  "content_type": "product",
  "object_id": 5,
  "parent": 1
}
```

### Getting all comments for a specific product
```
GET /api/comments/?content_type=product&object_id=5
```

### Getting all comments by the current user
```
GET /api/comments/
```