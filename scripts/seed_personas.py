"""Standalone script to seed persona data into the database."""

import asyncio
import sys
sys.path.insert(0, ".")

from config import Config
from db.connection import init_db, async_session
from db.models import Persona
from personas.definitions import PERSONAS


async def seed():
    await init_db()

    async with async_session() as session:
        for p_data in PERSONAS:
            existing = await session.execute(
                Persona.__table__.select().where(Persona.slug == p_data["slug"])
            )
            if existing.first():
                print(f"  Persona '{p_data['slug']}' already exists, skipping")
                continue

            persona = Persona(
                slug=p_data["slug"],
                display_name=p_data["display_name"],
                bot_token=Config.PERSONA_TOKENS.get(p_data["slug"], ""),
                bio=p_data["bio"],
                personality=p_data["personality"],
                fitness_baseline=p_data["fitness_baseline"],
                posting_window=p_data["posting_window"],
                emoji_style=p_data["emoji_style"],
                slang_notes=p_data["slang_notes"],
                motivation_style=p_data["motivation_style"],
                profile_photo_path=p_data["profile_photo_path"],
            )
            session.add(persona)
            print(f"  + Added persona: {p_data['display_name']} ({p_data['slug']})")

        await session.commit()
        print("\nDone! All personas seeded.")


if __name__ == "__main__":
    asyncio.run(seed())
