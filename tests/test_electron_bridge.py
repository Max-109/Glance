import unittest
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from src.ui.electron_bridge import (
    BRIDGE_TOKEN_HEADER,
    SettingsBridgeServer,
    _allowed_cors_origin,
    _bridge_token_matches,
)


class FakeSignal:
    def connect(self, callback) -> None:
        del callback


class FakeViewModel:
    def __init__(self) -> None:
        for name in (
            "settingsChanged",
            "savedSettingsChanged",
            "errorsChanged",
            "dirtyChanged",
            "savingChanged",
            "statusChanged",
            "audioDevicesChanged",
            "audioTestChanged",
            "currentSectionChanged",
            "bindingChanged",
            "previewChanged",
            "memoriesChanged",
        ):
            setattr(self, name, FakeSignal())


class SettingsBridgeSecurityTests(unittest.TestCase):
    def test_bridge_token_matching_rejects_missing_or_wrong_token(self) -> None:
        self.assertTrue(_bridge_token_matches("secret", "secret"))
        self.assertFalse(_bridge_token_matches("", "secret"))
        self.assertFalse(_bridge_token_matches("wrong", "secret"))

    def test_cors_origin_is_limited_to_local_renderer_origins(self) -> None:
        self.assertEqual(
            _allowed_cors_origin("http://127.0.0.1:3000"),
            "http://127.0.0.1:3000",
        )
        self.assertEqual(
            _allowed_cors_origin("http://localhost:3000"),
            "http://localhost:3000",
        )
        self.assertEqual(_allowed_cors_origin("https://example.com"), "")

    def test_bridge_rejects_requests_without_token(self) -> None:
        bridge = SettingsBridgeServer(FakeViewModel(), bridge_token="secret")
        try:
            request = Request(f"{bridge.url}/api/state", method="GET")
            with self.assertRaises(HTTPError) as error:
                urlopen(request, timeout=2)
            error.exception.close()
        finally:
            bridge.close()

        self.assertEqual(error.exception.code, 403)

    def test_options_allows_token_header_for_local_renderer_origin(self) -> None:
        bridge = SettingsBridgeServer(FakeViewModel(), bridge_token="secret")
        try:
            request = Request(
                f"{bridge.url}/api/state",
                method="OPTIONS",
                headers={
                    "Origin": "http://127.0.0.1:3000",
                    "Access-Control-Request-Headers": BRIDGE_TOKEN_HEADER,
                },
            )
            with urlopen(request, timeout=2) as response:
                self.assertEqual(response.status, 204)
                self.assertEqual(
                    response.headers.get("Access-Control-Allow-Origin"),
                    "http://127.0.0.1:3000",
                )
                self.assertIn(
                    BRIDGE_TOKEN_HEADER,
                    response.headers.get("Access-Control-Allow-Headers", ""),
                )
        finally:
            bridge.close()


if __name__ == "__main__":
    unittest.main()
