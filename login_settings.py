import os
import yaml

from getpass import getpass, getuser
from typing import TypedDict, Optional, Any

from lofar_tmss_client.tmss_http_rest_client import TMSSsession


LOGIN_FILE: str = os.environ.get("TMSS_LOGIN_FILE", default="login.yaml")

class LoginSettings(TypedDict):
    username: Optional[str]
    password: Optional[str]
    token: Optional[str]
    host: str
    port: int

def _unset_check(key: str, input_dict: dict[Any, Any]) -> bool:
    return (key not in input_dict or input_dict[key] is None)

def _remove_key_if_present(input_dict: LoginSettings, keys: list[str]) -> LoginSettings:
    for key in keys:
        if key in input_dict:
            del input_dict[key]
    return input_dict

def get_settings() -> LoginSettings:
    with open(LOGIN_FILE, "r") as fp:
        settings: LoginSettings = yaml.load(fp, Loader=yaml.FullLoader)

    # Validate input YAML
    for key, key_type in LoginSettings.__annotations__.items():
        if hasattr(key_type, "__args__"):
            if type(None) in key_type.__args__:
                continue
        if key not in settings:
            raise RuntimeError(f"{LOGIN_FILE} is missing {key}")

    # Cleanup input YAML if extra keys are present
    for key in list(settings):
        if key not in LoginSettings.__annotations__:
            del settings[key]

    # Get an input token or password if not present in the input YAML
    if _unset_check("password", settings) and _unset_check("token", settings):
        input_type: str = input("Are you providing a [t]oken or [p]assword? ").lower()
        if input_type in {'t', 'token'}:
            input_type = "token"
        elif input_type in {'p', 'password'}:
            input_type = "password"
            if _unset_check("username", settings):
                settings['username'] = input("Please provide your TMSS username: ")
        else:
            raise InputError(f"Unknown input type '{input_type}', expected one of {'t', 'p', 'token', 'password'}")

        settings[input_type] = getpass(f"Please provide your {input_type}: ")

    # Case: Password set in login.yaml, but not username
    if _unset_check("username", settings) and _unset_check("token", settings):
        settings['username'] = input("Please provide your TMSS username: ")

    # Token authentication does not use usernames
    if not _unset_check("token", settings):
        settings = _remove_key_if_present(settings, ['password'])
    # Password auth does not use token
    elif not _unset_check("password", settings):
        settings = _remove_key_if_present(settings, ['token'])

    # Used by scripts to add names to SUs
    if _unset_check("username", settings):
        settings['username'] = getuser()

    return settings

def get_tmss_session(settings: LoginSettings) -> TMSSsession:
    local_settings = settings.copy()
    if not _unset_check('token', local_settings):
        if "username" in local_settings:
            del local_settings["username"]
        return TMSSsession.token_auth(**local_settings)
    if not _unset_check('password', local_settings):
        return TMSSsession(**local_settings)
    raise RuntimeError("Not passed a valid authentication configuration")
