from django.db import models
from cryptography.fernet import Fernet

# Replace the placeholder key with the generated Fernet key
SECRET_KEY = b'PbLQDFHVrSbvRkUh1lSIkdZyk3oska7sZ_nrsNyUwio='
cipher_suite = Fernet(SECRET_KEY)

# Create your models here.

class Franchise(models.Model):
    # ...existing fields...

    def set_password(self, raw_password):
        """Encrypt and set the password."""
        encrypted_password = cipher_suite.encrypt(raw_password.encode())
        self.password = encrypted_password.decode()

    def get_password(self):
        """Decrypt and return the password."""
        return cipher_suite.decrypt(self.password.encode()).decode()
