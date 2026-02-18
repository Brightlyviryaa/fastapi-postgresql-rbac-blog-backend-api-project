import requests
import time
import json

API_URL = "http://localhost:8000/api/v1"

# 1. Login to get token
def get_token():
    try:
        resp = requests.post(f"{API_URL}/login/access-token", data={
            "username": "admin@example.com",
            "password": "password" # Default from initial_data.py
        })
        if resp.status_code != 200:
            print(f"Login failed: {resp.text}")
            return None
        return resp.json()["access_token"]
    except Exception as e:
        print(f"Connection failed: {e}")
        return None

# 2. Create Post
def create_post(token, title, content, slug, category_id=1):
    headers = {"Authorization": f"Bearer {token}"}
    data = {
        "title": title,
        "slug": slug,
        "content": content,
        "status": "published",
        "category_id": category_id,
        "meta_description": f"About {title}"
    }
    resp = requests.post(f"{API_URL}/posts", json=data, headers=headers)
    if resp.status_code == 200:
        print(f"Created post: {title}")
        return resp.json()
    else:
        print(f"Failed to create post {title}: {resp.text}")
        return None

# 3. Search
def search(query):
    print(f"\nSearching for '{query}'...")
    resp = requests.get(f"{API_URL}/search", params={"q": query, "sort": "relevance", "limit": 5})
    if resp.status_code == 200:
        data = resp.json()
        print(f"Found {data['total']} results:")
        for item in data['items']:
            print(f" - {item['title']} (Slug: {item['slug']})")
    else:
        print(f"Search failed: {resp.text}")

# 4. Related
def check_related(slug):
    print(f"\nChecking related posts for {slug}...")
    resp = requests.get(f"{API_URL}/posts/{slug}/related", params={"limit": 5})
    if resp.status_code == 200:
        data = resp.json()
        print(f"Found {data['total']} related posts:")
        for item in data['items']:
            print(f" - {item['title']}")
    else:
        print(f"Related check failed: {resp.text}")

def main():
    print("Waiting for API to be ready...")
    time.sleep(5) 
    
    token = get_token()
    if not token:
        print("Cannot proceed without token.")
        return

    # Create dummy posts
    # We assume category 1 exists (from initial data seeding? No, initial data only creates users/roles)
    # Actually initial_seed doesn't create categories. We might need to create one.
    # But let's try creating category first.
    
    # Create Category
    headers = {"Authorization": f"Bearer {token}"}
    cat_resp = requests.post(f"{API_URL}/categories", json={"name": "General", "slug": "general"}, headers=headers)
    cat_id = 1
    if cat_resp.status_code == 200:
        cat_id = cat_resp.json()["id"]
    elif cat_resp.status_code == 400 and "already exists" in cat_resp.text:
         # Try to get it? Or assume ID 1
         pass

    p1 = create_post(token, "Python for Beginners", "Learn Python programming language features.", "python-beginners", cat_id)
    p2 = create_post(token, "Advanced React Hooks", "Deep dive into React hooks and functionality.", "react-hooks", cat_id)
    p3 = create_post(token, "Delicious Chicken Curry", "How to cook spicy chicken curry with rice.", "chicken-curry", cat_id)

    # Allow some time? Voyage API is fast but async? No, crud is sync-await.
    time.sleep(2)

    # Search
    search("programming code") # Should find Python/React
    search("cooking food")     # Should find Chicken Curry

    # Related
    # We use hardcoded slugs if p1 is None (creation failed)
    target_slug = p1["slug"] if p1 else "python-beginners"
    check_related(target_slug)

if __name__ == "__main__":
    main()
