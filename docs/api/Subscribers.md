# Newsletter Subscribers API

## Subscribe
`POST /api/v1/subscribers`

Subscribes an email to the newsletter.

**Body:**
```json
{
  "email": "user@example.com"
}
```

**Response:**
```json
{ "message": "Successfully subscribed." }
```

## Unsubscribe
`DELETE /api/v1/subscribers/{email}`

Unsubscribes an email.

## Sequence Diagrams

### Subscribe

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant CRUD
    participant Database

    Client->>API: POST /subscribers (email)
    API->>CRUD: get_by_email(email)
    alt Email exists
        CRUD-->>API: Subscriber
        API-->>Client: 200 OK (Already subscribed)
    else New Email
        CRUD-->>API: None
        API->>CRUD: create(email)
        CRUD->>Database: Insert Subscriber
        Database-->>CRUD: Created Subscriber
        CRUD-->>API: Created Subscriber
        API-->>Client: 200 OK (Subscribed)
    end
```
