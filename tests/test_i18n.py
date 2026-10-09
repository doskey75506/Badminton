import re
import string
from pathlib import Path

import i18n


def _fields(lang):
    return {
        key: {
            field
            for _, field, _, _ in string.Formatter().parse(text)
            if field is not None
        }
        for key, text in i18n.LANGS[lang].items()
    }


def test_langs_have_same_keys():
    assert set(i18n.LANGS["zh"]) == set(i18n.LANGS["en"])


def test_format_placeholders_match():
    zh_fields = _fields("zh")
    en_fields = _fields("en")
    for key in i18n.LANGS["zh"]:
        assert zh_fields[key] == en_fields[key], key


def test_app_uses_existing_keys():
    app_src = (Path(__file__).parent.parent / "app.py").read_text(
        encoding="utf-8"
    )
    keys = set(re.findall(r'T\("([a-z0-9_]+)"\)', app_src))
    assert keys
    assert keys <= set(i18n.LANGS["zh"])


def test_app_never_double_formats():
    app_src = (Path(__file__).parent.parent / "app.py").read_text(
        encoding="utf-8"
    )
    assert 'T("' not in app_src or not re.search(
        r'T\("[a-z0-9_]+\"\)\.format', app_src
    )


def test_t_formats():
    assert i18n.t("zh", "member_chip", n="张三", r="1000") == "张三（1000）"
    assert i18n.t("en", "member_chip", n="Zhang", r="1000") == "Zhang (1000)"
    assert i18n.t("en", "h_count", n=3) == "3 matches"
