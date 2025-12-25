from pydantic import Field, RedisDsn, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from chicory.types import ValidationMode


class BrokerConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="CHICORY_BROKER_"
    )

    redis_host: str | None = Field(default=None, alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=0, alias="REDIS_DB")
    redis_user: str | None = Field(default=None, alias="REDIS_USER")
    redis_password: SecretStr | None = Field(default=None, alias="REDIS_PASSWORD")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")

    @property
    def redis_dsn(self) -> str | None:
        if self.redis_url:
            return RedisDsn(self.redis_url).encoded_string()
        if self.redis_host:
            return RedisDsn.build(
                scheme="redis",
                username=self.redis_user,
                password=self.redis_password.get_secret_value()
                if self.redis_password
                else None,
                host=self.redis_host,
                port=self.redis_port,
                path=str(self.redis_db),
            ).encoded_string()
        return None


class BackendConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="CHICORY_BACKEND_"
    )

    redis_host: str | None = Field(default=None, alias="REDIS_HOST")
    redis_port: int = Field(default=6379, alias="REDIS_PORT")
    redis_db: int = Field(default=1, alias="REDIS_DB")
    redis_user: str | None = Field(default=None, alias="REDIS_USER")
    redis_password: SecretStr | None = Field(default=None, alias="REDIS_PASSWORD")
    redis_url: str | None = Field(default=None, alias="REDIS_URL")

    @property
    def redis_dsn(self) -> str | None:
        if self.redis_url:
            return RedisDsn(self.redis_url).encoded_string()
        if self.redis_host:
            return RedisDsn.build(
                scheme="redis",
                username=self.redis_user,
                password=self.redis_password.get_secret_value()
                if self.redis_password
                else None,
                host=self.redis_host,
                port=self.redis_port,
                path=str(self.redis_db),
            ).encoded_string()
        return None


class ChicoryConfig(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", env_prefix="CHICORY_"
    )

    broker: BrokerConfig = BrokerConfig()
    backend: BackendConfig = BackendConfig()
    validation_mode: ValidationMode = Field(
        default=ValidationMode.INPUTS, alias="VALIDATION_MODE"
    )
