"""User Service - Example microservice for user management."""
from datetime import datetime
from typing import List, Optional
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr

# User model
class User(BaseModel):
    id: Optional[int] = None
    username: str
    email: EmailStr
    full_name: str
    disabled: bool = False
    created_at: Optional[datetime] = None


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    password: str


class UserUpdate(BaseModel):
    email: Optional[EmailStr] = None
    full_name: Optional[str] = None
    disabled: Optional[bool] = None


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: User


# Create FastAPI app
app = FastAPI(
    title="User Service",
    version="1.0.0",
    description="User management microservice",
)

# In-memory database (for demo purposes)
users_db = {
    1: User(
        id=1,
        username="admin",
        email="admin@example.com",
        full_name="Admin User",
        created_at=datetime.utcnow(),
    ),
    2: User(
        id=2,
        username="john_doe",
        email="john@example.com",
        full_name="John Doe",
        created_at=datetime.utcnow(),
    ),
}

next_user_id = 3


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "user-service"}


@app.post("/api/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    """Login endpoint."""
    # Mock authentication
    user = next((u for u in users_db.values() if u.username == request.username), None)

    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    # Mock JWT token (in real implementation, use actual JWT)
    token = f"mock_token_{user.username}"

    return LoginResponse(
        access_token=token,
        user=user,
    )


@app.post("/api/auth/register", response_model=User)
async def register(user_data: UserCreate):
    """Register a new user."""
    global next_user_id

    # Check if username exists
    if any(u.username == user_data.username for u in users_db.values()):
        raise HTTPException(status_code=400, detail="Username already exists")

    # Create new user
    new_user = User(
        id=next_user_id,
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        created_at=datetime.utcnow(),
    )

    users_db[next_user_id] = new_user
    next_user_id += 1

    return new_user


@app.get("/api/users", response_model=List[User])
async def list_users():
    """List all users."""
    return list(users_db.values())


@app.get("/api/users/{user_id}", response_model=User)
async def get_user(user_id: int):
    """Get user by ID."""
    user = users_db.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return user


@app.post("/api/users", response_model=User)
async def create_user(user_data: UserCreate):
    """Create a new user."""
    global next_user_id

    # Check if username exists
    if any(u.username == user_data.username for u in users_db.values()):
        raise HTTPException(status_code=400, detail="Username already exists")

    new_user = User(
        id=next_user_id,
        username=user_data.username,
        email=user_data.email,
        full_name=user_data.full_name,
        created_at=datetime.utcnow(),
    )

    users_db[next_user_id] = new_user
    next_user_id += 1

    return new_user


@app.put("/api/users/{user_id}", response_model=User)
async def update_user(user_id: int, user_data: UserUpdate):
    """Update a user."""
    user = users_db.get(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user_data.email is not None:
        user.email = user_data.email
    if user_data.full_name is not None:
        user.full_name = user_data.full_name
    if user_data.disabled is not None:
        user.disabled = user_data.disabled

    return user


@app.delete("/api/users/{user_id}")
async def delete_user(user_id: int):
    """Delete a user."""
    if user_id not in users_db:
        raise HTTPException(status_code=404, detail="User not found")

    del users_db[user_id]

    return {"message": "User deleted successfully"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
