from pathlib import Path

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


BASE_DIR = Path(__file__).resolve().parents[1]


class Settings(BaseSettings):
    hf_api_key: str = Field(
        default="",
        validation_alias=AliasChoices("HF_API_KEY", "HUGGINGFACE_API_KEY"),
    )
    hf_model: str = Field(
        default="HuggingFaceH4/zephyr-7b-beta",
        validation_alias=AliasChoices("HF_MODEL", "HUGGINGFACE_MODEL"),
    )
    hf_timeout_seconds: int = Field(
        default=60,
        validation_alias=AliasChoices("HF_TIMEOUT_SECONDS", "HUGGINGFACE_TIMEOUT_SECONDS"),
    )
    hf_structured_retries: int = Field(
        default=2,
        validation_alias=AliasChoices("HF_STRUCTURED_RETRIES", "HUGGINGFACE_STRUCTURED_RETRIES"),
    )
    pipeline_mode: str = "ast"
    enable_repair_loop: bool = True
    max_repair_attempts: int = 2
    lean_command: str = "lean"
    lean_timeout_seconds: int = 60
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:5175,http://127.0.0.1:5175"
    port: int = 8001
    telemetry_file: Path = BASE_DIR / "data" / "telemetry.jsonl"
    knowledge_base_file: Path = BASE_DIR / "data" / "knowledge_base.json"
    evaluation_output_dir: Path = BASE_DIR / "data" / "evaluation"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origin_list(self) -> list[str]:
        return [
            origin.strip()
            for origin in self.cors_origins.split(",")
            if origin.strip()
        ]


settings = Settings()
