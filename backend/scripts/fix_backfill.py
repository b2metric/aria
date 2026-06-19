import asyncio
import os
import sys

from cryptography.fernet import Fernet
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.app.core.config import get_settings
from backend.app.services.crypto import AppKEKProvider


async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Fetch all customers
        res = await session.execute(text("SELECT id, slug FROM customers"))
        customers = res.fetchall()

        for cust in customers:
            cust_id, slug = cust

            # Re-generate a valid Fernet key
            raw_dek = Fernet.generate_key()
            encrypted_dek = AppKEKProvider.wrap_dek(raw_dek)

            await session.execute(
                text(
                    "UPDATE customer_key_configs SET encrypted_dek = :edek WHERE customer_id = :cid"
                ),
                {"cid": cust_id, "edek": encrypted_dek},
            )

        await session.commit()
        print("Backfill fixed.")


if __name__ == "__main__":
    asyncio.run(main())
