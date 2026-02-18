# Auth API

## Login Access Token

**Method**: `POST`
**URL**: `/api/v1/login/access-token`

**Description**:
OAuth2 compatible token login, get an access token for future requests.

**Request Body** (`application/x-www-form-urlencoded`):

| Field | Type | Description | Required |
| :--- | :--- | :--- | :--- |
| `username` | string | User's email | Yes |
| `password` | string | User's password | Yes |

**Response Codes**:

- `200 OK`: Successful login.
- `400 Bad Request`: Incorrect email or password, or inactive user.

**Response Body** (JSON):

```json
{
  "access_token": "string",
  "token_type": "bearer"
}
```

## Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant CRUD
    participant Database

    Client->>API: POST /login/access-token (username, password)
    API->>CRUD: authenticate(email, password)
    CRUD->>Database: get_by_email(email)
    Database-->>CRUD: User object or None
    alt User exists
        CRUD->>CRUD: verify_password(password, hashed_password)
        alt Password correct
            CRUD-->>API: User object
            API->>API: create_access_token(user.id)
            API-->>Client: 200 OK (access_token)
        else Password incorrect
            CRUD-->>API: None
            API-->>Client: 400 Bad Request
        end
    else User does not exist
        CRUD-->>API: None
        API-->>Client: 400 Bad Request
    end
```
