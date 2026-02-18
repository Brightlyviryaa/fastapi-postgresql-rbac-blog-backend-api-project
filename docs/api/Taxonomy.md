# Taxonomy API

## Categories

### List Categories

**Method**: `GET`
**URL**: `/api/v1/categories/`

**Description**:
Retrieve all categories.

**Authentication**:
Requires a valid access token.

**Response Body** (JSON Array):

```json
[
  {
    "id": 1,
    "name": "Hardware",
    "slug": "hardware"
  },
  {
    "id": 2,
    "name": "Software",
    "slug": "software"
  }
]
```

#### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Middleware
    participant CRUD
    participant Database

    Client->>API: GET /categories/
    API->>Middleware: get_current_user(token)
    alt Token valid
        Middleware-->>API: User object
        API->>CRUD: get_multi()
        CRUD->>Database: Select all categories
        Database-->>CRUD: Category list
        CRUD-->>API: Category list
        API-->>Client: 200 OK (Category list)
    else Invalid Token
        Middleware-->>Client: 401/403 Error
    end
```

### Create Category

**Method**: `POST`
**URL**: `/api/v1/categories/`

**Description**:
Create a new category.

**Request Body** (JSON):

```json
{
  "name": "New Category"
}
```

**Response Body** (JSON):

```json
{
  "id": 3,
  "name": "New Category",
  "slug": "new-category"
}
```

#### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Middleware
    participant CRUD
    participant Database

    Client->>API: POST /categories/ (category_data)
    API->>Middleware: get_current_user(token)
    alt Token valid
        Middleware-->>API: User object
        API->>CRUD: get_by_slug(slug)
        CRUD->>Database: Select category by slug
        Database-->>CRUD: Category or None
        alt Slug exists
            CRUD-->>API: Category object
            API-->>Client: 400 Bad Request (Exists)
        else Slug unique
            CRUD-->>API: None
            API->>CRUD: create(category_data)
            CRUD->>Database: Insert category
            Database-->>CRUD: Created Category
            CRUD-->>API: Created Category
            API-->>Client: 200 OK (Created Category)
        end
    else Invalid Token
        Middleware-->>Client: 401/403 Error
    end
```

---

## Tags

### List Tags

**Method**: `GET`
**URL**: `/api/v1/tags/`

**Description**:
Retrieve all tags. Can be searched.

**Request Parameters**:

| Parameter | Type | Description | Default | Required |
| :--- | :--- | :--- | :--- | :--- |
| `search` | string | Search term for tag name | None | No |

**Authentication**:
Requires a valid access token.

**Response Body** (JSON Array):

```json
[
  {
    "id": 1,
    "name": "Tech",
    "slug": "tech"
  },
  {
    "id": 2,
    "name": "Philosophy",
    "slug": "philosophy"
  }
]
```

#### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Middleware
    participant CRUD
    participant Database

    Client->>API: GET /tags/ (search)
    API->>Middleware: get_current_user(token)
    alt Token valid
        Middleware-->>API: User object
        API->>CRUD: get_multi(search)
        CRUD->>Database: Select tags
        Database-->>CRUD: Tag list
        CRUD-->>API: Tag list
        API-->>Client: 200 OK (Tag list)
    else Invalid Token
        Middleware-->>Client: 401/403 Error
    end
```

### Create Tag

**Method**: `POST`
**URL**: `/api/v1/tags/`

**Description**:
Create a new tag.

**Request Body** (JSON):

```json
{
  "name": "New Tag"
}
```

**Response Body** (JSON):

```json
{
  "id": 3,
  "name": "New Tag",
  "slug": "new-tag"
}
```

#### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Middleware
    participant CRUD
    participant Database

    Client->>API: POST /tags/ (tag_data)
    API->>Middleware: get_current_user(token)
    alt Token valid
        Middleware-->>API: User object
        API->>CRUD: get_by_slug(slug)
        CRUD->>Database: Select tag by slug
        Database-->>CRUD: Tag or None
        alt Slug exists
            CRUD-->>API: Tag object
            API-->>Client: 400 Bad Request (Exists)
        else Slug unique
            CRUD-->>API: None
            API->>CRUD: create(tag_data)
            CRUD->>Database: Insert tag
            Database-->>CRUD: Created Tag
            CRUD-->>API: Created Tag
            API-->>Client: 200 OK (Created Tag)
        end
    else Invalid Token
        Middleware-->>Client: 401/403 Error
    end
```
