from pydantic import BaseModel, EmailStr


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UnifiedLogin(BaseModel):
    email: EmailStr
    password: str


class GoogleLogin(BaseModel):
    id_token: str


class AdminLogin(BaseModel):
    email: EmailStr
    password: str


class ForgotPassword(BaseModel):
    email: EmailStr


class ChangePassword(BaseModel):
    old_password: str
    new_password: str
    confirm_password: str


class ResetPassword(BaseModel):
    token: str
    new_password: str
    confirm_password: str


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class AppleLogin(BaseModel):
    id_token: str
    email: str | None = None
    name: str | None = None

