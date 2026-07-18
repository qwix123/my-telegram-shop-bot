# emoji_manager.py

from database import Database
from config import DEFAULT_EMOJI, EMOJI_MEANINGS

db = Database()
_emoji_cache = {}


def load_emojis_from_db():
    """Загружает эмодзи из БД в кэш"""
    global _emoji_cache
    _emoji_cache = db.get_all_emojis()


def e(name: str) -> str:
    """Главная функция получения эмодзи. Используется во всём коде."""
    default = DEFAULT_EMOJI.get(name, "")

    if name in _emoji_cache:
        emoji_data = _emoji_cache[name]
        emoji_id = emoji_data.get('id')
        emoji_char = emoji_data.get('char') or default
        if emoji_id:
            return f'<tg-emoji emoji-id="{emoji_id}">{emoji_char}</tg-emoji>'

    return default


def smart_match_emojis(sticker_set) -> dict:
    """Умный подбор эмодзи из набора"""
    stickers = sticker_set.stickers
    matched = {}
    used_ids = set()

    all_stickers = []
    for sticker in stickers:
        if sticker.custom_emoji_id:
            all_stickers.append({
                'id': sticker.custom_emoji_id,
                'emoji': sticker.emoji or ''
            })

    # ЭТАП 1: Точное совпадение по эмодзи
    for role, keywords in EMOJI_MEANINGS.items():
        if role in matched:
            continue
        for sticker in all_stickers:
            if sticker['id'] in used_ids:
                continue
            if sticker['emoji'] and sticker['emoji'] in keywords:
                matched[role] = {'id': sticker['id'], 'char': sticker['emoji']}
                used_ids.add(sticker['id'])
                break

    # ЭТАП 2: Заполнение оставшихся ролей случайными эмодзи из набора
    remaining_roles = [r for r in DEFAULT_EMOJI.keys() if r not in matched]
    available_stickers = [s for s in all_stickers if s['id'] not in used_ids]

    for role, sticker in zip(remaining_roles, available_stickers):
        matched[role] = {
            'id': sticker['id'],
            'char': sticker['emoji'] or DEFAULT_EMOJI.get(role, '')
        }
        used_ids.add(sticker['id'])

    return matched


async def apply_emoji_pack(bot, pack_name: str) -> dict:
    """Загружает и применяет набор эмодзи"""
    try:
        sticker_set = await bot.get_sticker_set(pack_name)

        if not sticker_set.stickers:
            return {'success': False, 'error': 'Набор пуст'}

        first_sticker = sticker_set.stickers[0]
        if not first_sticker.custom_emoji_id:
            return {
                'success': False,
                'error': 'Это не набор премиум-эмодзи'
            }

        matched = smart_match_emojis(sticker_set)

        if not matched:
            return {'success': False, 'error': 'Не удалось подобрать эмодзи'}

        db.clear_emojis()
        for role, data in matched.items():
            db.set_emoji(role, data['id'], data['char'])

        load_emojis_from_db()

        return {
            'success': True,
            'matched': matched,
            'total_in_set': len(sticker_set.stickers),
            'pack_title': sticker_set.title,
            'pack_name': pack_name
        }

    except Exception as ex:
        return {'success': False, 'error': str(ex)}


def reset_emojis() -> None:
    """Сбрасывает эмодзи на дефолтные"""
    db.clear_emojis()
    load_emojis_from_db()


# Загружаем эмодзи при импорте модуля
load_emojis_from_db()