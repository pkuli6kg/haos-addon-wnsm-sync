"""Unit tests for WNSMApiClient."""

import sys
from datetime import date, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

from wnsm_sync.api.client import WNSMApiClient
from wnsm_sync.api.errors import AuthenticationError, WNSMApiError


FAKE_TOKEN_RESPONSE = {"access_token": "test-token-abc123", "token_type": "Bearer"}


def make_client(use_mock=False):
    return WNSMApiClient(
        client_id="test-client",
        client_secret="test-secret",
        api_key="test-api-key",
        use_mock=use_mock,
    )


# ------------------------------------------------------------------
# Authentication
# ------------------------------------------------------------------


@patch("requests.Session.post")
def test_authenticate_success(mock_post):
    resp = MagicMock()
    resp.json.return_value = FAKE_TOKEN_RESPONSE
    resp.raise_for_status.return_value = None
    mock_post.return_value = resp

    client = make_client()
    client.authenticate()

    assert client.is_authenticated()
    assert client._access_token == "test-token-abc123"


@patch("requests.Session.post")
def test_authenticate_missing_token(mock_post):
    resp = MagicMock()
    resp.json.return_value = {}  # no access_token
    resp.raise_for_status.return_value = None
    mock_post.return_value = resp

    client = make_client()
    with pytest.raises(AuthenticationError):
        client.authenticate()


@patch("requests.Session.post")
def test_authenticate_http_error(mock_post):
    import requests

    resp = MagicMock()
    resp.status_code = 401
    http_err = requests.HTTPError(response=resp)
    resp.raise_for_status.side_effect = http_err
    mock_post.return_value = resp

    client = make_client()
    with pytest.raises(AuthenticationError):
        client.authenticate()


# ------------------------------------------------------------------
# get_consumption – mock mode
# ------------------------------------------------------------------


def test_get_consumption_mock_returns_structure():
    client = make_client(use_mock=True)
    today = date.today()
    result = client.get_consumption("AT001", today - timedelta(days=1), today)

    assert "zaehlpunkt" in result
    assert "zaehlwerke" in result
    zw = result["zaehlwerke"]
    assert isinstance(zw, list) and len(zw) > 0
    messwerte = zw[0]["messwerte"]
    assert isinstance(messwerte, list) and len(messwerte) > 0

    first = messwerte[0]
    assert "zeitVon" in first
    assert "messwert" in first
    assert "qualitaet" in first


def test_get_consumption_mock_values_are_wh():
    """Mock data should return Wh values (> 0)."""
    client = make_client(use_mock=True)
    today = date.today()
    result = client.get_consumption("AT001", today - timedelta(days=1), today)
    messwerte = result["zaehlwerke"][0]["messwerte"]
    for m in messwerte:
        assert m["messwert"] > 0


# ------------------------------------------------------------------
# get_consumption – real mode (mocked HTTP)
# ------------------------------------------------------------------


@patch("requests.Session.request")
def test_get_consumption_real_calls_correct_url(mock_request):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = {"zaehlpunkt": "AT001", "zaehlwerke": []}
    resp.raise_for_status.return_value = None
    mock_request.return_value = resp

    client = make_client()
    client._access_token = "token"  # skip auth

    today = date.today()
    client.get_consumption("AT001", today - timedelta(days=1), today)

    call_url = mock_request.call_args[0][1]
    assert "zaehlpunkte/AT001/messwerte" in call_url


@patch("requests.Session.request")
def test_get_consumption_retries_on_401(mock_request):
    """On 401, the client should re-authenticate and retry."""
    import requests as req_lib

    auth_resp = MagicMock()
    auth_resp.json.return_value = FAKE_TOKEN_RESPONSE
    auth_resp.raise_for_status.return_value = None

    resp_401 = MagicMock()
    resp_401.status_code = 401
    resp_401.raise_for_status.return_value = None  # raise_for_status not called on 401 branch

    resp_ok = MagicMock()
    resp_ok.status_code = 200
    resp_ok.json.return_value = {"zaehlpunkt": "AT001", "zaehlwerke": []}
    resp_ok.raise_for_status.return_value = None

    # First request → 401, second request → 200
    mock_request.side_effect = [resp_401, resp_ok]

    client = make_client()
    client._access_token = "old-token"

    with patch.object(client, "authenticate") as mock_auth:
        mock_auth.return_value = None
        client._access_token = "new-token"

        today = date.today()
        # patch _session.post for the re-auth token fetch
        with patch.object(client._session, "post", return_value=auth_resp):
            result = client.get_consumption("AT001", today - timedelta(days=1), today)

    assert result is not None


# ------------------------------------------------------------------
# get_metering_points
# ------------------------------------------------------------------


@patch("requests.Session.request")
def test_get_metering_points(mock_request):
    resp = MagicMock()
    resp.status_code = 200
    resp.json.return_value = [{"zaehlpunktnummer": "AT001"}]
    resp.raise_for_status.return_value = None
    mock_request.return_value = resp

    client = make_client()
    client._access_token = "token"

    result = client.get_metering_points()
    assert isinstance(result, list)
    assert result[0]["zaehlpunktnummer"] == "AT001"
