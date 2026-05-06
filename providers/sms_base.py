from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Optional


@dataclass
class SmsConfig:
    """5sim.net REST API (https://5sim.net/docs)."""

    api_token: str
    country: str = "netherlands"
    operator: str = "any"
    product: str = "google"
    base_url: str = "https://5sim.net/v1"

    @classmethod
    def from_env(cls) -> SmsConfig:
        token = os.environ.get("FIVESIM_TOKEN", "").strip()
        return cls(
            api_token=token,
            country=os.environ.get("FIVESIM_COUNTRY", "netherlands").strip(),
            operator=os.environ.get("FIVESIM_OPERATOR", "any").strip(),
            product=os.environ.get("FIVESIM_PRODUCT", "google").strip(),
            base_url=os.environ.get("FIVESIM_BASE_URL", "https://5sim.net/v1").strip(),
        )


@dataclass
class BotSettings:
    sms: SmsConfig
    auto_generate_userinfo: bool = True
    auto_generate_number: int = 10
    user_csv_path: str = "User.csv"
    wait: int = 4
    request_max_try: int = 10
    socks_proxy: Optional[str] = None
    headless: bool = False
    include_refer_url: bool = False
    data_dir: str = "./data"


class SmsProvider(ABC):
    """Minimal interface for phone verification used by the Selenium flow."""

    @abstractmethod
    def buy_number(self, max_retries: int, retry_wait: float) -> tuple[str, int]:
        """Return E.164 phone string and provider order id."""

    @abstractmethod
    def wait_for_code(
        self,
        order_id: int,
        timeout_s: float = 300.0,
        poll_interval: float = 5.0,
    ) -> str:
        """Block until an OTP is received or raise."""

    @abstractmethod
    def finish_ok(self, order_id: int) -> None:
        """Mark order completed after successful verification."""

    @abstractmethod
    def cancel_order(self, order_id: int) -> None:
        """Cancel order on failure or abandon."""

    def profile(self) -> Optional[dict]:
        """Optional: balance / profile for GUI smoke test."""
        return None

    def guest_products(self, country: str, operator: str) -> Optional[dict]:
        """Optional: list products/prices without auth."""
        return None
