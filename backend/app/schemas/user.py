from pydantic import BaseModel, EmailStr


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    full_name: str
    password: str


class UserResponse(BaseModel):
    id: int
    email: EmailStr
    full_name: str

class Token(BaseModel):
    access_token: str
    token_type: str


    model_config = {"from_attributes": True}