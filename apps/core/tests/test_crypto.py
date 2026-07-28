from cryptography.fernet import Fernet
from django.test import SimpleTestCase, override_settings
from apps.core.crypto import SecretCipher
class SecretCipherTests(SimpleTestCase):
    @override_settings(FIELD_ENCRYPTION_KEY=Fernet.generate_key().decode())
    def test_round_trip(self):
        cipher=SecretCipher(); encrypted=cipher.encrypt("segredo")
        self.assertNotEqual(encrypted,"segredo")
        self.assertEqual(cipher.decrypt(encrypted),"segredo")
