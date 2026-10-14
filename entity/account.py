from dataclasses import dataclass, field
from typing import Dict


@dataclass(frozen=True)
class Account:
    user_id: int
    login_name: str
    password_hash: str
    role_created: bool
    banned: bool
    profile: Dict[str, object] = field(default_factory=dict)