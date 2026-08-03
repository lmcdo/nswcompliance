# prior-art-checked: deliberate clean-room OSS extraction; standalone package must not import project code (see oss/prose-gate/EXTRACTION.md)
"""Load configuration from ``.prose-gate.toml`` and bundled presets."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path

from .exclusions import ExclusionRules
from .selectors import DEFAULT_PATTERNS

CONFIG_FILENAME = ".prose-gate.toml"


class ConfigError(Exception):
    """Raised for unreadable config files or unknown presets."""


@dataclass
class Config:
    preset: str | None = "assurance"
    extra_terms: list[str] = field(default_factory=list)
    user_facing: list[str] = field(default_factory=lambda: list(DEFAULT_PATTERNS))
    diff_base: str = "main"
    exclusions: ExclusionRules = field(default_factory=ExclusionRules)


def load_config(path: str | None = None) -> Config:
    """Load config from an explicit path, or ``.prose-gate.toml`` in the
    current directory, or fall back to pure defaults."""
    if path is not None:
        config_path = Path(path)
        if not config_path.is_file():
            raise ConfigError(f"config file not found: {path}")
    else:
        config_path = Path.cwd() / CONFIG_FILENAME
        if not config_path.is_file():
            return Config()

    try:
        with config_path.open("rb") as fh:
            raw = tomllib.load(fh)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {config_path}: {exc}") from exc

    cfg = Config()
    if "preset" in raw:
        cfg.preset = raw["preset"] or None
    if "extra_terms" in raw:
        cfg.extra_terms = [str(t) for t in raw["extra_terms"]]
    if "user_facing" in raw:
        cfg.user_facing = [str(p) for p in raw["user_facing"]]
    if "diff_base" in raw:
        cfg.diff_base = str(raw["diff_base"])
    for key, value in raw.get("exclusions", {}).items():
        if hasattr(cfg.exclusions, key):
            setattr(cfg.exclusions, key, bool(value))
        else:
            raise ConfigError(f"unknown exclusion rule: {key}")
    return cfg


def load_preset(name: str) -> list[str]:
    """Load a term list from a bundled preset name or a path to a TOML file
    with a ``terms`` array."""
    if name.endswith(".toml") or "/" in name or "\\" in name:
        preset_path = Path(name)
        if not preset_path.is_file():
            raise ConfigError(f"preset file not found: {name}")
        data = tomllib.loads(preset_path.read_text(encoding="utf-8"))
    else:
        ref = resources.files("prose_gate").joinpath(f"presets/{name}.toml")
        try:
            data = tomllib.loads(ref.read_text(encoding="utf-8"))
        except FileNotFoundError:
            available = ", ".join(sorted(builtin_presets()))
            raise ConfigError(
                f"unknown preset '{name}' (bundled presets: {available})"
            ) from None
    terms = data.get("terms")
    if not isinstance(terms, list) or not terms:
        raise ConfigError(f"preset '{name}' has no 'terms' array")
    return [str(t) for t in terms]


def builtin_presets() -> list[str]:
    preset_dir = resources.files("prose_gate").joinpath("presets")
    return [
        entry.name.removesuffix(".toml")
        for entry in preset_dir.iterdir()
        if entry.name.endswith(".toml")
    ]


def resolve_terms(cfg: Config) -> list[str]:
    """Combine the preset term list (if any) with per-project extras."""
    terms: list[str] = []
    if cfg.preset:
        terms.extend(load_preset(cfg.preset))
    terms.extend(cfg.extra_terms)
    return terms
