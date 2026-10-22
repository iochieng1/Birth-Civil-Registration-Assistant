import io
import json

from crs_assistant import sms


def test_console_gateway_collects_messages():
    gateway = sms.ConsoleGateway()
    assert gateway.send("+254712345678", "hello")
    assert gateway.outbox == [("+254712345678", "hello")]


def test_from_env_defaults_to_console(monkeypatch):
    monkeypatch.delenv("AT_USERNAME", raising=False)
    monkeypatch.delenv("AT_API_KEY", raising=False)
    assert isinstance(sms.from_env(), sms.ConsoleGateway)


def test_from_env_uses_africas_talking_sandbox(monkeypatch):
    monkeypatch.setenv("AT_USERNAME", "sandbox")
    monkeypatch.setenv("AT_API_KEY", "key")
    gateway = sms.from_env()
    assert isinstance(gateway, sms.AfricasTalkingGateway)
    assert "sandbox" in gateway.url


class FakeResponse(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_africas_talking_send_parses_success(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["headers"] = dict(request.header_items())
        captured["body"] = request.data.decode()
        body = {"SMSMessageData": {"Recipients": [{"status": "Success"}]}}
        return FakeResponse(json.dumps(body).encode())

    monkeypatch.setattr(sms.urllib.request, "urlopen", fake_urlopen)
    gateway = sms.AfricasTalkingGateway("user", "secret", sender_id="CRS")
    assert gateway.send("+254712345678", "hi there")
    assert captured["headers"]["Apikey"] == "secret"
    assert "from=CRS" in captured["body"]


def test_africas_talking_send_handles_network_error(monkeypatch):
    def boom(request, timeout):
        raise OSError("down")

    monkeypatch.setattr(sms.urllib.request, "urlopen", boom)
    assert not sms.AfricasTalkingGateway("user", "secret").send("+254712345678", "hi")
