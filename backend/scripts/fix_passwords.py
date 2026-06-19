import asyncio
import os
import uuid
import sys
from cryptography.fernet import Fernet
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text

sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))

from backend.app.services.crypto import AppKEKProvider, async_get_fernet_for_customer
from backend.app.core.config import get_settings

async def main():
    settings = get_settings()
    engine = create_async_engine(settings.database_url)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Fetch all DB configs
        res = await session.execute(text("SELECT id, customer_id, encrypted_password FROM customer_db_configs"))
        configs = res.fetchall()

        app_f = AppKEKProvider.get_kek_fernet()

        for config in configs:
            conf_id, cust_id, enc_pwd = config
            
            if enc_pwd.startswith('gAAAAA'):
                try:
                    # Try decrypting with app KEK (which was used previously because DEK failed)
                    plain = app_f.decrypt(enc_pwd.encode()).decode()
                    
                    # Now re-encrypt with the customer's actual DEK
                    cust_f = await async_get_fernet_for_customer(cust_id, session)
                    new_enc_pwd = cust_f.encrypt(plain.encode()).decode()
                    
                    await session.execute(
                        text("UPDATE customer_db_configs SET encrypted_password = :ep WHERE id = :id"),
                        {"ep": new_enc_pwd, "id": conf_id}
                    )
                    print(f"Fixed DB password for config {conf_id}")
                except Exception as e:
                    print(f"Failed to fix DB config {conf_id}: {e}")

        # Fetch all LLM configs
        res = await session.execute(text("SELECT id, customer_id, encrypted_upstream_api_key, encrypted_virtual_key FROM customer_llm_configs"))
        configs = res.fetchall()

        for config in configs:
            conf_id, cust_id, e1, e2 = config
            updates = {}
            cust_f = await async_get_fernet_for_customer(cust_id, session)

            if e1 and e1.startswith('gAAAAA'):
                try:
                    p1 = app_f.decrypt(e1.encode()).decode()
                    updates["e1"] = cust_f.encrypt(p1.encode()).decode()
                except: pass
            if e2 and e2.startswith('gAAAAA'):
                try:
                    p2 = app_f.decrypt(e2.encode()).decode()
                    updates["e2"] = cust_f.encrypt(p2.encode()).decode()
                except: pass

            if updates:
                q = "UPDATE customer_llm_configs SET "
                params = {"id": conf_id}
                if "e1" in updates:
                    q += "encrypted_upstream_api_key = :e1"
                    params["e1"] = updates["e1"]
                if "e2" in updates:
                    if "e1" in updates: q += ", "
                    q += "encrypted_virtual_key = :e2"
                    params["e2"] = updates["e2"]
                q += " WHERE id = :id"
                await session.execute(text(q), params)
                print(f"Fixed LLM config {conf_id}")

        await session.commit()
        print("Passwords fixed.")

if __name__ == "__main__":
    asyncio.run(main())
