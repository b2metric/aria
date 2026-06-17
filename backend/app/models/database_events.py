from sqlalchemy import event
from backend.app.models.database import CustomerDBConfig
from backend.app.services.crypto import encrypt_password

@event.listens_for(CustomerDBConfig, 'before_insert')
@event.listens_for(CustomerDBConfig, 'before_update')
def encrypt_db_password(mapper, connection, target):
    """Encrypt the password before saving to the database."""
    # Only encrypt if it's not already encrypted (naive check, Fernet tokens start with gAAAAA)
    if target.encrypted_password and not target.encrypted_password.startswith('gAAAAA'):
        target.encrypted_password = encrypt_password(target.encrypted_password)
