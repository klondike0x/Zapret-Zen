<div align="center">

<picture>
  <img alt="Zapret-Zen banner" src="ui_assets/icons/app_large.png" width="200">
</picture>

# Zapret Zen

**Утилита для удобного и быстрого обхода блокировок на Windows**

<br />
<br />

[![Version](https://img.shields.io/github/v/release/peshk0v/Zapret-Zen?style=for-the-badge&logo=github&color=5865F2&label=Версия)](https://github.com/peshk0v/Zapret-Zen/releases)
[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![PySide6](https://img.shields.io/badge/PySide6-6.7%2B-41CD52?style=for-the-badge&logo=qt&logoColor=white)](https://doc.qt.io/qtforpython/)
[![License](https://img.shields.io/github/license/peshk0v/Zapret-Zen?style=for-the-badge&color=E0A96D&label=Лицензия)](LICENSE)
[![Telegram](https://img.shields.io/badge/Telegram-Канал-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://t.me/zapzen)

</div>

---

## 🖼️ Скриншоты

<div align="center">

| Главная | Сервисы | Модификации |
| :---: | :---: | :---: |
| <picture><source media="(prefers-color-scheme: dark)" srcset="assets/screenshot_dashboard_dark.png"><source media="(prefers-color-scheme: light)" srcset="assets/screenshot_dashboard_light.png"><img src="assets/screenshot_dashboard_light.png" width="280" alt="Главная"></picture> | <picture><source media="(prefers-color-scheme: dark)" srcset="assets/screenshot_services_dark.png"><source media="(prefers-color-scheme: light)" srcset="assets/screenshot_services_light.png"><img src="assets/screenshot_services_light.png" width="280" alt="Сервисы"></picture> | <picture><source media="(prefers-color-scheme: dark)" srcset="assets/screenshot_mods_dark.png"><source media="(prefers-color-scheme: light)" srcset="assets/screenshot_mods_light.png"><img src="assets/screenshot_mods_light.png" width="280" alt="Модификации"></picture> |

</div>

---

## ⚙️ Возможности

| Функция | Описание |
| :--- | :--- |
| 🛡️ **Обход блокировок** | Управление компонентами `zapret` и `tg-ws-proxy`: запуск, остановка, просмотр статуса, фоновый автозапуск |
| 👤 **Профили настроек** | Быстрое переключение между готовыми конфигурациями и пресетами под разные задачи и сети |
| 🎛️ **Пресеты сервисов** | Быстрый и удобный выбор сервисов, разбитых по категориям |
| 🧩 **Система модов** | Установка, обновление и отключение пользовательских модов сообщества для расширения правил |
| 🎨 **Динамические темы** | Кастомизация интерфейса: Light, Dark, OLED темы и настраиваемые акцентные цвета |
| 🩺 **Диагностика** | Встроенный модуль проверки системы: тест связности, проверка DNS и целостности компонентов |
| ⚙️ **Автоконфигурация** | Автоматический подбор оптимальной стратегии на основе выбранных сервисов |
| 🔔 **Уведомления** | Нативная система информирования о событиях, ошибках и выходе обновлений |
| 📥 **Системный трей** | Работа в фоновом режиме, сворачивание и тихий запуск при старте ОС |
| 🔄 **Автообновления** | Автоматическая проверка свежих релизов приложения и модов прямо с GitHub |
| 🌐 **Локализация** | Полная поддержка русского и английского языков |

---

## 💻 Установка

### 📦 Портативная версия (Рекомендуется)

1. Скачайте архив `zapret_zen_<version>_portable_win_<architecture>.zip` со страницы [Releases](https://github.com/peshk0v/Zapret-Zen/releases) под вашу архитектуру CPU.
2. Распакуйте содержимое в удобную папку.
3. Запустите `zapret_zen.exe`.

### 💿 Инсталлятор

1. Скачайте файл `install_zapretzen_<version>_universal.exe` со страницы [Releases](https://github.com/peshk0v/Zapret-Zen/releases).
2. Запустите мастер установки — он развернёт программу и добавит запись в стандартный список приложений Windows.

---

## 🛠️ Разработка и сборка

### Системные требования
* **Python**: `3.11+`
* **ОС**: Windows 10 / 11

### 1. Настройка окружения

```powershell
# Создание и активация виртуального окружения
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Установка зависимостей разработчика
pip install -e .[dev]

```

### 2. Запуск из исходников

```powershell
.\.venv\Scripts\python.exe -m zapret_zen.main

```

### 3. Сборка Portable-версии

```powershell
.\.venv\Scripts\python.exe scripts\sync_app_icon.py
.\.venv\Scripts\pyinstaller.exe packaging/zapret_zen.spec --distpath dist_pyinstaller --workpath build_pyinst --noconfirm

```

### 4. Сборка Инсталлятора

```powershell
# Формирование payload-архива
$tempDir = Join-Path $env:TEMP "zapretzen_payload"
$payloadRoot = Join-Path $tempDir "zapret_zen"
Copy-Item -LiteralPath dist_pyinstaller\zapret_zen -Destination $payloadRoot -Recurse -Force
Compress-Archive -Path (Join-Path $tempDir "*") -DestinationPath installer_payload\win_x64.zip -CompressionLevel Optimal -Force
Remove-Item $tempDir -Recurse -Force

# Компиляция инсталлятора
.\.venv\Scripts\pyinstaller.exe packaging/install_zapretzen.spec --distpath dist_installer --workpath build_installer --noconfirm
```

---

## 📁 Структура проекта

```text
Zapret-Zen/
├── assets/           # Графические ресурсы для документации
├── configs/          # Пользовательские конфиги и переопределения правил
├── data/             # Состояние приложения (настройки, профили, кэш)
├── installer/        # Исходный код мастера установки
├── mods/             # Установленные моды сообщества
├── packaging/        # Файлы конфигурации .spec для PyInstaller
├── runtime/          # Встроенные бинарники (zapret, tg-ws-proxy, dns-manager)
├── scripts/          # Вспомогательные скрипты сборки и утилиты
├── src/zapret_zen/   # Исходный код приложения
│   ├── domain/       # Модели данных (настройки, компоненты, сервисы)
│   ├── services/     # Бизнес-логика, интеграции и бэкенд
│   └── ui/           # Графический интерфейс на PySide6
├── themes/           # JSON-файлы оформления тем
└── ui_assets/        # Иконки (Flaticon), шрифты, логотипы

```

---

## 🧲 Используемые компоненты

| Инструмент | Автор / Проект |
| --- | --- |
| **zapret-discord-youtube** | [Flowseal](https://github.com/Flowseal/zapret-discord-youtube) |
| **tg-ws-proxy** | [Flowseal](https://github.com/Flowseal/tg-ws-proxy) |
| **zapret ecosystem** | [bol-van](https://github.com/bol-van/zapret-win-bundle) |

> [!CAUTION]
> ### Авторство и правовая информация
> 
> 
> **Zapret Zen** является модификацией проекта **[Zapret Hub](https://github.com/goshkow/Zapret-Hub)** от [goshkow](https://github.com/goshkow).
> Приложение не присваивает себе авторство встроенных утилит, оригинального интерфейса и менеджера. Пользователь вправе модифицировать файлы самостоятельно, однако авторские права оригинальных разработчиков сохраняются.
> В графическом интерфейсе используются иконки Uicons, права на которые принадлежат [Flaticon](https://www.flaticon.com/uicons).

---

## 📞 Обратная связь

| Назначение | Ссылка |
| --- | --- |
| 🐛 **Баг-трекер** | [Сообщить об ошибке](https://github.com/peshk0v/Zapret-Zen/issues/new) |
| 💬 **Обсуждения** | [Задать вопрос или предложить идею](https://github.com/peshk0v/Zapret-Zen/discussions) |
| 📢 **Новости** | [Telegram-канал проекта](https://t.me/zapzen) |

---

## ©️ Лицензия

Распространяется под лицензией [MIT](https://www.google.com/search?q=LICENSE).
