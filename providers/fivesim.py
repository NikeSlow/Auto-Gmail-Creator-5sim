from __future__ import annotations

import re
import time
from typing import Any, Optional

import requests

from providers.sms_base import SmsConfig, SmsProvider


class FiveSimError(Exception):
    pass


class FiveSimProvider(SmsProvider):
    def __init__(
        self,
        config: SmsConfig,
        session: Optional[requests.Session] = None,
    ):
        self.config = config
        self.session = session or requests.Session()
        self._order_id: Optional[int] = None

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.config.api_token}",
            "Accept": "application/json",
        }

    def _url(self, path: str) -> str:
        base = self.config.base_url.rstrip("/")
        return f"{base}{path}"

    def profile(self) -> dict[str, Any]:
        r = self.session.get(
            self._url("/user/profile"),
            headers=self._headers(),
            timeout=60,
        )
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            raise FiveSimError(f"profile HTTP {r.status_code}: {r.text}") from e
        return r.json()

    def guest_products(self, country: str, operator: str) -> dict[str, Any]:
        r = self.session.get(
            self._url(f"/guest/products/{country}/{operator}"),
            headers={"Accept": "application/json"},
            timeout=60,
        )
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            raise FiveSimError(
                f"guest/products HTTP {r.status_code}: {r.text}"
            ) from e
        return r.json()

    def buy_number(self, max_retries: int, retry_wait: float) -> tuple[str, int]:
        if not self.config.api_token:
            raise FiveSimError("Missing 5sim API token")

        country = self.config.country.strip("/")
        operator = self.config.operator.strip("/")
        product = self.config.product.strip("/")
        path = f"/user/buy/activation/{country}/{operator}/{product}"
        last_msg: Any = None

        for attempt in range(max_retries):
            r = self.session.get(
                self._url(path),
                headers=self._headers(),
                timeout=90,
            )
            if r.status_code == 200:
                try:
                    data = r.json()
                except ValueError as e:
                    raise FiveSimError(f"buy: invalid JSON: {r.text[:500]}") from e
                order_id = int(data["id"])
                phone = _normalize_e164(str(data.get("phone", "")))
                self._order_id = order_id
                return phone, order_id

            last_msg = r.text
            if r.status_code == 401:
                raise FiveSimError(f"buy unauthorized: {r.text}")
            time.sleep(retry_wait)

        raise FiveSimError(
            f"buy failed after {max_retries} tries (last HTTP body): {last_msg}"
        )

    def check_order(self, order_id: int) -> dict[str, Any]:
        r = self.session.get(
            self._url(f"/user/check/{order_id}"),
            headers=self._headers(),
            timeout=60,
        )
        try:
            r.raise_for_status()
        except requests.HTTPError as e:
            raise FiveSimError(f"check HTTP {r.status_code}: {r.text}") from e
        return r.json()

    def wait_for_code(
        self,
        order_id: int,
        timeout_s: float = 300.0,
        poll_interval: float = 5.0,
    ) -> str:
        deadline = time.time() + timeout_s
        code_re = re.compile(r"\b(\d{4,8})\b")

        while time.time() < deadline:
            data = self.check_order(order_id)
            sms_list = data.get("sms") or []
            for sms in reversed(sms_list):
                code = sms.get("code")
                if code is not None and str(code).strip().isdigit():
                    return str(code).strip()
                text = str(sms.get("text") or "")
                m = code_re.search(text)
                if m:
                    return m.group(1)
            time.sleep(poll_interval)

        raise FiveSimError("Timeout waiting for SMS code")

    def finish_ok(self, order_id: int) -> None:
        r = self.session.get(
            self._url(f"/user/finish/{order_id}"),
            headers=self._headers(),
            timeout=60,
        )
        if r.status_code not in (200, 204) and not (
            r.status_code == 400 and "already" in r.text.lower()
        ):
            try:
                r.raise_for_status()
            except requests.HTTPError as e:
                raise FiveSimError(f"finish HTTP {r.status_code}: {r.text}") from e

    def cancel_order(self, order_id: int) -> None:
        r = self.session.get(
            self._url(f"/user/cancel/{order_id}"),
            headers=self._headers(),
            timeout=60,
        )
        if r.status_code not in (200, 204, 400):
            try:
                r.raise_for_status()
            except requests.HTTPError:
                pass


def _normalize_e164(phone: str) -> str:
    p = phone.strip()
    if not p:
        return p
    if p.startswith("+"):
        return "+" + p[1:].replace(" ", "")
    digits = re.sub(r"\D", "", p)
    return f"+{digits}"
