from unittest.mock import Mock
from django.test import SimpleTestCase
from apps.ixc_integration.clients.ixc_client import IXCClient

class IXCClientTests(SimpleTestCase):
    def test_list_records_normalizes_ixc_payload(self):
        client=IXCClient("https://ixc.local","token")
        response=Mock(ok=True,status_code=200)
        response.json.return_value={"registros":[{"id":"1"}],"total":"1"}
        client.session.request=Mock(return_value=response)
        result=client.list_records("cliente",per_page=1)
        self.assertEqual(result.total,1)
        self.assertEqual(result.records[0]["id"],"1")
