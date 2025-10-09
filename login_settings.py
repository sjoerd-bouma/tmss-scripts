import os
import yaml

from getpass import getpass
from typing import TypedDict, Optional

LOGIN_FILE: str = os.path.join(os.environ.get("TMSS_LOGIN_FILE"), "login.yaml")

class LoginSettings(TypedDict):
    username: str
    password: Optional[str]
    host: str
    port: int

def get_settings() -> LoginSettings:
    with open(LOGIN_FILE, "r") as fp:
        settings: LoginSettings = yaml.load(fp, Loader=yaml.FullLoader)

    for key, key_type in LoginSettings.__annotations__.items():
        if hasattr(key_type, "__args__"):
            if type(None) in key_type.__args__:
                continue
        if key not in settings:
            raise RuntimeError(f"{LOGIN_FILE} is missing {key}")

    if 'password' not in settings or settings['password'] is None:
        settings['password'] = getpass(f"Please provide the password for user {settings['username']}: ")

    return settings
