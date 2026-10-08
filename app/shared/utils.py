"""
app/utils.py

This will have some things need for different cases
"""

import random

DEMO_SONGS_LINKS = [
    "https://suno.com/s/JKmaWAzKI6CiuQMJ",
    "https://suno.com/s/cbDOEH5feyWw6oEF",
    "https://suno.com/s/C9EJnItzEbYApJMH",
    "https://suno.com/s/WxZwWbtM8cb5G48P",
    "https://suno.com/s/lKK8wrwiodr2R2SS",
    "https://suno.com/s/Cij6o9LwTCxmb5Y7",
    "https://suno.com/s/RpJiid6IVcLKzHPd",
    "https://suno.com/s/aR3tsMFA68Q9lNuJ",
    "https://suno.com/s/NQ1bhdeDofPumgBY",
    "https://suno.com/s/UXNbVRTlqvVb2Nd1",
    "https://suno.com/s/Xp3XZnfea2MXGpap",
    "https://suno.com/s/o32UL0hRByg1yPyK",
    "https://suno.com/s/NY3DvLKQ5QopDzPU",
    "https://suno.com/s/YZ33o5QaXED9iO0S",
    "https://suno.com/s/AwI6KsFH3YxZZgaz",
    "https://suno.com/s/zfqMzGmNlw9bTvAT",
    "https://suno.com/s/Fce4w7EnIQfRhPUL",
    "https://suno.com/s/VnR5ZuCghr8ixRYO",
    "https://suno.com/s/APAJBfHXzpLnBsEs",
    "https://suno.com/s/DvOwi5JCbS0PSNsT",
    "https://suno.com/s/RbiSw2UYp0J7sJkY",
    "https://suno.com/s/xGMsb9CspedVbECW",
    "https://suno.com/s/QJ8JomxCWEeR2MfX",
    "https://suno.com/s/IQjJCfrVTRu0wvZO",
    "https://suno.com/s/1lPpWawS5O0VIe1W",
    "https://suno.com/s/gG1qk2qA4rAI5MD8",
]


def get_random_demo_songs_links(count: int = 3) -> list[str]:
    """Returns a specified number of random unique demo song links."""
    return random.sample(DEMO_SONGS_LINKS, count)
