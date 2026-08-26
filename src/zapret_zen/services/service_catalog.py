from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ServicePreset:
    id: str
    title_ru: str
    title_en: str
    description_ru: str
    description_en: str
    icon_file: str
    accent: str
    short_description_ru: str = ""
    short_description_en: str = ""


@dataclass(frozen=True, slots=True)
class ServiceCategory:
    id: str
    title_ru: str
    title_en: str
    description_ru: str
    description_en: str
    icon_file: str
    member_ids: tuple[str, ...]


SERVICE_CATEGORIES: tuple[ServiceCategory, ...] = (
    ServiceCategory(
        id="gaming",
        title_ru="Gaming",
        title_en="Gaming",
        description_ru="Игровые платформы и лаунчеры",
        description_en="Games and launchers",
        icon_file="gaming.svg",
        member_ids=("epic-games", "battle-net", "league-of-legends", "riot-games", "roblox", "dnd"),
    ),
    ServiceCategory(
        id="socials",
        title_ru="Socials",
        title_en="Socials",
        description_ru="Социальные сети, мессенджеры и видео",
        description_en="Social media, messengers, and video",
        icon_file="socials.svg",
        member_ids=("discord", "youtube", "telegram-desktop", "tiktok", "instagram", "spotify", "reddit", "x-twitter", "netflix", "facebook", "wplace", "facetime"),
    ),
    ServiceCategory(
        id="workplace",
        title_ru="Workplace",
        title_en="Workplace",
        description_ru="Среды разработки, дизайн, нейросети и хостинг кода",
        description_en="Dev environments, design, neural networks, and code hosting",
        icon_file="workplace.svg",
        member_ids=("github", "figma", "ai"),
    ),
)


SERVICE_CATEGORY_MEMBER_IDS: set[str] = set()
for _cat in SERVICE_CATEGORIES:
    SERVICE_CATEGORY_MEMBER_IDS.update(_cat.member_ids)


def service_category_for_id(service_id: str) -> str | None:
    for _cat in SERVICE_CATEGORIES:
        if service_id in _cat.member_ids:
            return _cat.id
    return None


def service_ids_in_categories() -> set[str]:
    return set(SERVICE_CATEGORY_MEMBER_IDS)


ALWAYS_APPLY_SERVICE_IDS: tuple[str, ...] = ("cloudflare", "clouds")


SERVICE_PRESETS: tuple[ServicePreset, ...] = (
    ServicePreset("discord", "Discord", "Discord", "Голосовой чат, сообщения и медиа Discord", "Voice chat, messaging, and Discord media", "discord.svg", "#5865f2", "Голосовой чат, сообщения и медиа", "Voice chat, messages, and media"),
    ServicePreset("youtube", "YouTube", "YouTube", "Видео, превью, Shorts и CDN Google", "Video playback, thumbnails, Shorts, and Google CDN", "youtube.svg", "#ff0033"),
    ServicePreset("telegram-desktop", "Telegram", "Telegram", "Десктопное приложение Telegram для ПК", "Telegram desktop app for PC", "telegram.svg", "#26a5e4", "Десктопное приложение Telegram", "Telegram desktop app"),
    ServicePreset("roblox", "Roblox", "Roblox", "Игровая платформа и CDN Roblox", "Roblox platform and CDN", "roblox.svg", "#d8dde8"),
    ServicePreset("dnd", "D&D", "D&D", "D&D Beyond, Roll20, Foundry VTT и инструменты", "D&D Beyond, Roll20, Foundry VTT, and tools", "dnd.svg", "#9b2335", "D&D Beyond, Roll20, Foundry VTT", "D&D Beyond, Roll20, Foundry VTT"),
    ServicePreset("tiktok", "TikTok", "TikTok", "Лента, видео, авторизация и CDN TikTok", "Feed, video playback, auth, and TikTok CDN", "tiktok.svg", "#25f4ee", "Лента, видео, авторизация и CDN", "Feed, video, auth, and CDN"),
    ServicePreset("instagram", "Instagram", "Instagram", "Лента, фото, Reels и CDN Instagram", "Feed, photos, Reels, and Instagram CDN", "instagram.svg", "#e4405f"),
    ServicePreset("epic-games", "Epic Games", "Epic Games", "Магазин, лаунчер, загрузки и сервисы Epic", "Store, launcher, downloads, and Epic services", "epicgames.svg", "#eef2f8", "Магазин, лаунчер, загрузки и сервисы", "Store, launcher, downloads, and services"),
    ServicePreset("battle-net", "Battle.net", "Battle.net", "Лаунчер, игры Blizzard и загрузка контента", "Launcher, Blizzard games, and content delivery", "battledotnet.svg", "#148eff"),
    ServicePreset("spotify", "Spotify", "Spotify", "Веб-плеер, авторизация и музыкальный CDN", "Web player, auth, and music delivery CDN", "spotify.svg", "#1ed760", "Веб-плеер и авторизация", "Web player and auth"),
    ServicePreset("reddit", "Reddit", "Reddit", "Форумы, медиа, API и статические файлы Reddit", "Communities, media, API, and Reddit static files", "reddit.svg", "#ff4500", "Форумы, медиа, API и файлы Reddit", "Forums, media, API, and Reddit files"),
    ServicePreset("x-twitter", "X / Twitter", "X / Twitter", "Лента, медиа, API и короткие ссылки X", "Timeline, media, API, and X short links", "x.svg", "#f2f6ff"),
    ServicePreset("github", "GitHub", "GitHub", "Сайт, raw-файлы, ассеты и GitHub Pages", "Website, raw files, assets, and GitHub Pages", "github.svg", "#f0f6fc"),
    ServicePreset("riot-games", "Riot Games", "Riot Games", "Клиент Riot, авторизация и игровые сервисы", "Riot client, authentication, and game services", "riotgames.svg", "#d32936", "Клиент, авторизация и игровые сервисы", "Client, auth, and game services"),
    ServicePreset("league-of-legends", "LOL", "LOL", "Клиент League и игровые серверы Riot", "League client and Riot game servers", "leagueoflegends.svg", "#c89b3c"),
    ServicePreset("figma", "Figma", "Figma", "Файлы, макеты и CDN Figma", "Files, projects, and Figma CDN", "figma.svg", "#a259ff"),
    ServicePreset("ai", "AI", "AI", "Нейросети и AI-сервисы", "Neural networks and AI services", "ai.svg", "#7c3aed", "Нейросети и AI-сервисы", "Neural networks and AI services"),
    ServicePreset("netflix", "Netflix", "Netflix", "Стриминг, постеры и CDN Netflix", "Streaming, artwork, and Netflix CDN", "netflix.svg", "#e50914"),
    ServicePreset("facebook", "Facebook", "Facebook", "Лента, вход, медиа и CDN Facebook", "Feed, login, media, and Facebook CDN", "facebook.svg", "#1877f2"),
    ServicePreset("wplace", "WPlace", "WPlace", "Виртуальные рабочие пространства", "Virtual workspaces", "wplace.svg", "#4f73d9"),
    ServicePreset("facetime", "FaceTime", "FaceTime", "Видеозвонки Apple FaceTime", "Apple FaceTime video calls", "facetime.svg", "#30d158"),
)


SERVICE_PRESET_IDS = {item.id for item in SERVICE_PRESETS}
