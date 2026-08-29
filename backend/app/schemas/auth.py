from pydantic import BaseModel, ConfigDict, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    email: str
    full_name: str
    organization_id: str | None = None
    # Not on the User model itself -- resolved by the auth router from
    # organization_id so the frontend can brand the shell with the logged-in
    # user's own organization instead of a hardcoded firm name (Ground
    # Intelligence is multi-tenant; PIGL is one organization among others).
    organization_name: str | None = None
