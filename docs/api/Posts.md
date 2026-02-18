# Posts API

## List Posts
`GET /api/v1/posts`

Retrieves a list of posts with pagination and filtering.

**Query Parameters:**
- `skip`: (int) Offset (default: 0)
- `limit`: (int) Limit (default: 10)
- `status`: (str) Filter by status (draft, published)
- `category_slug`: (str) Filter by category slug
- `tag_slug`: (str) Filter by tag slug
- `search`: (str) Search in title/content (full-text search)

**Response:**
```json
{
  "total": 142,
  "items": [
    {
      "id": 1,
      "title": "The Hallucination is the Feature",
      "slug": "the-hallucination-is-the-feature",
      "status": "published",
      "view_count": 1200,
      "reading_time": 12,
      "category": { "id": 1, "name": "AI & Ethics", "slug": "ai-ethics" },
      "author": { "id": 10, "full_name": "Jonathan Doe" },
      "created_at": "2026-02-18T10:00:00Z",
      "updated_at": "2026-02-18T10:00:00Z"
    }
  ]
}
```

## Get Post Detail
`GET /api/v1/posts/{slug}`

Retrieves a single post by slug, including full content and tags.

**Response:**
```json
{
  "id": 1,
  "title": "The Hallucination is the Feature",
  "slug": "the-hallucination-is-the-feature",
  "content": "<p>Content...</p>",
  "abstract": "Abstract text...",
  "pdf_url": null,
  "status": "published",
  "view_count": 1205,
  "reading_time": 12,
  "volume": "Vol. 24",
  "issue": "Jan 2026",
  "category": { "id": 1, "name": "AI & Ethics", "slug": "ai-ethics" },
  "tags": [
    { "id": 1, "name": "Tech", "slug": "tech" },
    { "id": 2, "name": "Philosophy", "slug": "philosophy" }
  ],
  "author": { "id": 10, "full_name": "Jonathan Doe", "avatar_url": "..." },
  "related_posts": [
    { "id": 5, "title": "Related Article", "slug": "related", "thumbnail_url": "..." }
  ],
  "created_at": "2026-02-18T10:00:00Z"
}
```

## Create Post
`POST /api/v1/posts`

Creates a new post. Requires `editor` role.

**Body:**
```json
{
  "title": "New Article",
  "slug": "new-article",
  "content": "...",
  "status": "draft",
  "category_id": 1,
  "tag_ids": [1, 2],
  "thumbnail_url": "https://...",
  "meta_title": "SEO Title",
  "meta_description": "SEO Description",
  "scheduled_at": "2026-02-20T10:00:00Z"
}
```

## Update Post
`PUT /api/v1/posts/{id}`

Updates an existing post.

**Body:** (Same as Create, all fields optional)

## Delete Post
`DELETE /api/v1/posts/{id}`

Soft deletes a post.

## Upload Media
`POST /api/v1/posts/upload-media`

Uploads an image or PDF. Returns the public URL.

**Form Data:**
- `file`: (File) - Image (jpg/png) or PDF.

**Response:**
```json
{
  "url": "https://cdn.sigmatechno.com/uploads/file.ext",
  "mime_type": "image/jpeg"
}
```
