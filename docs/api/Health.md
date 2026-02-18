# Health API

## Health Check

**Method**: `GET`
**URL**: `/api/v1/health/`

**Description**:
Check if the service is up and the database is accessible.

**Response Codes**:

- `200 OK`: Service is healthy.

**Response Body** (JSON):

```json
{
  "status": "ok"
}
```

If the health check fails, it might return:

```json
{
  "status": "error"
}
```

## Sequence Diagram

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant Database

    Client->>API: GET /health/
    API->>Database: Execute "SELECT 1"
    alt Database Accessible
        Database-->>API: Success
        API-->>Client: 200 OK (status: ok)
    else Database Error
        Database-->>API: Exception
        API-->>Client: 200 OK (status: error)
    end
```
