import base64
from unittest.mock import Mock, patch

from django.test import SimpleTestCase

from apps.ixc_integration.clients.ixc_client import IXCClient


class IXCClientTests(SimpleTestCase):
    def test_normalizes_root_url(self):
        client = IXCClient("https://ixc.example.com", "1:token")

        self.assertEqual(
            client.base_url,
            "https://ixc.example.com/webservice/v1",
        )

    def test_preserves_full_webservice_url(self):
        client = IXCClient(
            "https://ixc.example.com/webservice/v1",
            "1:token",
        )

        self.assertEqual(
            client.base_url,
            "https://ixc.example.com/webservice/v1",
        )

    def test_encodes_token_as_basic_auth(self):
        token = "1:token"
        expected = base64.b64encode(token.encode()).decode()

        client = IXCClient("https://ixc.example.com", token)

        self.assertEqual(
            client.session.headers["Authorization"],
            f"Basic {expected}",
        )

    @patch("requests.Session.request")
    def test_listing_uses_post_and_json_body(self, request_mock):
        response = Mock()
        response.ok = True
        response.status_code = 200
        response.json.return_value = {
            "total": "1",
            "registros": [{"id": "1"}],
        }
        request_mock.return_value = response

        client = IXCClient("https://ixc.example.com", "1:token")
        result = client.list_records(
            "radpop_radio_cliente_fibra",
            field="radpop_radio_cliente_fibra.id",
            operator="=",
            value="1",
        )

        self.assertEqual(result.total, 1)

        request_mock.assert_called_once()
        _, kwargs = request_mock.call_args

        self.assertEqual(kwargs["method"], "POST")
        self.assertEqual(
            kwargs["json"]["qtype"],
            "radpop_radio_cliente_fibra.id",
        )
        self.assertEqual(kwargs["json"]["query"], "1")
        self.assertEqual(kwargs["json"]["oper"], "=")
