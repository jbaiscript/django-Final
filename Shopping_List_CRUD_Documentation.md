# Shopping List CRUD Operations Documentation

## 1. Create Shopping List (POST)
To create a new shopping list, send a POST request to `/api/auth/shopping-lists/`:

**Endpoint:** `POST /api/auth/shopping-lists/`

**Required Headers:**
- `Authorization: Bearer <your_token>` (after logging in)

**Request Body:**
```json
{
  "name": "My Shopping List"
}
```

**Parameters:**
- `name`: The name for the new shopping list (required)

**Response:**
- On success: Returns the created shopping list object with status 201 Created
- On error: Returns error details with appropriate status code

**Response Example:**
```json
{
  "id": 1,
  "name": "My Shopping List",
  "user": 2,
  "created_at": "2023-12-03T10:30:00Z",
  "updated_at": "2023-12-03T10:30:00Z"
}
```

**Behavior:**
- Creates a new shopping list associated with the authenticated user
- The user field is automatically populated with the authenticated user
- Shopping list names must be unique per user

## 2. Read Shopping Lists (GET)
There are two ways to read shopping lists in the system:

**Endpoint 1: List all user's shopping lists**
`GET /api/auth/shopping-lists/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Response:**
- Returns an array of all shopping lists belonging to the authenticated user

**Response Example:**
```json
[
  {
    "id": 1,
    "name": "My Shopping List",
    "user": 2,
    "created_at": "2023-12-03T10:30:00Z",
    "updated_at": "2023-12-03T10:30:00Z"
  },
  {
    "id": 2,
    "name": "Weekly Groceries",
    "user": 2,
    "created_at": "2023-12-02T15:45:00Z",
    "updated_at": "2023-12-02T15:45:00Z"
  }
]
```

**Endpoint 2: Get specific shopping list details (with items)**
`GET /api/auth/shopping-lists/{pk}/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Parameters:**
- `pk`: Primary key (ID) of the specific shopping list to retrieve

**Response:**
- Returns details of the specific shopping list including all its items

**Response Example:**
```json
{
  "id": 1,
  "name": "My Shopping List",
  "user": 2,
  "created_at": "2023-12-03T10:30:00Z",
  "updated_at": "2023-12-03T10:30:00Z",
  "items": [
    {
      "id": 1,
      "shopping_list": 1,
      "product_id": 5,
      "product_name": "Apple",
      "product_price": 2.99,
      "quantity": 3,
      "added_at": "2023-12-03T11:00:00Z"
    }
  ]
}
```

**Behavior:**
- Only returns shopping lists that belong to the authenticated user
- Returns 404 if the shopping list doesn't exist or doesn't belong to the user

## 3. Update Shopping List (PUT/PATCH)
To update an existing shopping list, send a PUT or PATCH request to the following endpoint:

**Endpoint:** `PUT /api/auth/shopping-lists/{pk}/` or `PATCH /api/auth/shopping-lists/{pk}/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Parameters:**
- `pk`: Primary key (ID) of the shopping list to update

**Request Body (for PUT):**
```json
{
  "name": "Updated Shopping List Name"
}
```

**Request Body (for PATCH):**
```json
{
  "name": "Updated Shopping List Name"
}
```

**Response:**
- On success: Returns the updated shopping list object with status 200 OK
- On error: Returns error details with appropriate status code

**Response Example:**
```json
{
  "id": 1,
  "name": "Updated Shopping List Name",
  "user": 2,
  "created_at": "2023-12-03T10:30:00Z",
  "updated_at": "2023-12-03T12:15:00Z"
}
```

**Behavior:**
- Only allows updates to shopping lists that belong to the authenticated user
- The user field cannot be changed (it's read-only)
- PATCH allows partial updates (only certain fields)
- PUT requires all required fields to be provided

## 4. Delete Shopping List (DELETE)
To delete a shopping list, send a DELETE request to the following endpoint:

**Endpoint:** `DELETE /api/auth/shopping-lists/{pk}/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Parameters:**
- `pk`: Primary key (ID) of the shopping list to delete

**Response:**
- On success: Returns status 204 (No Content)
- On error: Returns error details with appropriate status code

**Behavior:**
- Only allows deletion of shopping lists that belong to the authenticated user
- Permanently removes the shopping list and all its associated items
- Returns 404 if the shopping list doesn't exist or doesn't belong to the user

## 5. Shopping List Items Operations
Shopping list items have their own set of CRUD operations that are associated with a specific shopping list.

### 5.1 Create Shopping List Item (POST)
To add an item to a shopping list, send a POST request:

**Endpoint:** `POST /api/auth/shopping-lists/{shopping_list_id}/items/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Parameters:**
- `shopping_list_id`: ID of the shopping list to add the item to

**Request Body:**
```json
{
  "product_id": 5,
  "quantity": 3
}
```

**Parameters:**
- `product_id`: ID of the product to add to the shopping list (required)
- `quantity`: Number of items (optional, defaults to 1)

**Response:**
- On success: Returns the created shopping list item with status 201 Created
- On error: Returns error details with appropriate status code

**Response Example:**
```json
{
  "id": 1,
  "shopping_list": 1,
  "product_id": 5,
  "product_name": "Apple",
  "product_price": 2.99,
  "quantity": 3,
  "added_at": "2023-12-03T11:00:00Z"
}
```

### 5.2 Read Shopping List Items (GET)
To get all items in a specific shopping list:

**Endpoint:** `GET /api/auth/shopping-lists/{shopping_list_id}/items/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Parameters:**
- `shopping_list_id`: ID of the shopping list whose items to retrieve

**Response:**
- Returns an array of all items in the specified shopping list

**Response Example:**
```json
[
  {
    "id": 1,
    "shopping_list": 1,
    "product_id": 5,
    "product_name": "Apple",
    "product_price": 2.99,
    "quantity": 3,
    "added_at": "2023-12-03T11:00:00Z"
  },
  {
    "id": 2,
    "shopping_list": 1,
    "product_id": 12,
    "product_name": "Bread",
    "product_price": 3.49,
    "quantity": 1,
    "added_at": "2023-12-03T11:15:00Z"
  }
]
```

### 5.3 Update Shopping List Item (PUT/PATCH)
To update an existing shopping list item:

**Endpoint:** `PUT /api/auth/shopping-lists/{shopping_list_id}/items/{pk}/` or `PATCH /api/auth/shopping-lists/{shopping_list_id}/items/{pk}/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Parameters:**
- `shopping_list_id`: ID of the shopping list
- `pk`: Primary key (ID) of the shopping list item to update

**Request Body:**
```json
{
  "quantity": 5
}
```

**Response:**
- On success: Returns the updated shopping list item with status 200 OK
- On error: Returns error details with appropriate status code

### 5.4 Delete Shopping List Item (DELETE)
To remove an item from a shopping list:

**Endpoint:** `DELETE /api/auth/shopping-lists/{shopping_list_id}/items/{pk}/`

**Required Headers:**
- `Authorization: Bearer <your_token>`

**Parameters:**
- `shopping_list_id`: ID of the shopping list
- `pk`: Primary key (ID) of the shopping list item to delete

**Response:**
- On success: Returns status 204 (No Content)
- On error: Returns error details with appropriate status code

**Behavior:**
- Only allows operations on shopping lists that belong to the authenticated user
- Product information (name and price) is retrieved dynamically from the products database