# Users API

## List Users

**Method**: `GET`
**URL**: `/api/v1/users/`

**Description**:
Retrieve users. Only superusers can list all users.

**Request Parameters**:

| Parameter | Type | Description | Default | Required |
| :--- | :--- | :--- | :--- | :--- |
| `skip` | integer | Number of records to skip | 0 | No |
| `limit` | integer | Max number of records to return | 100 | No |

**Authentication**:
Requires a valid access token from a superuser.

**Response Body** (JSON Array):

```json
[
  {
    "email": "user@example.com",
    "is_active": true,
    "is_superuser": false,
    "full_name": "John Doe",
    "role_id": 1,
    "id": 1,
    "role": {
       "id": 1,
       "name": "user",
       "description": "Regular user"
    }
  }
]
```

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Middleware
    participant CRUD
    participant Database

    Client->>API: GET /users/ (token)
    API->>Middleware: get_current_active_superuser(token)
    alt Token valid & Superuser
        Middleware-->>API: User object
        API->>CRUD: get_multi(skip, limit)
        CRUD->>Database: Select users
        Database-->>CRUD: User list
        CRUD-->>API: User list
        API-->>Client: 200 OK (User list)
    else Invalid Token or Not Superuser
        Middleware-->>Client: 401/403 Error
    end
```

---

## Create User

**Method**: `POST`
**URL**: `/api/v1/users/`

**Description**:
Create new user. Only superusers can create new users.

**Request Body** (JSON):

```json
{
  "email": "user@example.com",
  "password": "strongpassword",
  "is_active": true,
  "is_superuser": false,
  "full_name": "John Doe",
  "role_id": 1
}
```

**Authentication**:
Requires a valid access token from a superuser.

**Response Codes**:

- `200 OK`: User created successfully.
- `400 Bad Request`: User with this email already exists.

**Response Body** (JSON):

```json
{
  "email": "user@example.com",
  "is_active": true,
  "is_superuser": false,
  "full_name": "John Doe",
  "role_id": 1,
  "id": 1,
    "role": {
       "id": 1,
       "name": "user",
       "description": "Regular user"
    }
}
```

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Middleware
    participant CRUD
    participant Database

    Client->>API: POST /users/ (token, user_data)
    API->>Middleware: get_current_active_superuser(token)
    alt Token valid & Superuser
        Middleware-->>API: User object
        API->>CRUD: get_by_email(email)
        CRUD->>Database: Select user by email
        Database-->>CRUD: User or None
        alt User exists
            CRUD-->>API: User object
            API-->>Client: 400 Bad Request (Exists)
        else User does not exist
            CRUD-->>API: None
            API->>CRUD: create(user_data)
            CRUD->>Database: Insert user
            Database-->>CRUD: Created User
            CRUD-->>API: Created User
            API-->>Client: 200 OK (Created User)
        end
    else Invalid Token or Not Superuser
        Middleware-->>Client: 401/403 Error
    end
```

---

## Get Current User

**Method**: `GET`
**URL**: `/api/v1/users/me`

**Description**:
Get current user.

**Authentication**:
Requires a valid access token.

**Response Body** (JSON):

```json
{
  "email": "user@example.com",
  "is_active": true,
  "is_superuser": false,
  "full_name": "John Doe",
  "role_id": 1,
  "id": 1,
    "role": {
       "id": 1,
       "name": "user",
       "description": "Regular user"
    }
}
```

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Middleware

    Client->>API: GET /users/me (token)
    API->>Middleware: get_current_active_user(token)
    alt Token valid
        Middleware-->>API: User object
        API-->>Client: 200 OK (User object)
    else Invalid Token
        Middleware-->>Client: 401/403 Error
    end
```
