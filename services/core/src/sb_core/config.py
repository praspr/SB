"""Configuration for the unified local service.

Priority (highest → lowest):
  1. Environment variables (``SB_CORE_*``)
  2. YAML config file (``~/.config/sb/config.yaml`` or ``SB_CORE_CONFIG_PATH``)
  3. Built-in defaults

List fields (``roots``, ``git_authors``) accept JSON arrays or
space-separated values from environment variables.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from pydantic import field_validator, model_validator
from pydantic_settings import (
    BaseSettings,
    EnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)
from pydantic.fields import FieldInfo

_DEFAULT_YAML = Path("~/.config/sb/config.yaml")


def _to_str_list(v: Any) -> list:
    """Coerce a raw roots/authors value into a list of items (str or dict).

    Accepts a Python list (YAML), a JSON array string, or a space-separated
    string (env).  Returns the list untouched when already a list.
    """
    if isinstance(v, list):
        return v
    if isinstance(v, str):
        s = v.strip()
        if not s:
            return []
        if s.startswith("["):
            try:
                parsed = json.loads(s)
                if isinstance(parsed, list):
                    return parsed
            except json.JSONDecodeError:
                pass
        return s.split()
    return []


def _normalize_roots(v: Any) -> list[dict]:
    """Normalize roots into ``[{path, label?, domain?}, ...]``.

    String items become ``{"path": item}``.  Dict items preserve ``label`` and
    ``domain`` when present; items without a ``path`` are dropped.
    """
    result: list[dict] = []
    for item in _to_str_list(v):
        if isinstance(item, dict):
            path = item.get("path")
            if not path:
                continue
            entry: dict = {"path": str(path)}
            if item.get("label"):
                entry["label"] = str(item["label"])
            if item.get("domain"):
                entry["domain"] = str(item["domain"])
            result.append(entry)
        elif item is not None:
            result.append({"path": str(item)})
    return result


def _yaml_config_path() -> Path | None:
    """Return the YAML config path (from env or default), or None if not set."""
    custom = os.environ.get("SB_CORE_CONFIG_PATH", "").strip()
    if custom:
        return Path(custom).expanduser()
    default = _DEFAULT_YAML.expanduser()
    return default  # YamlConfigSettingsSource handles nonexistent files gracefully


class _RobustEnvSource(EnvSettingsSource):
    """EnvSettingsSource that falls back to the raw string on JSON parse failure.

    pydantic-settings tries ``json.loads()`` on complex fields (lists) before
    our ``field_validator`` runs.  For non-JSON values like ``/a /b`` this
    raises ``SettingsError``.  We catch that and return the raw string so the
    ``_coerce_list`` validator can handle it.
    """

    def prepare_field_value(
        self, field_name: str, field: FieldInfo, value: Any, value_is_complex: bool
    ) -> Any:
        try:
            return super().prepare_field_value(
                field_name, field, value, value_is_complex
            )
        except Exception:  # noqa: BLE001 – SettingsError / JSONDecodeError
            return value


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="SB_CORE_", extra="ignore")

    host: str = "127.0.0.1"
    port: int = 8787
    skills_root: Path | None = None

    # Core SQLite store path
    db_path: Path = Path("~/.local/share/sb/core.db")

    # Roots for changelog and git adapters (plain path strings, back-compat)
    roots: list[str] = []

    # Roots with optional label/domain preserved: [{path, label?, domain?}, ...]
    roots_detailed: list[dict] = []

    # Git author filter (e.g. ["you@example.com"])
    git_authors: list[str] = []

    # ---- Identity (optional; no secrets) ----
    identity_name: str | None = None
    identity_email: str | None = None

    # ---- Goals file (schema documented in goals.py) ----
    goals_path: Path = Path("~/.config/sb/goals.yaml")

    # ---- claudegate LLM client (no credentials) ----
    llm_base_url: str = "http://127.0.0.1:9999"
    llm_timeout: float = 30.0
    llm_tier: str | None = None
    llm_model: str = "claude"
    llm_cache_dir: Path = Path("~/.local/share/sb/cache")

    # ---- Expand nested identity + derive detailed roots from YAML/env ----

    @model_validator(mode="before")
    @classmethod
    def _expand_nested(cls, data: Any) -> Any:  # noqa: N805
        if not isinstance(data, dict):
            return data
        identity = data.get("identity")
        if isinstance(identity, dict):
            if data.get("identity_name") is None and identity.get("name"):
                data["identity_name"] = identity["name"]
            if data.get("identity_email") is None:
                email = identity.get("email")
                if not email:
                    # Fall back to the first string in an ``emails`` list.
                    emails = identity.get("emails")
                    if isinstance(emails, list):
                        email = next(
                            (e for e in emails if isinstance(e, str) and e.strip()),
                            None,
                        )
                if email:
                    data["identity_email"] = email
        if "roots" in data and "roots_detailed" not in data:
            data["roots_detailed"] = _normalize_roots(data["roots"])
        return data

    # ---- List-field validators: accept JSON arrays OR space-separated values ----

    @field_validator("roots", "git_authors", mode="before")
    @classmethod
    def _coerce_list(cls, v: Any) -> Any:  # noqa: N805
        """Accept JSON-encoded lists, space-separated strings from env, or YAML lists.

        For ``roots``, each list item may be a plain string or a dict with a
        ``path`` key (rich YAML format ``{path: ..., label: ..., ...}``).
        Only the ``path`` value is used; other keys are silently ignored.
        """
        if not isinstance(v, str):
            # Handle list items that may be dicts (rich YAML roots format)
            if isinstance(v, list):
                result = []
                for item in v:
                    if isinstance(item, dict):
                        p = item.get("path")
                        if p:
                            result.append(str(p))
                    elif item is not None:
                        result.append(str(item))
                return result
            return v
        v = v.strip()
        if not v:
            return []
        if v.startswith("["):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    # Recurse to handle dict items in JSON lists too
                    return cls._coerce_list(parsed)
            except json.JSONDecodeError:
                pass
        return v.split()

    # ---- Custom settings sources: env overrides YAML ----

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        yaml_path = _yaml_config_path()
        yaml_source = YamlConfigSettingsSource(
            settings_cls,
            yaml_file=str(yaml_path) if yaml_path else None,
        )
        # Priority: init > env (robust) > yaml > file_secret
        robust_env = _RobustEnvSource(settings_cls)
        return (init_settings, robust_env, yaml_source, file_secret_settings)


settings = Settings()
