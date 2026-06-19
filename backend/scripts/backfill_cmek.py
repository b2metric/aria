import asyncio
import os
import uuid
import sys
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.app.services.crypto import AppKEKProvider
from backend.app.core.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Fetch all customers
        res = await session.execute(text("SELECT id, slug FROM customers"))
        customers = res.fetchall()
        print(f"Found {len(customers)} customers.")

        for cust in customers:
            cust_id, slug = cust
            print(f"Processing customer: {slug} ({cust_id})")

            # Check if key config already exists
            res_key = await session.execute(
                text("SELECT id FROM customer_key_configs WHERE customer_id = :cid"),
                {"cid": cust_id}
            )
            existing = res_key.scalar_one_or_none()
            if existing:
                print(f"  -> CMEK config already exists for {slug}. Skipping.")
                continue

            # Create a random 32-byte DEK
            raw_dek = os.urandom(32)
            
            # Wrap DEK using AppKEKProvider
            encrypted_dek = AppKEKProvider.wrap_dek(raw_dek)
            
            new_id = uuid.uuid4()
            await session.execute(
                text("INSERT INTO customer_key_configs (id, customer_id, provider, encrypted_dek, is_active) VALUES (:id, :cid, 'app', :edek, true)"),
                {"id": str(new_id), "cid": cust_id, "edek": encrypted_dek}
            )
            print(f"  -> Created new CMEK AppKEK config for {slug}.")

        await session.commit()
        print("Backfill completed.")

if __name__ == "__main__":
    asyncio.run(main())
