import unittest
from unittest.mock import MagicMock

from providers.fivesim import FiveSimProvider
from providers.sms_base import SmsConfig


class TestFiveSimProvider(unittest.TestCase):
    def test_buy_and_wait_for_code(self) -> None:
        cfg = SmsConfig(api_token="test", country="a", operator="b", product="c")
        prov = FiveSimProvider(cfg)
        mock_session = MagicMock()

        def fake_get(url: str, **_kwargs):
            resp = MagicMock()
            if "/buy/activation/" in url:
                resp.status_code = 200
                resp.json.return_value = {"id": 99, "phone": "79001234567"}
            elif "/check/" in url:
                resp.status_code = 200
                resp.json.return_value = {
                    "sms": [{"code": "654321", "text": "Your code 654321"}]
                }
            else:
                resp.status_code = 200
                resp.text = ""
            resp.raise_for_status = lambda: None
            return resp

        mock_session.get.side_effect = fake_get
        prov.session = mock_session

        phone, oid = prov.buy_number(max_retries=1, retry_wait=0.01)
        self.assertEqual(oid, 99)
        self.assertEqual(phone, "+79001234567")
        code = prov.wait_for_code(oid, timeout_s=2.0, poll_interval=0.01)
        self.assertEqual(code, "654321")


if __name__ == "__main__":
    unittest.main()
