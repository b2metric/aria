import logging
import uuid

from sqlalchemy.dialects.postgresql import insert

from backend.app.auth.models import UserContext
from backend.app.db.session import get_sessionmaker
from backend.app.models.organization import Customer, Team, User

logger = logging.getLogger(__name__)


async def sync_user_from_token(user_ctx: UserContext):
    """
    Syncs the Keycloak user and team into the local PostgreSQL database.
    This ensures foreign key constraints (queries, tokens, etc.) don't fail
    if the user was created directly in Keycloak rather than through the ARIA Admin UI.
    """
    if not user_ctx.sub:
        return

    maker = get_sessionmaker()
    try:
        async with maker() as db:
            # Upsert Team if team_id is present
            if user_ctx.team_id:
                try:
                    team_uuid = uuid.UUID(user_ctx.team_id)
                    team_stmt = (
                        insert(Team)
                        .values(
                            id=team_uuid,
                            customer_id=uuid.UUID(user_ctx.workspace_id)
                            if user_ctx.workspace_id != "default"
                            else None,  # We need a valid customer ID if possible
                            name=f"Team {user_ctx.team_id[:8]}",  # Best effort name if created outside
                        )
                        .on_conflict_do_nothing(index_elements=["id"])
                    )

                    # Try to execute, but if customer_id constraint fails, we'll catch it
                    await db.execute(team_stmt)
                    await db.commit()
                except Exception as e:
                    logger.debug(
                        f"Could not upsert team from token (might lack customer mapping): {e}"
                    )
                    await db.rollback()

            # We need to find the customer ID for the user
            customer_id = None
            if user_ctx.workspace_id:
                from sqlalchemy import select

                try:
                    cust_uuid = uuid.UUID(user_ctx.workspace_id)
                    customer_id = cust_uuid
                except ValueError:
                    # It's a slug
                    res = await db.execute(
                        select(Customer.id).where(Customer.slug == user_ctx.workspace_id)
                    )
                    customer_id = res.scalar_one_or_none()

            if not customer_id:
                return  # Can't sync user without a customer_id

            # Upsert User
            try:
                user_uuid = uuid.UUID(user_ctx.sub)

                stmt = insert(User).values(
                    id=user_uuid,
                    external_id=user_ctx.sub,
                    customer_id=customer_id,
                    email=user_ctx.email or f"{user_ctx.sub}@unknown.com",
                    display_name=user_ctx.name or user_ctx.preferred_username or "Unknown",
                    role=user_ctx.role.value if user_ctx.role else "member",
                    team_id=uuid.UUID(user_ctx.team_id) if user_ctx.team_id else None,
                    is_active=True,
                )

                # Update if exists
                stmt = stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "email": stmt.excluded.email,
                        "display_name": stmt.excluded.display_name,
                        "role": stmt.excluded.role,
                        "team_id": stmt.excluded.team_id,
                    },
                )

                await db.execute(stmt)
                await db.commit()
            except Exception as e:
                logger.error(f"Failed to sync user from token: {e}")
                await db.rollback()
    except Exception as e:
        logger.error(f"DB session failed during user sync: {e}")
