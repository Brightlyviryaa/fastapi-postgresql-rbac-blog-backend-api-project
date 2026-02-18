import asyncio
import httpx

async def smoke_test():
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8000") as client:
        # 1. Login to get token
        login_data = {
            "username": "admin@example.com",
            "password": "password"
        }
        print("Attempting login...")
        response = await client.post("/api/v1/login/access-token", data=login_data)
        if response.status_code != 200:
            print(f"Login failed: {response.text}")
            return
        
        token = response.json()["access_token"]
        print("Login successful, token obtained.")
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # 2. Get current user
        print("Fetching current user...")
        response = await client.get("/api/v1/users/me", headers=headers)
        if response.status_code != 200:
            print(f"Get me failed: {response.text}")
            return
        user_data = response.json()
        print(f"Current user: {user_data['email']} (Superuser: {user_data['is_superuser']})")
        
        # 3. List users (admin only)
        print("Listing users...")
        response = await client.get("/api/v1/users/", headers=headers)
        if response.status_code != 200:
            print(f"List users failed: {response.text}")
            return
        users = response.json()
        print(f"Found {len(users)} users.")
        
        print("Smoke test PASSED!")

if __name__ == "__main__":
    # Note: Server must be running for this test. 
    # Since we can't easily start and stop server in background within this script cleanly without complex logic,
    # This script assumes server is running.
    print("This script requires the server to be running on port 8000.")
    print("Run `uvicorn app.main:app --reload` in another terminal, then run this script.")
    asyncio.run(smoke_test())
