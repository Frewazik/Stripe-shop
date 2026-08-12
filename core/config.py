from functools import lru_cache

from pydantic import Field, PostgresDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class UnsupportedCurrencyError(KeyError):
    def __init__(self, currency: str) -> None:
        super().__init__(f"No Stripe credentials configured for currency: {currency!r}")


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    secret_key: str
    debug: bool = False
    allowed_hosts: list[str] = Field(default_factory=lambda: ["localhost", "127.0.0.1"])
    csrf_trusted_origins: list[str] = Field(default_factory=list)

    database_url: PostgresDsn

    stripe_keys: dict[str, str] = Field(default_factory=dict)
    stripe_pub_keys: dict[str, str] = Field(default_factory=dict)
    stripe_webhook_secrets: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _validate_stripe_currency_parity(self) -> "Settings":
        # Валюта продаётся, только если есть и secret, и publishable, и webhook-секрет.
        # Под каждую валюту свой аккаунт Stripe (свой webhook-секрет), поэтому
        # полуготовая валюта должна падать на старте, а не на оплате
        currencies = set(self.stripe_keys)
        for label, mapping in (
            ("pub", self.stripe_pub_keys),
            ("webhook", self.stripe_webhook_secrets),
        ):
            if set(mapping) != currencies:
                raise ValueError(
                    f"Stripe {label} currency mismatch: "
                    f"{sorted(set(mapping) ^ currencies)}"
                )
        return self

    def stripe_secret_for(self, currency: str) -> str:
        try:
            return self.stripe_keys[currency.lower()]
        except KeyError as exc:
            raise UnsupportedCurrencyError(currency) from exc

    def stripe_pub_for(self, currency: str) -> str:
        try:
            return self.stripe_pub_keys[currency.lower()]
        except KeyError as exc:
            raise UnsupportedCurrencyError(currency) from exc

    def stripe_webhook_secret_for(self, currency: str) -> str:
        try:
            return self.stripe_webhook_secrets[currency.lower()]
        except KeyError as exc:
            raise UnsupportedCurrencyError(currency) from exc


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]
