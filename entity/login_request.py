from dataclasses import dataclass


@dataclass(frozen=True)
class LoginRequest:
    login_name: str
    password_hash: str
    location: int
    game_id: int
    user_ip: int
    captcha: bytes