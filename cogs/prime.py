# cogs/prime.py

import os
import re
import unicodedata
import aiohttp
import asyncpg
import discord
from discord.ext import commands
from discord.ui import View, Button

PRIME_URL = "https://cosmos-one-piece-v2.gitbook.io/piraterie/primes-personnel/gvednstndtrsdd"

# … (ROLE_IDS, ROLE_ORDER, FLEET_EMOJIS, QUOTAS, EMOJI_FORCE, normalize(), name_matches(), get_fleet_emoji() inchangés)

class Prime(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot    = bot
        self.db_url = os.getenv("DATABASE_URL")
        self.pool   = None
        bot.add_view(self.RefreshView(self))

    async def cog_load(self):
        self.pool = await asyncpg.create_pool(self.db_url)
        async with self.pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS primes (
                    name TEXT PRIMARY KEY,
                    bounty BIGINT
                )
            """)

    async def cog_unload(self):
        await self.pool.close()

    async def fetch_and_upsert(self):
        """Scrape la page GitBook standard et upserte toutes les primes."""
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(PRIME_URL) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status} en GET {PRIME_URL}")
                html = await resp.text()

        # Regex qui capture "Nom – 12,345,678 B" ou "Nom - 12,345,678 B"
        pattern = re.compile(r"([^\-<>\r\n]+?)\s*[–-]\s*([\d,]+)\s*B")
        data = []
        for name, bounty in pattern.findall(html):
            clean_name   = name.strip()
            clean_bounty = int(bounty.replace(",", ""))
            data.append((clean_name, clean_bounty))

        if not data:
            raise RuntimeError("Aucune prime trouvée dans le HTML brut")

        # Upsert en base (jamais de DELETE)
        async with self.pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO primes(name, bounty)
                VALUES($1, $2)
                ON CONFLICT (name) DO UPDATE
                  SET bounty = EXCLUDED.bounty
                """,
                data
            )

    # … (get_all_primes, find_prime_for, build_embed, prime_user identiques)

    @commands.command(name="primes")
    @commands.has_permissions(administrator=True)
    async def primes(self, ctx: commands.Context):
        await ctx.message.delete()
        loading = await ctx.send("⏳ Mise à jour des primes…")
        try:
            await self.fetch_and_upsert()
            embed = await self.build_embed(ctx.guild)
            await loading.delete()
            await ctx.send(embed=embed, view=self.RefreshView(self))
        except Exception as e:
            await loading.edit(content=f"❌ Échec mise à jour : {e}")

    class RefreshView(View):
        def __init__(self, cog: "Prime"):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label="🔁 Actualiser", style=discord.ButtonStyle.secondary, custom_id="refresh_primes")
        async def refresh(self, interaction: discord.Interaction, button: Button):
            if not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message("🚫 Réservé aux administrateurs.", ephemeral=True)

            loading = await interaction.response.send_message("⏳ Actualisation…", ephemeral=True)
            try:
                await self.cog.fetch_and_upsert()
                new_embed = await self.cog.build_embed(interaction.guild)
                await interaction.message.edit(embed=new_embed, view=self)
                await interaction.followup.edit_message(loading.id, content="✅ Primes actualisées.")
            except Exception as e:
                await interaction.followup.edit_message(loading.id, content=f"❌ Erreur : {e}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Prime(bot))
