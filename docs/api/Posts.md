# Posts API

## List Posts

**Method**: `GET`
**URL**: `/api/v1/posts/`

**Description**:
Retrieve posts. Can be filtered by status, category, or tags.

**Request Parameters**:

| Parameter | Type | Description | Default | Required |
| :--- | :--- | :--- | :--- | :--- |
| `skip` | integer | Number of records to skip | 0 | No |
| `limit` | integer | Max number of records to return | 100 | No |
| `status` | string | Filter by status ('draft', 'published') | None | No |
| `category_id` | integer | Filter by category ID | None | No |
| `tag_id` | integer | Filter by tag ID | None | No |
| `search` | string | Search term for title | None | No |

**Authentication**:
Requires a valid access token.

**Response Body** (JSON Array):

```json
[
  {
    "id": 1,
    "title": "Judul Postingan...",
    "slug": "judul-postingan",
    "status": "published",
    "visibility": "public",
    "created_at": "2023-10-27T10:00:00Z",
    "updated_at": "2023-10-27T12:00:00Z",
    "author": {
      "id": 1,
      "full_name": "Admin User"
    },
    "category": {
      "id": 1,
      "name": "Hardware",
      "slug": "hardware"
    },
    "tags": [
      {
        "id": 1,
        "name": "Tech",
        "slug": "tech"
      }
    ]
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

    Client->>API: GET /posts/ (filters)
    API->>Middleware: get_current_user(token)
    alt Token valid
        Middleware-->>API: User object
        API->>CRUD: get_multi(skip, limit, filters)
        CRUD->>Database: Select posts
        Database-->>CRUD: Post list
        CRUD-->>API: Post list
        API-->>Client: 200 OK (Post list)
    else Invalid Token
        Middleware-->>Client: 401/403 Error
    end
```

---

## Create Post

**Method**: `POST`
**URL**: `/api/v1/posts/`

**Description**:
Create a new post.

**Request Body** (JSON):

```json
{
  "title": "Judul Postingan...",
  "slug": "slug-postingan-otomatis",
  "content": "<p>Mulai menulis cerita Anda di sini...</p>",
  "status": "draft",
  "visibility": "public",
  "scheduled_at": "2023-11-01T09:00:00Z",
  "category_id": 1,
  "tag_ids": [1, 2],
  "thumbnail_url": "https://storage.googleapis.com/...",
  "meta_title": "Judul Postingan for SEO",
  "meta_description": "Deskripsi singkat...",
  "canonical_url": "https://...",
  "pdf_url": "https://storage.googleapis.com/..."
}
```

**Authentication**:
Requires a valid access token.

**Response Codes**:

- `200 OK`: Post created successfully.
- `400 Bad Request`: Slug already exists.

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Middleware
    participant CRUD
    participant Database

    Client->>API: POST /posts/ (post_data)
    API->>Middleware: get_current_user(token)
    alt Token valid
        Middleware-->>API: User object
        API->>CRUD: get_by_slug(slug)
        CRUD->>Database: Select post by slug
        Database-->>CRUD: Post or None
        alt Slug exists
            CRUD-->>API: Post object
            API-->>Client: 400 Bad Request (Slug exists)
        else Slug unique
            CRUD-->>API: None
            API->>CRUD: create(post_data)
            CRUD->>Database: Insert post
            Database-->>CRUD: Created Post
            CRUD-->>API: Created Post
            API-->>Client: 200 OK (Created Post)
        end
    else Invalid Token
        Middleware-->>Client: 401/403 Error
    end
```

---

## Get Post

**Method**: `GET`
**URL**: `/api/v1/posts/{id_or_slug}`

**Description**:
Get a single post details by ID or Slug.

**Response Body** (JSON):

```json
{
  "id": 1,
  "title": "Judul Postingan...",
  "slug": "judul-postingan-otomatis",
  "content": "<p>Content...</p>",
  "status": "draft",
  "visibility": "public",
  "scheduled_at": null,
  "thumbnail_url": null,
  "meta_title": "Judul",
  "meta_description": "Desc",
  "canonical_url": null,
  "pdf_url": null,
  "created_at": "2023-10-27T10:00:00Z",
  "updated_at": "2023-10-27T10:00:00Z",
  "author_id": 1,
  "category": {
      "id": 1,
      "name": "Hardware",
      "slug": "hardware"
  },
  "tags": [
      {
          "id": 1,
          "name": "Tech",
          "slug": "tech"
      }
  ]
}
```

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant CRUD
    participant Database

    Client->>API: GET /posts/{id_or_slug}
    API->>CRUD: get(id) or get_by_slug(slug)
    CRUD->>Database: Select post
    Database-->>CRUD: Post or None
    alt Post found
        CRUD-->>API: Post object
        API-->>Client: 200 OK (Post object)
    else Post not found
        CRUD-->>API: None
        API-->>Client: 404 Not Found
    end
```

---

## Update Post

**Method**: `PUT`
**URL**: `/api/v1/posts/{id}`

**Description**:
Update an existing post.

**Request Body** (JSON): SAME AS CREATE POST, but all fields optional.

**Authentication**:
Requires a valid access token. Author or Superuser only.

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Middleware
    participant CRUD
    participant Database

    Client->>API: PUT /posts/{id} (update_data)
    API->>Middleware: get_current_user(token)
    alt Token valid
        Middleware-->>API: User object
        API->>CRUD: get(id)
        CRUD->>Database: Select post
        Database-->>CRUD: Post or None
        alt Post found
             alt User is Author or Superuser
                API->>CRUD: update(post, update_data)
                CRUD->>Database: Update post
                Database-->>CRUD: Updated Post
                CRUD-->>API: Updated Post
                API-->>Client: 200 OK (Updated Post)
             else User not authorized
                API-->>Client: 403 Forbidden
             end
        else Post not found
             API-->>Client: 404 Not Found
        end
    else Invalid Token
        Middleware-->>Client: 401/403 Error
    end
```

---

## Delete Post

**Method**: `DELETE`
**URL**: `/api/v1/posts/{id}`

**Description**:
Delete a post.

**Authentication**:
Requires a valid access token. Author or Superuser only.

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Middleware
    participant CRUD
    participant Database

    Client->>API: DELETE /posts/{id}
    API->>Middleware: get_current_user(token)
    alt Token valid
        Middleware-->>API: User object
        API->>CRUD: get(id)
        CRUD->>Database: Select post
        Database-->>CRUD: Post or None
        alt Post found
             alt User is Author or Superuser
                API->>CRUD: remove(id)
                CRUD->>Database: Delete post
                Database-->>CRUD: Deleted Post
                CRUD-->>API: Deleted Post
                API-->>Client: 200 OK (Deleted Post)
             else User not authorized
                API-->>Client: 403 Forbidden
             end
        else Post not found
             API-->>Client: 404 Not Found
        end
    else Invalid Token
        Middleware-->>Client: 401/403 Error
    end
```

---

## Upload Media

**Method**: `POST`
**URL**: `/api/v1/posts/upload`

**Description**:
Upload a file (Image for thumbnail or PDF) to storage. Returns the public URL.

**Request Body** (Multipart/Form-Data):
- `file`: File binary.

**Response Body** (JSON):

```json
{
  "url": "https://storage.googleapis.com/bucket/filename.ext",
  "filename": "filename.ext",
  "content_type": "image/jpeg"
}
```

### Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Middleware
    participant Storage

    Client->>API: POST /posts/upload (file)
    API->>Middleware: get_current_user(token)
    alt Token valid
        Middleware-->>API: User object
        API->>Storage: Upload file
        Storage-->>API: File URL
        API-->>Client: 200 OK (File URL)
    else Invalid Token
        Middleware-->>Client: 401/403 Error
    end
```
