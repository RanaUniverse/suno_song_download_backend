"""
app/bot_tg/services/accounts.py

Account related things will be here of how to handle accounts
"""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class UserAccount:
    downloads_count: int
    is_premium: bool


async def get_user_account(
    user_id: int,
) -> UserAccount | None:
    """
    Return the logged-in account linked to this Telegram user,
    or None if the user is not logged in.

    Placeholder: there is no login system yet, so this always returns None.
    Later: look up the DB/Redis here.
    """
    return None


def verify_user_with_payload_value(payload: str, user_id: int) -> bool:
    """
    Temporary check: the /start payload must equal the user's id.
    """
    return payload == str(user_id)
