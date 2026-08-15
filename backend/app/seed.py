"""
Seeds the six approved MVP roles (Implementation Design Rev 2 §E.1), the
permission codes actually enforced by Phase-1 code, a default
RolePermission matrix, and one bootstrap ADMINISTRATOR account so the
platform is usable immediately after migration.

Only permissions Phase 1 code actually checks are seeded here (project.create,
project.read, admin.manage_users). Permissions for modules that don't exist
yet (lab.upload, calculation.run, review.approve, etc.) are intentionally
NOT pre-seeded -- adding permission rows for capabilities that don't exist
would be exactly the kind of "looks implemented but isn't" gap PIGL's
authorization explicitly warned against. They will be added, seeded, and
wired into the matrix module-by-module as each module is actually built.

Run with: python -m app.seed
"""
import os
import sys

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.security import hash_password
from app.models.rbac import Permission, Role, RolePermission, User

ROLES = [
    ("ENGINEER", "Engineer", "Geotechnical Engineers, Geophysicists, Field Engineers/Investigators, Survey/GIS Personnel"),
    ("TECHNICAL_REVIEWER", "Technical Reviewer", "Reviews and approves calculations, interpretations and reports"),
    ("LABORATORY_USER", "Laboratory User", "Laboratory Personnel"),
    ("PROJECT_MANAGER", "Project Manager", "Manages project-level information and status"),
    ("ADMINISTRATOR", "Administrator", "System administration: users, roles, permissions, project membership"),
    ("CLIENT_EXTERNAL_REVIEWER", "Client / External Reviewer", "Controlled, read-scoped access to approved project information"),
]

PERMISSIONS = [
    ("project.create", "Create a new project"),
    ("project.read", "View a project's details"),
    ("admin.manage_users", "Manage users, roles, permissions and project membership"),
]

# role_code -> [permission_code, ...]
# Matrix reflects Implementation Design Rev 2 §E.3. CLIENT_EXTERNAL_REVIEWER
# deliberately does not inherit TECHNICAL_REVIEWER or PROJECT_MANAGER
# permissions (explicit PIGL/Product instruction).
DEFAULT_MATRIX = {
    "ENGINEER": ["project.read"],
    "TECHNICAL_REVIEWER": ["project.read"],
    "LABORATORY_USER": ["project.read"],
    "PROJECT_MANAGER": ["project.create", "project.read"],
    "ADMINISTRATOR": ["project.create", "project.read", "admin.manage_users"],
    "CLIENT_EXTERNAL_REVIEWER": ["project.read"],
}


def seed(db: Session) -> None:
    role_by_code: dict[str, Role] = {}
    for code, name, description in ROLES:
        role = db.query(Role).filter(Role.code == code).first()
        if role is None:
            role = Role(code=code, name=name, description=description)
            db.add(role)
            db.flush()
        role_by_code[code] = role

    permission_by_code: dict[str, Permission] = {}
    for code, description in PERMISSIONS:
        perm = db.query(Permission).filter(Permission.code == code).first()
        if perm is None:
            perm = Permission(code=code, description=description)
            db.add(perm)
            db.flush()
        permission_by_code[code] = perm

    for role_code, perm_codes in DEFAULT_MATRIX.items():
        role = role_by_code[role_code]
        for perm_code in perm_codes:
            perm = permission_by_code[perm_code]
            exists = (
                db.query(RolePermission)
                .filter(RolePermission.role_id == role.id, RolePermission.permission_id == perm.id)
                .first()
            )
            if exists is None:
                db.add(RolePermission(role_id=role.id, permission_id=perm.id))

    db.commit()

    # Bootstrap admin account, so someone can log in and create the first
    # organization/client/project/users through the API without a direct
    # database edit. Credentials come from environment variables so a real
    # password is never committed to source control.
    # Default domain is .example (IANA-reserved for documentation, RFC 2606)
    # rather than .local -- pydantic's EmailStr / email-validator rejects
    # .local, .test, .invalid, and .localhost outright as special-use
    # domains, which would make the very first login attempt fail
    # validation before it even reached a password check. In a real
    # deployment, set GI_BOOTSTRAP_ADMIN_EMAIL to an actual PIGL email
    # address rather than relying on this default.
    admin_email = os.environ.get("GI_BOOTSTRAP_ADMIN_EMAIL", "admin@pigl.example")
    admin_password = os.environ.get("GI_BOOTSTRAP_ADMIN_PASSWORD")
    existing_admin = db.query(User).filter(User.email == admin_email).first()
    if existing_admin is None:
        if not admin_password:
            print(
                "GI_BOOTSTRAP_ADMIN_PASSWORD not set -- skipping bootstrap admin creation. "
                "Set it and re-run `python -m app.seed` to create the initial administrator.",
                file=sys.stderr,
            )
            return
        admin = User(
            email=admin_email,
            name="Bootstrap Administrator",
            password_hash=hash_password(admin_password),
            global_role_id=role_by_code["ADMINISTRATOR"].id,
        )
        db.add(admin)
        db.commit()
        print(f"Created bootstrap administrator: {admin_email}")


if __name__ == "__main__":
    db = SessionLocal()
    try:
        seed(db)
    finally:
        db.close()
