# ADR 006: Authentication and Role-Based Access Control (RBAC)

## Status
Accepted

## Context
HospitalOps AI requires a secure authentication and authorization mechanism. Future modules (such as forecasting, operational dashboard, alerts) will expose sensitive hospital operational data. We need:
1. Secure identity verification (login, session management).
2. Protection against brute-force attacks.
3. Secure refresh token handling (to minimize long-lived secrets in browser storage).
4. Granular permissions decoupled from high-level roles.

## Decisions

### 1. Password Hashing
We chose **Argon2id** (via `passlib` and `argon2-cffi`) as the password hashing algorithm. It provides resistance against both GPU-based brute-force attacks and side-channel timing attacks, making it the current recommended standard over bcrypt.

### 2. Token Architecture
- **Access Token:** Short-lived JWT (e.g., 15 minutes) returned in the JSON response payload. The frontend keeps this in memory (not in `localStorage`) and attaches it as a `Bearer` token to API requests. This mitigates XSS risks for the access token.
- **Refresh Token:** Long-lived opaque string (e.g., 7 days) stored in a secure, `HttpOnly`, `SameSite=lax` cookie. The backend uses this cookie to rotate tokens via the `/api/v1/auth/refresh` endpoint. This mitigates both XSS (since JS cannot read `HttpOnly` cookies) and CSRF (since `SameSite` prevents cross-origin requests from automatically attaching the cookie in dangerous contexts, and refresh is an explicit backend API call).

### 3. Session Management
Refresh sessions are stateful and tracked in **Redis** (`hospitalops:auth:session:<refresh_token>`). This provides the ability to instantly revoke a user's session (e.g., on logout or admin intervention) without waiting for the token to expire.

### 4. Role-Based Access Control (RBAC)
We implemented a **Centralized Permissions Matrix**. 
Instead of hardcoding role checks in every endpoint (`require_role(ADMIN)`), endpoints should ideally rely on `require_permission("beds.manage")`.
The `Role` enum (e.g., `ADMIN`, `DOCTOR`, `OPERATIONS_MANAGER`) maps to a list of granular string permissions in `app/core/security.py`. This decouples the authorization logic in the API layer from the organizational role definitions, allowing us to modify role capabilities centrally.

### 5. Rate Limiting
A simple Redis-backed rate limiter (`hospitalops:auth:rate:<email>`) is implemented on the `/login` endpoint to mitigate credential stuffing and brute-force attacks.

## Consequences
- **Positive:** Highly secure token lifecycle protecting against XSS/CSRF. Immediate session revocation via Redis. Granular decoupled permissions allow flexible future expansion.
- **Negative:** Requires Redis to be available for authentication to function (creates a hard dependency). Requires the frontend to manage token refresh logic (intercepting 401s, calling `/refresh`, and retrying requests).
