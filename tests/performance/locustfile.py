import random
from locust import HttpUser, task, between, tag

class SigmaTechnoUser(HttpUser):
    """
    Simulates user behavior for performance testing.
    Includes public read operations (cached) and admin operations (authenticated + cached).
    """
    # Wait between 1 and 3 seconds between tasks
    wait_time = between(1, 3)
    
    # Store token for admin tasks
    access_token = None

    def on_start(self):
        """Called when a User starts running."""
        # Simple probability: 20% of users are admins who log in
        if random.random() < 0.2:
            self.login()

    def login(self):
        """Authenticate as admin to get a token."""
        # Note: This assumes the default seed admin credentials
        # Ideally, use environment variables or a secure way to pass credentials
        response = self.client.post("/api/v1/login/access-token", data={
            "username": "admin@example.com",
            "password": "password"
        })
        if response.status_code == 200:
            self.access_token = response.json()["access_token"]

    @task(3)
    @tag('public', 'search')
    def search_posts(self):
        """High traffic public endpoint: Search."""
        queries = ["fastapi", "react", "python", "tutorial", "guide"]
        q = random.choice(queries)
        self.client.get(f"/api/v1/search?q={q}", name="/api/v1/search")

    @task(5)
    @tag('public', 'posts')
    def list_posts(self):
        """High traffic public endpoint: Post List."""
        # Test pagination caching
        page = random.randint(0, 5) * 10 
        self.client.get(f"/api/v1/posts?skip={page}&limit=10", name="/api/v1/posts")

    @task(2)
    @tag('public', 'taxonomy')
    def list_categories(self):
        """Low traffic public endpoint: Categories."""
        self.client.get("/api/v1/categories", name="/api/v1/categories")

    @task(1)
    @tag('admin', 'dashboard')
    def dashboard_stats(self):
        """Admin endpoint: Dashboard Stats."""
        if self.access_token:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            self.client.get("/api/v1/dashboard/stats", headers=headers, name="/api/v1/dashboard/stats")

    @task(2)
    @tag('admin', 'dashboard')
    def dashboard_posts(self):
        """Admin endpoint: Dashboard Posts Table."""
        if self.access_token:
            headers = {"Authorization": f"Bearer {self.access_token}"}
            self.client.get("/api/v1/dashboard/posts?limit=10", headers=headers, name="/api/v1/dashboard/posts")
