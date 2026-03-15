"""Pydantic Settings models for PolicyFoundry configuration.

Provides nested configuration models for LLM, sources, targets, and output
settings. The root PolicyFoundryConfig class uses pydantic-settings to support
YAML file loading and environment variable overrides with a defined merge order.

Merge priority (highest to lowest):
  1. Init kwargs (--config flag or direct instantiation)
  2. Environment variables (POLICYFOUNDRY_ prefix, __ nesting)
  3. Local YAML (.policyfoundry.yaml in CWD)
  4. Global YAML (~/.policyfoundry/config.yaml)
"""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import (
    BaseSettings,
    NoDecode,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)


class LLMConfig(BaseModel):
    """LLM provider configuration."""

    provider: str = "ollama"
    model: str = "llama3.2"
    temperature: float = 0.1
    max_tokens: int = 4096
    base_url: str | None = None
    api_key: str | None = None
    timeout: int = 120


class SourcesConfig(BaseModel):
    """Log source configuration."""

    log_paths: Annotated[list[str], NoDecode] = Field(default_factory=list)
    s3_bucket: str | None = None
    s3_prefix: str | None = None
    aws_profile: str | None = None

    @field_validator("log_paths", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: object) -> object:
        """Parse comma-separated strings into lists."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


class TargetsConfig(BaseModel):
    """Target security group configuration."""

    security_group_ids: Annotated[list[str], NoDecode] = Field(default_factory=list)

    @field_validator("security_group_ids", mode="before")
    @classmethod
    def parse_comma_separated(cls, v: object) -> object:
        """Parse comma-separated strings into lists."""
        if isinstance(v, str):
            return [item.strip() for item in v.split(",") if item.strip()]
        return v


class ExcelConfig(BaseModel):
    """Excel ingestion configuration.

    Controls how Excel traffic exports are parsed. By default, auto-detects
    columns from the first sheet's header row. Override column_mapping when
    auto-detection fails for non-standard column names.
    """

    sheet_name: str | None = None  # default: first sheet
    header_row: int = 1
    column_mapping: dict[str, int] | None = None  # override for detect_columns


class OutputConfig(BaseModel):
    """Output formatting configuration."""

    format: str = "rich"
    data_dir: str = "~/.policyfoundry/data"


class PolicyFoundryConfig(BaseSettings):
    """Root configuration for PolicyFoundry.

    Supports YAML config files, environment variables, and init kwargs
    with a defined merge priority. See module docstring for priority order.
    """

    model_config = SettingsConfigDict(
        env_prefix="POLICYFOUNDRY_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    llm: LLMConfig = Field(default_factory=LLMConfig)
    sources: SourcesConfig = Field(default_factory=SourcesConfig)
    targets: TargetsConfig = Field(default_factory=TargetsConfig)
    output: OutputConfig = Field(default_factory=OutputConfig)
    excel: ExcelConfig = Field(default_factory=ExcelConfig)

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        """Configure source priority: init > env > local YAML > global YAML."""
        sources: list[PydanticBaseSettingsSource] = []

        sources.append(init_settings)

        sources.append(env_settings)

        local_yaml = Path.cwd() / ".policyfoundry.yaml"
        if local_yaml.exists():
            sources.append(
                YamlConfigSettingsSource(settings_cls, yaml_file=local_yaml)
            )

        global_yaml = Path.home() / ".policyfoundry" / "config.yaml"
        if global_yaml.exists():
            sources.append(
                YamlConfigSettingsSource(settings_cls, yaml_file=global_yaml)
            )

        return tuple(sources)
