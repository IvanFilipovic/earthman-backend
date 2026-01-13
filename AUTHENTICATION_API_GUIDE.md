# Authentication API Integration Guide

This guide explains how the frontend should integrate with the authentication endpoints to fix the reported issues.

## Issues and Solutions

### Issue 1: Token Not Stored After Login/Registration ❌
**Problem:** Frontend receives tokens but doesn't store them, causing `/api/customers/me/` to return 401.

**Solution:** Store tokens in localStorage after successful login/registration.

### Issue 2: Password Fields Not Hidden ❌
**Problem:** Password input fields show plain text.

**Solution:** Use `type="password"` on password input fields.

### Issue 3: No Button Disabled State ❌
**Problem:** Register button is always enabled even when fields are empty.

**Solution:** Add validation to disable button when required fields are empty.

### Issue 4: Inverted Checkbox Logic ❌
**Problem:** Privacy policy checkbox must be unchecked to register.

**Solution:** Require checkbox to be **checked** (agreed) to enable registration.

---

## API Endpoints

### 1. Registration Endpoint

**Endpoint:** `POST /api/customers/register/`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!",
  "password2": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe",
  "newsletter": false
}
```

**Success Response (201):**
```json
{
  "message": "Customer registered successfully",
  "customer": {
    "id": 1,
    "email": "user@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "newsletter": false,
    "is_active": true,
    "date_joined": "2026-01-13T10:30:00Z",
    "orders": []
  },
  "tokens": {
    "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
    "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
  }
}
```

**Frontend Implementation:**
```javascript
async function register(formData) {
  try {
    const response = await fetch('http://localhost:8000/api/customers/register/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(formData),
    });

    const data = await response.json();

    if (response.ok) {
      // ✅ STORE TOKENS - This is currently missing!
      localStorage.setItem('access_token', data.tokens.access);
      localStorage.setItem('refresh_token', data.tokens.refresh);

      // ✅ UPDATE USER STORE
      userStore.setUser(data.customer);
      userStore.setTokens(data.tokens);

      // Redirect to dashboard
      router.push('/dashboard');
    }
  } catch (error) {
    console.error('Registration failed:', error);
  }
}
```

---

### 2. Login Endpoint

**Endpoint:** `POST /api/customers/login/`

**Request Body:**
```json
{
  "email": "user@example.com",
  "password": "SecurePassword123!"
}
```

**Success Response (200):**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Frontend Implementation:**
```javascript
async function login(email, password) {
  try {
    const response = await fetch('http://localhost:8000/api/customers/login/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ email, password }),
    });

    const data = await response.json();

    if (response.ok) {
      // ✅ STORE TOKENS - This is currently missing!
      localStorage.setItem('access_token', data.access);
      localStorage.setItem('refresh_token', data.refresh);

      // ✅ FETCH USER DATA AND UPDATE STORE
      await fetchUserData();

      // Redirect to dashboard
      router.push('/dashboard');
    }
  } catch (error) {
    console.error('Login failed:', error);
  }
}
```

---

### 3. Get Current User Endpoint

**Endpoint:** `GET /api/customers/me/`

**Headers Required:**
```
Authorization: Bearer <access_token>
```

**Success Response (200):**
```json
{
  "id": 1,
  "email": "user@example.com",
  "first_name": "John",
  "last_name": "Doe",
  "newsletter": false,
  "is_active": true,
  "date_joined": "2026-01-13T10:30:00Z",
  "orders": [...]
}
```

**Error Response (401):**
```json
{
  "detail": "Authentication credentials were not provided."
}
```

**Frontend Implementation:**
```javascript
async function fetchUserData() {
  try {
    // ✅ GET TOKEN FROM STORAGE
    const accessToken = localStorage.getItem('access_token');

    if (!accessToken) {
      throw new Error('No access token found');
    }

    const response = await fetch('http://localhost:8000/api/customers/me/', {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
        // ✅ INCLUDE BEARER TOKEN - This is currently missing!
        'Authorization': `Bearer ${accessToken}`,
      },
    });

    if (response.status === 401) {
      // Token expired or invalid, try to refresh
      await refreshToken();
      return fetchUserData(); // Retry
    }

    const data = await response.json();

    if (response.ok) {
      // ✅ UPDATE USER STORE
      userStore.setUser(data);
    }
  } catch (error) {
    console.error('Failed to fetch user data:', error);
    // Clear tokens and redirect to login
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    router.push('/login');
  }
}
```

---

### 4. Refresh Token Endpoint

**Endpoint:** `POST /api/customers/token/refresh/`

**Request Body:**
```json
{
  "refresh": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Success Response (200):**
```json
{
  "access": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

**Frontend Implementation:**
```javascript
async function refreshToken() {
  try {
    const refreshToken = localStorage.getItem('refresh_token');

    if (!refreshToken) {
      throw new Error('No refresh token found');
    }

    const response = await fetch('http://localhost:8000/api/customers/token/refresh/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ refresh: refreshToken }),
    });

    const data = await response.json();

    if (response.ok) {
      // ✅ UPDATE ACCESS TOKEN
      localStorage.setItem('access_token', data.access);
    } else {
      // Refresh token expired, redirect to login
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      router.push('/login');
    }
  } catch (error) {
    console.error('Token refresh failed:', error);
  }
}
```

---

## Frontend Form Fixes

### Login Form

```jsx
// ❌ WRONG - Password visible
<input type="text" name="password" />

// ✅ CORRECT - Password hidden
<input type="password" name="password" />
```

### Registration Form

```jsx
function RegisterForm() {
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    password2: '',
    first_name: '',
    last_name: '',
    newsletter: false,
    agreedToTerms: false, // ✅ Add this
  });

  // ✅ VALIDATE FORM
  const isFormValid = () => {
    return (
      formData.email &&
      formData.password &&
      formData.password2 &&
      formData.password === formData.password2 &&
      formData.agreedToTerms // ✅ Must be checked
    );
  };

  return (
    <form onSubmit={handleSubmit}>
      <input
        type="email"
        name="email"
        value={formData.email}
        onChange={handleChange}
        required
      />

      {/* ✅ CORRECT - Password hidden */}
      <input
        type="password"
        name="password"
        value={formData.password}
        onChange={handleChange}
        required
      />

      {/* ✅ CORRECT - Confirm password hidden */}
      <input
        type="password"
        name="password2"
        value={formData.password2}
        onChange={handleChange}
        required
      />

      <input
        type="text"
        name="first_name"
        value={formData.first_name}
        onChange={handleChange}
      />

      <input
        type="text"
        name="last_name"
        value={formData.last_name}
        onChange={handleChange}
      />

      <label>
        <input
          type="checkbox"
          name="newsletter"
          checked={formData.newsletter}
          onChange={handleChange}
        />
        Subscribe to newsletter
      </label>

      {/* ✅ CORRECT - Must be checked to register */}
      <label>
        <input
          type="checkbox"
          name="agreedToTerms"
          checked={formData.agreedToTerms}
          onChange={handleChange}
          required
        />
        I have read and agree to the Privacy Policy and Terms & Conditions
      </label>

      {/* ✅ CORRECT - Button disabled when form invalid */}
      <button
        type="submit"
        disabled={!isFormValid()}
      >
        Register
      </button>
    </form>
  );
}
```

---

## Axios Interceptor (Recommended)

For better token management, use an Axios interceptor:

```javascript
import axios from 'axios';

const api = axios.create({
  baseURL: 'http://localhost:8000',
});

// Request interceptor - Add token to all requests
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response interceptor - Handle 401 errors
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const refreshToken = localStorage.getItem('refresh_token');
        const response = await axios.post(
          'http://localhost:8000/api/customers/token/refresh/',
          { refresh: refreshToken }
        );

        const { access } = response.data;
        localStorage.setItem('access_token', access);

        originalRequest.headers.Authorization = `Bearer ${access}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh failed, logout user
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);

export default api;
```

---

## Testing the Backend

You can test the backend endpoints using curl:

```bash
# Register a new user
curl -X POST http://localhost:8000/api/customers/register/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!",
    "password2": "TestPass123!",
    "first_name": "Test",
    "last_name": "User"
  }'

# Login
curl -X POST http://localhost:8000/api/customers/login/ \
  -H "Content-Type: application/json" \
  -d '{
    "email": "test@example.com",
    "password": "TestPass123!"
  }'

# Get current user (replace <TOKEN> with actual access token)
curl -X GET http://localhost:8000/api/customers/me/ \
  -H "Authorization: Bearer <TOKEN>"
```

---

## Summary of Required Frontend Changes

1. **✅ Store tokens** in localStorage after login/registration
2. **✅ Include Authorization header** in all authenticated requests
3. **✅ Use `type="password"`** for password input fields
4. **✅ Add form validation** to disable register button when fields empty
5. **✅ Fix checkbox logic** - require it to be checked (not unchecked)
6. **✅ Implement token refresh** logic to handle expired tokens
7. **✅ Update user store** with user data after successful authentication

The backend is working correctly. All issues are in the frontend implementation.
