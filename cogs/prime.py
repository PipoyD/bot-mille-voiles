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

# Hiérarchie des rôles & icônes
ROLE_IDS = {
    "CAPITAINE":       1317851007358734396,
    "VICE_CAPITAINE":  1358079100203569152,
    "COMMANDANT":      1358031308542181382,
    "VICE_COMMANDANT": 1358032259596288093,
    "LIEUTENANT":      1358030829225381908,
    "MEMBRE":          1317850709948891177,
}
ROLE_ORDER = [
    (ROLE_IDS["CAPITAINE"],       "👑", "Capitaine"),
    (ROLE_IDS["VICE_CAPITAINE"],  "⚔️", "Vice-Capitaine"),
    (ROLE_IDS["COMMANDANT"],      "🛡️", "Commandant"),
    (ROLE_IDS["VICE_COMMANDANT"], "🗡️", "Vice-Commandant"),
    (ROLE_IDS["LIEUTENANT"],      "🎖️", "Lieutenant"),
    (ROLE_IDS["MEMBRE"],          "⚓", "Membre d’équipage"),
]

# Flotte → emoji (correctement associées)
FLEET_EMOJIS = {
    1371942480316203018: "<:1reflotte:1372158546531324004>",  # Écarlate
    1371942559894736916: "<:2meflotte:1372158586951696455>",  # Azur
}

# Seuils de classification et emojis
QUOTAS      = {"Puissant": 30_000_000, "Fort": 5_000_000, "Faible": 1_000_000}
EMOJI_FORCE = {"Puissant": "🔥", "Fort": "⚔️", "Faible": "💀"}

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

class SuffixModal(Modal, title="Mettre à jour l'URL de primes"):
    suffix = TextInput(
        label="Fin d'URL",
        placeholder="Ex : hybjaafrrbnajg",
        max_length=64
    )

    def __init__(self, cog: "Prime", message: discord.Message):
        super().__init__()
        self.cog = cog
        self.prime_message = message

    async def on_submit(self, interaction: discord.Interaction):
        # Met à jour le suffix et relance l'upsert
        new_suffix = self.suffix.value.strip()
        self.cog.prime_url = f"{BASE_URL}/{new_suffix}"
        await self.cog.fetch_and_upsert()
        new_embed = await self.cog.build_embed(interaction.guild)

        # Met à jour le message original
        await self.prime_message.edit(embed=new_embed, view=self.cog.RefreshView(self.cog, self.prime_message))
        await interaction.response.send_message("✅ URL mise à jour et primes rafraîchies.", ephemeral=True)

class Prime(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot       = bot
        self.db_url    = os.getenv("DATABASE_URL")
        self.pool      = None
        self.prime_url = BASE_URL  # suffixe ajouté plus tard
        # Enregistre la vue persistante
        bot.add_view(self.RefreshView(self, None))

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
        async with aiohttp.ClientSession() as sess:
            async with sess.get(self.prime_url) as resp:
                html = await resp.text()
        matches = re.findall(r"([^\-\n\r<>]+?)\s*-\s*([\d,]+)\s*B", html)
        data = [(n.strip(), int(a.replace(",", ""))) for n, a in matches]
        async with self.pool.acquire() as conn:
            await conn.executemany("""
                INSERT INTO primes(name, bounty)
                VALUES($1, $2)
                ON CONFLICT (name) DO UPDATE
                  SET bounty = EXCLUDED.bounty
            """, data)

    async def get_all_primes(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT name, bounty FROM primes")

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

        # Effectif total = nombre de membres avec le rôle "MEMBRE"
        membre_role = guild.get_role(ROLE_IDS["MEMBRE"])
        total = len(membre_role.members) if membre_role else 0
        embed.add_field(name="Effectif total", value=f"{total} membres", inline=False)

        displayed      = set()
        classification = {"Puissant": [], "Fort": [], "Faible": []}

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
                        cat = ("Puissant" if val >= QUOTAS["Puissant"]
                               else "Fort" if val >= QUOTAS["Fort"]
                               else "Faible")
                        fleet = get_fleet_emoji(m)
                        grp.append((fleet, m, val, EMOJI_FORCE[cat]))
                        classification[cat].append(f"{fleet}{m.mention}")
                        displayed.add(m.id)
                        break
            grp.sort(key=lambda x: x[2], reverse=True)
            value = "\n".join(
                f"- {fleet}{member.mention} – 💰 `{val:,} B` – {force}"
                for fleet, member, val, force in grp
            ) or "N/A"
            embed.add_field(name=f"{emoji_role} {label} :", value=value, inline=False)
            embed.add_field(name="\u200b", value="__________________", inline=False)

        lines = []
        for cat in ("Puissant", "Fort", "Faible"):
            em       = EMOJI_FORCE[cat]
            mentions = " ".join(classification[cat]) or "N/A"
            lines.append(f"{em} **{cat}** ({len(classification[cat])}) : {mentions}")
        embed.add_field(name="📊 Classification Globale", value="\n".join(lines), inline=False)

        return embed

    @commands.command(name="primes")
    @commands.has_permissions(administrator=True)
    async def primes(self, ctx: commands.Context):
        """!primes — met à jour puis affiche l’embed + bouton Actualiser."""
        await ctx.message.delete()
        loading = await ctx.send("⏳ Mise à jour des primes…")
        await self.fetch_and_upsert()
        embed = await self.build_embed(ctx.guild)
        await loading.delete()
        # Passe le message à la vue pour l'édition future
        view = self.RefreshView(self, None)
        msg = await ctx.send(embed=embed, view=view)
        # assigne le message dans la vue
        view.prime_message = msg

    class RefreshView(View):
        def __init__(self, cog: "Prime", prime_message: discord.Message):
            super().__init__(timeout=None)
            self.cog = cog
            self.prime_message = prime_message

        @discord.ui.button(label="🔁 Actualiser", style=discord.ButtonStyle.secondary, custom_id="refresh_primes")
        async def refresh(self, interaction: discord.Interaction, button: Button):
            # ouvre la modal pour saisir le suffixe
            if not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message("🚫 Réservé aux administrateurs.", ephemeral=True)
            # envoie la modal en passant message et cog
            modal = SuffixModal(self.cog, interaction.message)
            await interaction.response.send_modal(modal)

async def setup(bot: commands.Bot):
    await bot.add_cog(Prime(bot))
