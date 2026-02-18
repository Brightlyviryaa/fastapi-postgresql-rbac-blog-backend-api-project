# Entity Relationship Diagram (ERD)

## Auth & CMS Module

The following ERD describes the data model for the application, covering Authentication (RBAC, JWT) and the CMS content module.

```mermaid
erDiagram
    Role ||--o{ User : assigned_to
    User ||--o{ Post : writes
    User ||--o{ RefreshToken : has
    User ||--o{ Comment : writes
    Post ||--o{ Comment : has
    Post }o--|| Category : belongs_to
    Post }o--o{ Tag : has

    Role {
        int id PK
        string name UK "admin, editor, author, user"
        string description
        string permissions "JSON/Text list of scopes"
        datetime created_at
        datetime updated_at
    }

    User {
        int id PK
        string email UK
        string full_name
        string hashed_password
        boolean is_active
        boolean is_superuser
        int role_id FK
        datetime created_at
        datetime updated_at
    }

    RefreshToken {
        int id PK
        int user_id FK
        string token UK
        string device_info "User Agent / IP"
        datetime expires_at
        datetime created_at
        datetime revoked_at
    }

    Post {
        int id PK
        string title
        string slug UK
        text content "Optional if PDF is present"
        string status "draft, published"
        string visibility "public, private"
        datetime scheduled_at
        string thumbnail_url
        string meta_title
        string meta_description
        string canonical_url
        string pdf_url "Optional if Content is present"
        int author_id FK
        int category_id FK
        vector embedding "Vector(1536)"
        int view_count "Analytics"
        int reading_time "In minutes"
        text abstract "Short summary/intro"
        string volume "For Journal e.g. Vol. 24"
        string issue "For Journal e.g. Jan 2026"
        datetime deleted_at "Soft Delete"
        datetime created_at
        datetime updated_at
    }

    Comment {
        int id PK
        int post_id FK
        int user_id FK
        text content
        boolean is_approved "For moderation"
        datetime created_at
        datetime updated_at
    }

    Subscriber {
        int id PK
        string email UK
        boolean is_active
        datetime created_at
    }

    Category {
        int id PK
        string name
        string slug UK
        datetime created_at
        datetime updated_at
    }

    Tag {
        int id PK
        string name
        string slug UK
        datetime created_at
        datetime updated_at
    }
```

## Entity Details

### Role (RBAC)
Defines the access level and permissions for a user.
- **name**: Unique identifier for the role (e.g., 'admin', 'editor').
- **permissions**: List of allowed scopes/actions for this role.

### User
Represents a registered user in the system.
- **role_id**: Links to the `Role` table.
- **is_superuser**: boolean to bypass RBAC checks (God mode).
- **hashed_password**: Bcrypt/Argon2 hash of the password.

### RefreshToken (JWT Security)
Used to obtain new Access Tokens without re-entering credentials.
- **token**: The actual refresh token string (can be hashed).
- **expires_at**: When this token becomes invalid.
- **revoked_at**: Timestamp if the token was manually revoked (logout/security event).
- **device_info**: Optional metadata about where the token was generated.

### Post (Content)
Represents a blog post or article.
- **deleted_at**: **(Soft Delete)** If not null, the post is considered deleted (In Trash).
- **status**: Can be 'draft' or 'published'.
- **visibility**: Can be 'public' or 'private'.
- **author_id**: Links to the `User` who created the post. Ensure only the author (or Admin) can edit/delete this.

### Category & Tag
Taxonomy for organizing content.
- **slug**: URL-friendly identifier.
