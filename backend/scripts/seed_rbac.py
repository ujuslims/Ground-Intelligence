"""
Seeds the six MVP system roles and a default permission matrix, per
Implementation Design Rev 2 §E.1 and §E.3.

The §E.3 matrix is explicitly labelled in Rev 2 as "a reasonable default
within the boundaries the Register assigns to the development team" -- NOT
the resolved PRD-persona-to-role mapping (that mapping is itself resolved in
§E.1; what remains an implementation detail is the exact permission cell
values, which PIGL may edit as RolePermission data without a redeploy).

Run with: python -m scripts.seed_rbac
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import SessionLocal, Base, engine
from app import models  # noqa: F401
from app.models.identity import Role, Permission, RolePermission

ROLES = [
    ("ENGINEER", "Geotechnical/geophysical/field engineers, GIS personnel. Creates/edits investigation data, runs calculations."),
    ("TECHNICAL_REVIEWER", "Reviews calculations, interpretations and reports; approves or rejects via Review."),
    ("LABORATORY_USER", "Uploads/manages laboratory information where permitted."),
    ("PROJECT_MANAGER", "Manages project-level information and monitors status."),
    ("ADMINISTRATOR", "Manages users, roles, permissions and project membership; system configuration."),
    ("CLIENT_EXTERNAL_REVIEWER", "Controlled, read-scoped access to approved project information only."),
]

PERMISSIONS = [
    "investigation:write",
    "laboratory:write",
    "laboratory:view",
    "calculation:run",
    "review:approve",
    "review:comment",
    "report:view_approved",
    "admin:manage_users",
]

# permission_code -> {role_name: level}
MATRIX = {
    "investigation:write": {"ENGINEER": "full", "ADMINISTRATOR": "full"},
    "laboratory:write": {"LABORATORY_USER": "full", "ADMINISTRATOR": "full"},
    "laboratory:view": {
        "ENGINEER": "view", "TECHNICAL_REVIEWER": "view", "LABORATORY_USER": "full",
        "PROJECT_MANAGER": "view", "ADMINISTRATOR": "full",
    },
    "calculation:run": {"ENGINEER": "full", "ADMINISTRATOR": "full"},
    "review:approve": {"TECHNICAL_REVIEWER": "full", "ADMINISTRATOR": "full"},
    "review:comment": {
        "ENGINEER": "comment", "PROJECT_MANAGER": "comment", "CLIENT_EXTERNAL_REVIEWER": "comment",
    },
    "report:view_approved": {
        "ENGINEER": "view", "TECHNICAL_REVIEWER": "view", "LABORATORY_USER": "view",
        "PROJECT_MANAGER": "view", "ADMINISTRATOR": "view", "CLIENT_EXTERNAL_REVIEWER": "view",
    },
    "admin:manage_users": {"ADMINISTRATOR": "full"},
}


def seed():
    Base.metadata.create_all(engine)
    db = SessionLocal()
    try:
        role_rows = {}
        for name, desc in ROLES:
            role = db.query(Role).filter_by(name=name).first()
            if not role:
                role = Role(name=name, description=desc)
                db.add(role)
                db.flush()
            role_rows[name] = role

        perm_rows = {}
        for code in PERMISSIONS:
            perm = db.query(Permission).filter_by(code=code).first()
            if not perm:
                perm = Permission(code=code, description=code)
                db.add(perm)
                db.flush()
            perm_rows[code] = perm

        for perm_code, role_levels in MATRIX.items():
            for role_name, level in role_levels.items():
                exists = (
                    db.query(RolePermission)
                    .filter_by(role_id=role_rows[role_name].id, permission_id=perm_rows[perm_code].id)
                    .first()
                )
                if not exists:
                    db.add(RolePermission(role_id=role_rows[role_name].id, permission_id=perm_rows[perm_code].id, level=level))

        db.commit()
        print(f"Seeded {len(ROLES)} roles, {len(PERMISSIONS)} permissions, RBAC matrix applied.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
