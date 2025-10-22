from enum import Enum
from typing import Dict, List


class NotificationType(Enum):
    def __init__(self, value, title: Dict[str, str], template: Dict[str, str], action: List[dict] = []):
        self._value_ = value
        self._title = title
        self._template = template
        self._action = action

    @property
    def template(self) -> dict:
        return self._template

    @property
    def title(self) -> dict:
        return self._title

    def action(self, lang="en", data: dict = {}) -> list:
        return [{"name": action["name_" + lang], "url": action["url"].format(**data)} for action in self._action]

    @classmethod
    def from_value(cls, value: str):
        for item in cls:
            if item.value == value:
                return item
        return None

    NEW_PODCAST_SERIES = (
        "new_podcast_series",
        {"en": "🎉 New podcast series available.", "fr": "🎉 Nouvelle série de podcasts disponible."},
        {"en": "Check out the new podcast series: {series_title}.", "fr": "Découvrez la nouvelle série de podcasts : {series_title}."},
        [{"name_en": "Listen now", "name_fr": "Écouter maintenant", "url": "/podcast"}]
    )

    NEW_PODCAST = (
        "new_podcast",
        {"en": "🎧 New podcast released.", "fr": "🎧 Nouveau podcast publié."},
        {"en": "A new podcast '{podcast_title}' was released in the series {series_title}.", "fr": "Un nouveau podcast '{podcast_title}' a été publié dans la série {series_title}."},
        [{"name_en": "Listen now", "name_fr": "Écouter maintenant", "url": "/podcast"}]
    )

    NEW_EPISODE = (
        "new_episode",
        {"en": "🎬 New episode released.", "fr": "🎬 Nouvel épisode publié."},
        {"en": "A new episode '{episode_title}' is available for {series_title}.", "fr": "Un nouvel épisode '{episode_title}' est disponible pour {series_title}."},
        [{"name_en": "Watch now", "name_fr": "Regarder maintenant", "url": "/series"}]
    )

    NEW_EBOOK = (
        "new_ebook",
        {"en": "📘 New ebook available.", "fr": "📘 Nouvel ebook disponible."},
        {"en": "A new ebook titled '{ebook_title}' has been added.", "fr": "Un nouvel ebook intitulé '{ebook_title}' a été ajouté."},
        [{"name_en": "Read now", "name_fr": "Lire maintenant", "url": "/ebooks"}]
    )

    NEW_STREAMING_EVENT = (
        "new_streaming_event",
        {"en": "📺 New streaming event.", "fr": "📺 Nouvel événement en streaming."},
        {"en": "Join us for a new streaming event: '{event_title}' at {event_time}.", "fr": "Rejoignez-nous pour un nouvel événement en streaming : '{event_title}' à {event_time}."},
        [{"name_en": "Join now", "name_fr": "Rejoindre maintenant", "url": "/streaming"}]
    )

    REMINDER_EVENT = (
        "reminder_event",
        {"en": "⏰ Reminder for upcoming event.", "fr": "⏰ Rappel pour un événement à venir."},
        {"en": "Don't forget to join the event '{event_title}' at {event_time}.", "fr": "N'oubliez pas de rejoindre l'événement '{event_title}' à {event_time}."},
        [{"name_en": "Join now", "name_fr": "Rejoindre maintenant", "url": "/streaming"}]
    )
