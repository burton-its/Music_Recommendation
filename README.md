# Music Recommendation App (Integrated Auth)

## Overview
This is a Flask music recommendation app that delegates authentication to microservices:
- Auth service (`/auth/register`, `/auth/login`)
- Validator service (`/validate-token`)
- Logout service (`/revoke`)

## Requirements
- Python 3.10+
- MySQL



## Environment Variables
`config.py` reads:

```
MYSQL_HOST=localhost
MYSQL_USER=root
MYSQL_PASSWORD=
MYSQL_DB=musicapp
SECRET_KEY=your_flask_secret

AUTH_SERVICE_URL=http://localhost:8000
VALIDATOR_SERVICE_URL=http://localhost:9000
LOGOUT_SERVICE_URL=http://localhost:5001
ACCESS_TOKEN_EXPIRE_SECONDS=900
```

## Running the App

Run services first:
1. Auth service (default port `8000`)
2. Logout service (default port `5001`)
3. Validator service (default port `9000`)
4. Main app

Important: `JWT_SECRET` and `JWT_ALG` must match across Auth, Validator, and Logout.

```
python app.py
```


## Routes
- `GET /` or `GET /login`: Show login form
- `POST /login`: Authenticate via Auth and validate token via Validator
- `GET /logout`: Revoke token via Logout and clear local session
- `GET /register`: Show registration form
- `POST /register`: Create user via Auth service
