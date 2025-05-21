# cogs/prime.py

import os
import re
import aiohttp
import unicodedata
import asyncpg
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

BASE_URL = "https://cosmos-one-piece-v2.gitbook.io/piraterie/primes-personnel"

# IDs des rôles
ROLE_IDS = {
    "CAPITAINE":       1317851007358734396,
    "VICE_CAPITAINE":  1358079100203569152,
    "COMMANDANT":      1358031308542181382,
    "VICE_COMMANDANT": 1358032259596288093,
    "LIEUTENANT":      1358030829225381908,
    "MEMBRE":          1317850709948891177,
}

# Ordre d'affichage par rôle
ROLE_ORDER = [
    (ROLE_IDS["CAPITAINE"],       "👑", "Capitaine"),
    (ROLE_IDS["VICE_CAPITAINE"],  "⚔️", "Vice-Capitaine"),
    (ROLE_IDS["COMMANDANT"],      "🛡️", "Commandant"),
    (ROLE_IDS["VICE_COMMANDANT"], "🗡️", "Vice-Commandant"),
    (ROLE_IDS["LIEUTENANT"],      "🎖️", "Lieutenant"),
    (ROLE_IDS["MEMBRE"],          "⚓", "Membre d’équipage"),
]

# Flotte → emoji
FLEET_EMOJIS = {
    1371942480316203018: "<:1reflotte:1372158546531324004>",  # Écarlate
    1371942559894736916: "<:2meflotte:1372158586951696455>",  # Azur
}

# Seuils d’aura et emojis
QUOTAS      = {"Puissant": 30_000_000, "Fort": 5_000_000, "Faible": 1_000_000}
EMOJI_FORCE = {"Puissant": "🔥", "Fort": "⚔️", "Faible": "💀"}

# Définition des rangs (nom, prime minimale)
RANKS = [
    ("Empereur Pirate Menace extrême",   3_200_000_000),
    ("SuperNova Très Dangereux",         1_150_000_000),
    ("Pirate de Rang Z Dangereux",         300_000_000),
    ("Pirate de Rang S+ Très Puissant",    200_000_000),
    ("Pirate de Rang S Très Puissant",     150_000_000),
    ("Pirate de Rang A+ Puissant",          60_000_000),
    ("Pirate de Rang A Puissant",           30_000_000),
    ("Pirate de Rang B Fort",               15_000_000),
    ("Pirate de Rang C Fort",                5_000_000),
    ("Pirate de Rang D Faible",              1_000_000),
    ("Pirate de Rang E Faible",                500_000),
    ("Rookie Faible",                             0),
]

def normalize(text: str) -> str:
    txt = unicodedata.normalize("NFD", text).lower()
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9 ]+", "", txt)

def name_matches(dname: str, entry: str) -> bool:
    dn = normalize(dname).split()
    en = normalize(entry).split()
    return all(tok in en for tok in dn)

def get_fleet_emoji(member: discord.Member) -> str:
    for r in member.roles:
        if r.id in FLEET_EMOJIS:
            return FLEET_EMOJIS[r.id]
    return ""

class SuffixModal(Modal, title="Mise à jour de l'URL de primes"):
    suffix = TextInput(label="Fin d'URL", placeholder="e.g. hybjaafrrbnajg", max_length=64)

    def __init__(self, cog: "Prime", message: discord.Message):
        super().__init__()
        self.cog = cog
        self.prime_message = message

    async def on_submit(self, interaction: discord.Interaction):
        new_suffix = self.suffix.value.strip()
        self.cog.prime_url = f"{BASE_URL}/{new_suffix}"
        await self.cog.fetch_and_upsert()
        new_embed = await self.cog.build_embed(interaction.guild)
        await self.prime_message.edit(embed=new_embed, view=self.cog.RefreshView(self.cog))
        await interaction.response.send_message("✅ URL mise à jour et primes actualisées !", ephemeral=True)

class Prime(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot       = bot
        self.db_url    = os.getenv("DATABASE_URL")
        self.pool      = None
        self.prime_url = BASE_URL
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
        # on vide et on remplit avec les nouvelles primes
        async with self.pool.acquire() as conn:
            await conn.execute("TRUNCATE primes")
        async with aiohttp.ClientSession() as sess:
            async with sess.get(self.prime_url) as resp:
                html = await resp.text()

        matches = re.findall(r"([^\-\n\r<>]+?)\s*-\s*([\d,]+)\s*B", html)
        data = [(n.strip(), int(a.replace(",", ""))) for n, a in matches]

        async with self.pool.acquire() as conn:
            await conn.executemany(
                """
                INSERT INTO primes(name, bounty)
                  VALUES($1,$2)
                ON CONFLICT(name) DO UPDATE
                  SET bounty = EXCLUDED.bounty
                """,
                data
            )

    async def get_all_primes(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT name, bounty FROM primes")

    async def find_prime_for(self, display_name: str):
        for r in await self.get_all_primes():
            if name_matches(display_name, r["name"]):
                return r["name"], r["bounty"]
        return None, None

    async def build_embed(self, guild: discord.Guild) -> discord.Embed:
        rows       = await self.get_all_primes()
        primes_raw = {r["name"]: r["bounty"] for r in rows}
        entries    = list(primes_raw.keys())

        embed = discord.Embed(
            title=f"• Équipage : {guild.name} • ⚓",
            color=0x1abc9c
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # Effectif total
        membre_role = guild.get_role(ROLE_IDS["MEMBRE"])
        total = len(membre_role.members) if membre_role else 0
        embed.add_field(name="Effectif total", value=f"{total} membres", inline=False)

        displayed      = set()
        classification = {"Puissant": [], "Fort": [], "Faible": []}

        # Sections par rôle
        for role_id, emoji_role, label in ROLE_ORDER:
            role = guild.get_role(role_id)
            if not role:
                continue

            grp = []
            for m in role.members:
                if m.id in displayed:
                    continue
                for e in entries:
                    if name_matches(m.display_name, e):
                        val = primes_raw[e]
                        cat = (
                            "Puissant" if val >= QUOTAS["Puissant"]
                            else "Fort"     if val >= QUOTAS["Fort"]
                            else "Faible"
                        )
                        fleet = get_fleet_emoji(m)
                        grp.append((fleet, m, val, EMOJI_FORCE[cat]))
                        classification[cat].append(f"{fleet}{m.mention}")
                        displayed.add(m.id)
                        break

            grp.sort(key=lambda x: x[2], reverse=True)
            lines = "\n".join(
                f"- {fleet}{member.mention} – 💰 `{val:,} B` – {force}"
                for fleet, member, val, force in grp
            ) or "N/A"
            embed.add_field(name=f"{emoji_role} {label}", value=lines, inline=False)

        # Classification globale (aura)
        aura_lines = []
        for cat in ("Puissant", "Fort", "Faible"):
            em   = EMOJI_FORCE[cat]
            lst  = classification[cat] or ["N/A"]
            aura_lines.append(f"{em} **{cat}** ({len(lst)}) : {' '.join(lst)}")
        embed.add_field(name="📊 Classification Globale", value="\n".join(aura_lines), inline=False)

        # Rangs & Auras
        id_to_bounty = {}
        for m in guild.members:
            for e in entries:
                if name_matches(m.display_name, e):
                    id_to_bounty[m.id] = primes_raw[e]
                    break

        ranks_members = {name: [] for name, _ in RANKS}
        for m in guild.members:
            bounty = id_to_bounty.get(m.id)
            if bounty is None:
                continue
            for name, thresh in RANKS:
                if bounty >= thresh:
                    fleet = get_fleet_emoji(m)
                    ranks_members[name].append(f"{fleet}{m.mention}")
                    break

        rank_lines = []
        for name, _ in RANKS:
            lst = ranks_members[name] or ["N/A"]
            rank_lines.append(f"**{name}** ({len(lst)}) : {' '.join(lst)}")
        embed.add_field(name="🏷️ Rangs & Auras", value="\n".join(rank_lines), inline=False)

        return embed

    @commands.command(name="primes")
    @commands.has_permissions(administrator=True)
    async def primes(self, ctx: commands.Context):
        """!primes — affiche l’embed + 🔁 (admin only)."""
        await ctx.message.delete()
        embed = discord.Embed(
            description="Cliquez sur 🔁 pour saisir la fin de l'URL et actualiser !",
            color=0x3498db
        )
        await ctx.send(embed=embed, view=self.RefreshView(self))

    @commands.command(name="prime")
    @commands.has_role(ROLE_IDS["MEMBRE"])
    async def prime_user(self, ctx: commands.Context):
        """!prime — affiche votre prime personnelle."""
        await ctx.message.delete()
        entry, bounty = await self.find_prime_for(ctx.author.display_name)
        if bounty is None:
            return await ctx.send("❌ Prime introuvable pour votre Nom RP.", ephemeral=True)
        await ctx.send(
            f"📜 **Nom RP :** {entry}\n"
            f"💰 **Prime :** `{bounty:,} B`",
            ephemeral=True
        )

    class RefreshView(View):
        def __init__(self, cog: "Prime"):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label="🔁 Actualiser", style=discord.ButtonStyle.secondary, custom_id="refresh_primes")
        async def refresh(self, interaction: discord.Interaction, button: Button):
            if not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message("🚫 Admins only", ephemeral=True)
            await interaction.response.send_modal(SuffixModal(self.cog, interaction.message))

async def setup(bot: commands.Bot):
    await bot.add_cog(Prime(bot))
