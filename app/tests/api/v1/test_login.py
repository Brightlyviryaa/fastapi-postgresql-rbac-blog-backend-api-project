import pytest
from httpx import AsyncClient
from unittest.mock import MagicMock, patch
from app.api.v1.endpoints import auth

@pytest.mark.asyncio
async def test_login_access_token_success(client: AsyncClient):
    """
    Test successful login with valid credentials.
    """
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "test@example.com"
    mock_user.is_active = True

    with patch("app.crud.user.authenticate", return_value=mock_user) as mock_auth, \
         patch("app.crud.user.is_active", return_value=True) as mock_active:
        
        login_data = {"username": "test@example.com", "password": "password"}
        response = await client.post("/api/v1/login/access-token", data=login_data)
        
        assert response.status_code == 200
        content = response.json()
        assert "access_token" in content
        assert content["token_type"] == "bearer"
        
        mock_auth.assert_called_once()
        # Verify arguments passed to authenticate (basic check)
        args, kwargs = mock_auth.call_args
        assert kwargs["email"] == "test@example.com"
        assert kwargs["password"] == "password"


@pytest.mark.asyncio
async def test_login_access_token_incorrect_password(client: AsyncClient):
    """
    Test login with incorrect credentials.
    Should return 400 Bad Request.
    """
    with patch("app.crud.user.authenticate", return_value=None):
        login_data = {"username": "test@example.com", "password": "wrongpassword"}
        response = await client.post("/api/v1/login/access-token", data=login_data)
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_login_access_token_inactive_user(client: AsyncClient):
    """
    Test login with valid credentials but inactive user.
    Should return 400 Bad Request.
    """
    mock_user = MagicMock()
    mock_user.id = 1
    mock_user.email = "inactive@example.com"
    
    with patch("app.crud.user.authenticate", return_value=mock_user), \
         patch("app.crud.user.is_active", return_value=False):
        
        login_data = {"username": "inactive@example.com", "password": "password"}
        response = await client.post("/api/v1/login/access-token", data=login_data)
        
        assert response.status_code == 400
        assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_login_access_token_validation_error_missing_fields(client: AsyncClient):
    """
    Test login with missing required fields (abuse/error case).
    Should return 422 Unprocessable Entity.
    """
    # Missing password
    login_data = {"username": "test@example.com"}
    response = await client.post("/api/v1/login/access-token", data=login_data)
    assert response.status_code == 422
    
    # Missing username
    login_data = {"password": "password"}
    response = await client.post("/api/v1/login/access-token", data=login_data)
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_access_token_sql_injection_attempt(client: AsyncClient):
    """
    Test login with SQL injection inputs.
    The app should treat these as literal strings and fail authentication safely (400),
    not execute them or crash (500).
    """
    sql_injection_payload = "' OR '1'='1"
    
    with patch("app.crud.user.authenticate", return_value=None) as mock_auth:
        login_data = {"username": sql_injection_payload, "password": "password"}
        response = await client.post("/api/v1/login/access-token", data=login_data)
        
        # Should be a normal auth failure, NOT a server error
        assert response.status_code == 400
        
        # Verify the injection string was passed literally to CRUD
        mock_auth.assert_called_once()
        args, kwargs = mock_auth.call_args
        assert kwargs["email"] == sql_injection_payload


@pytest.mark.asyncio
async def test_login_access_token_large_payload(client: AsyncClient):
    """
    Test login with excessively large password (DoS attempt).
    The endpoint should reject it with a 400 before passlib processes it.
    """
    long_password = "a" * 2000  # Exceeds MAX_LOGIN_PASSWORD_LENGTH (1024)
    login_data = {"username": "test@example.com", "password": long_password}
    
    response = await client.post("/api/v1/login/access-token", data=login_data)
    # Should be a graceful 400, NOT a 500 server crash
    assert response.status_code == 400
    assert response.json()["detail"] == "Incorrect email or password"


@pytest.mark.asyncio
async def test_login_access_token_xss_in_username(client: AsyncClient):
    """
    Test login with XSS script in username field.
    Should be treated as a literal string and fail authentication safely.
    """
    xss_payload = "<script>alert('xss')</script>"
    
    with patch("app.crud.user.authenticate", return_value=None):
        login_data = {"username": xss_payload, "password": "password"}
        response = await client.post("/api/v1/login/access-token", data=login_data)
        
        assert response.status_code == 400
        # Verify the response doesn't reflect the script back unescaped
        assert "<script>" not in response.text


@pytest.mark.asyncio
async def test_login_access_token_empty_strings(client: AsyncClient):
    """
    Test login with empty username and password.
    Should fail validation or authentication without crashing.
    """
    with patch("app.crud.user.authenticate", return_value=None):
        login_data = {"username": "", "password": ""}
        response = await client.post("/api/v1/login/access-token", data=login_data)
        
        assert response.status_code in (400, 422)


@pytest.mark.asyncio
async def test_login_access_token_unicode_injection(client: AsyncClient):
    """
    Test login with unicode/null byte injection in credentials.
    Should not cause server errors.
    """
    with patch("app.crud.user.authenticate", return_value=None):
        login_data = {"username": "admin\x00@example.com", "password": "pass\x00word"}
        response = await client.post("/api/v1/login/access-token", data=login_data)
        
        assert response.status_code == 400


@pytest.mark.asyncio
async def test_login_access_token_response_does_not_leak_password(client: AsyncClient):
    """
    Test that error responses never echo back the submitted password.
    """
    sensitive_password = "MySuperSecretPassword123!"
    
    with patch("app.crud.user.authenticate", return_value=None):
        login_data = {"username": "test@example.com", "password": sensitive_password}
        response = await client.post("/api/v1/login/access-token", data=login_data)
        
        assert response.status_code == 400
        assert sensitive_password not in response.text
