#!/usr/bin/env python3
"""Generate translations/*.json for all Home Assistant UI languages.

Uses Google via deep-translator for machine translation (en/ru preserved).
Run from repo root: python3 scripts/generate_translations.py
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path

from deep_translator import GoogleTranslator

# homeassistant/generated/languages.py (subset check)
LANGUAGES = [
    "af",
    "ar",
    "bg",
    "bn",
    "bs",
    "ca",
    "cs",
    "cy",
    "da",
    "de",
    "el",
    "en",
    "en-GB",
    "eo",
    "es",
    "es-419",
    "et",
    "eu",
    "fa",
    "fi",
    "fr",
    "fy",
    "ga",
    "gl",
    "gsw",
    "he",
    "hi",
    "hr",
    "hu",
    "hy",
    "id",
    "is",
    "it",
    "ja",
    "ka",
    "ko",
    "lb",
    "lt",
    "lv",
    "mk",
    "ml",
    "nb",
    "nl",
    "nn",
    "pl",
    "pt",
    "pt-BR",
    "ro",
    "ru",
    "sk",
    "sl",
    "sq",
    "sr",
    "sr-Latn",
    "sv",
    "ta",
    "te",
    "th",
    "tr",
    "uk",
    "ur",
    "vi",
    "zh-Hans",
    "zh-Hant",
]

# Map Home Assistant locale file name -> Google Translate target language code
HA_TO_GOOGLE: dict[str, str] = {
    "zh-Hans": "zh-CN",
    "zh-Hant": "zh-TW",
    "en-GB": "en",
    "es-419": "es",
    "pt-BR": "pt",
    "sr-Latn": "sr",
    "fy": "nl",
    "gsw": "de",
    "nb": "no",
    "nn": "no",
    "lb": "de",
    "he": "iw",
}


def translate_value(translator: GoogleTranslator, text: str, cache: dict[str, str]) -> str:
    if text in cache:
        return cache[text]
    # Keep technical tokens readable
    stripped = text.strip()
    if not stripped:
        return text
    try:
        out = translator.translate(text)
        time.sleep(0.08)
    except Exception:
        out = text
    cache[text] = out
    return out


def walk_translate(obj: object, translator: GoogleTranslator, cache: dict[str, str]) -> object:
    if isinstance(obj, dict):
        return {k: walk_translate(v, translator, cache) for k, v in obj.items()}
    if isinstance(obj, list):
        return [walk_translate(v, translator, cache) for v in obj]
    if isinstance(obj, str):
        return translate_value(translator, obj, cache)
    return obj


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    en_path = root / "custom_components/qr_code_reader/translations/en.json"
    out_dir = root / "custom_components/qr_code_reader/translations"

    only_raw = os.environ.get("GENERATE_TRANSLATIONS_ONLY", "")
    only_set: set[str] | None = None
    if only_raw.strip():
        only_set = {x.strip() for x in only_raw.split(",") if x.strip()}

    en_data = json.loads(en_path.read_text(encoding="utf-8"))

    for ha_lang in LANGUAGES:
        if only_set is not None and ha_lang not in only_set:
            continue
        out_file = out_dir / f"{ha_lang}.json"
        if ha_lang == "en":
            out_file.write_text(
                json.dumps(en_data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            continue
        if ha_lang == "en-GB":
            out_file.write_text(
                json.dumps(en_data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            continue
        if ha_lang == "ru":
            # Maintained manually in translations/ru.json
            print("skip ru (manual)")
            continue

        google = HA_TO_GOOGLE.get(ha_lang, ha_lang.replace("_", "-"))
        try:
            translator = GoogleTranslator(source="en", target=google)
        except Exception:
            print(f"skip translator for {ha_lang} (unknown target {google}), using English")
            out_file.write_text(
                json.dumps(en_data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            continue

        cache: dict[str, str] = {}
        try:
            translated = walk_translate(en_data, translator, cache)
        except Exception as exc:
            print(f"{ha_lang}: translate failed ({exc}), using English")
            translated = en_data

        out_file.write_text(
            json.dumps(translated, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"ok {ha_lang}")
    print("done")


if __name__ == "__main__":
    main()
