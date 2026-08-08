"""Core configuration models for AIOps Agent."""

from __future__ import annotations

from enum import Enum
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, SecretStr


class LLMProvider(str, Enum):
    """Supported LLM providers."""

    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    DEEPSEEK = "deepseek"


class ServerConfig(BaseModel):
    """Configuration for a single managed server."""

    name: str = Field(..., description="Human-readable server name")
    host: str = Field(..., description="IP address or hostname")
    port: int = Field(22, ge=1, le=65535)
    username: str = Field("aiops", description="SSH username")
    ssh_key_path: Path | None = Field(None, description="Path to SSH private key")
    ssh_key_passphrase: SecretStr | None = Field(None, description="SSH key passphrase")
    environment: Literal["staging", "production"] = "staging"
    metadata: dict = Field(default_factory=dict, description="Arbitrary server metadata")

    @property
    def display_name(self) -> str:
        return f"{self.name} ({self.host}) [{self.environment}]"


class LLMConfig(BaseModel):
    """Configuration for the LLM backend."""

    provider: LLMProvider = LLMProvider.OPENAI
    model: str = "gpt-4o"
    api_key: SecretStr | None = None
    base_url: str | None = None
    temperature: float = Field(0.1, ge=0.0, le=2.0)
    max_tokens: int = 4096


class ToolPermission(BaseModel):
    """Permission rule for sudo access on a tool."""

    command: str
    args_allowed: list[str] = Field(default_factory=list)
    require_approval: bool = False


class TelegramConfig(BaseModel):
    """Telegram Bot configuration."""

    enabled: bool = False
    token_env: str = "TELEGRAM_BOT_TOKEN"
    allowed_users: list[int] = Field(default_factory=list, description="Telegram user IDs (empty = allow all)")
    webhook: bool = False
    webhook_url: str = ""
    webhook_port: int = Field(8443, ge=1, le=65535)


class SecurityConfig(BaseModel):
    """Security configuration."""

    allowed_sudo_commands: list[ToolPermission] = Field(default_factory=list)
    forbidden_commands: list[str] = Field(
        default_factory=lambda: [
            "rm -rf /",
            "shutdown",
            "reboot",
            "userdel",
            "passwd",
            "iptables",
            "ufw reset",
            "mkfs",
            "dd if=",
            "> /dev/sda",
        ]
    )
    require_approval_for_all: bool = Field(
        False, description="Require human approval for every write operation"
    )


class AppConfig(BaseModel):
    """Top-level application configuration."""

    servers: list[ServerConfig] = Field(default_factory=list)
    llm: LLMConfig = Field(default_factory=LLMConfig)
    security: SecurityConfig = Field(default_factory=SecurityConfig)
    audit_log_path: Path = Field(Path("./logs/audit.log"))
    memory_path: Path = Field(Path("./memory"))
    playbooks_path: Path = Field(Path("./playbooks"))
    default_server: str | None = None

    @classmethod
    def from_yaml(cls, path: Path) -> "AppConfig":
        """Load configuration from a YAML file."""
        import yaml

        data = yaml.safe_load(path.read_text())
        return cls.model_validate(data)

    @classmethod
    def from_yaml_with_env(cls, path: Path) -> "AppConfig":
        """Load config from YAML, then override LLM fields with env vars (higher priority)."""
        import os

        import yaml

        data = yaml.safe_load(path.read_text())
        config = cls.model_validate(data)

        # LLM env var overrides — env vars take priority over config.yaml
        env_overrides = {
            "AIOPS_LLM_PROVIDER": ("provider", None),
            "AIOPS_LLM_MODEL": ("model", None),
            "AIOPS_LLM_BASE_URL": ("base_url", None),
            "AIOPS_LLM_TEMPERATURE": ("temperature", float),
            "AIOPS_LLM_MAX_TOKENS": ("max_tokens", int),
        }
        for env_var, (field_name, cast) in env_overrides.items():
            value = os.getenv(env_var)
            if value is not None:
                if cast is not None:
                    value = cast(value)
                setattr(config.llm, field_name, value)

        # Separate env var for API key (SecretStr)
        api_key = os.getenv("AIOPS_LLM_API_KEY") or os.getenv("OPENAI_API_KEY")
        if api_key:
            from pydantic import SecretStr

            config.llm.api_key = SecretStr(api_key)

        return config

    def get_server(self, name: str) -> ServerConfig:
        """Get a server by name, falling back to default_server."""
        for s in self.servers:
            if s.name == name:
                return s
        if self.default_server:
            for s in self.servers:
                if s.name == self.default_server:
                    return s
        raise KeyError(f"Server '{name}' not found and no default configured")