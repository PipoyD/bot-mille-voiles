# cogs/primes.py

import re
import sqlite3
import aiohttp
import discord
import unicodedata
from discord.ext import commands
from discord.ui import View, Button

PRIME_URL = "https://cosmos-one-piece-v2.gitbook.io/piraterie/primes-personnel/hybjaafrrbnajg"

# IDs de rôles (recruteurs et hiérarchie)
RECRUTEUR_ROLE_ID = 1317850709948891177
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

# Fleets emojis (cf. cogs/flotte.py)
FLEET_EMOJIS = {
    1371942480316203018: "<:2meflotte:1372158586951696455>",
    1371942559894736916: "<:1reflotte:1372158546531324004>",
}

# Classification
QUOTAS = {"Puissant": 50_000_000, "Fort": 10_000_000, "Faible": 1_000_000}
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

class PrimesCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        # On initialise la DB SQLite
        self.db_path = "data/primes.db"
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS primes (
                name TEXT PRIMARY KEY,
                bounty INTEGER
            )
        """)
        self.conn.commit()

    async def fetch_and_update(self):
        """Récupère le HTML, parse les primes, et met à jour la table."""
        async with aiohttp.ClientSession() as sess:
            async with sess.get(PRIME_URL) as resp:
                html = await resp.text()

        matches = re.findall(r"([^\-\n\r<>]+?)\s*-\s*([\d,]+)\s*B", html)
        data = [(n.strip(), int(a.replace(",", ""))) for n, a in matches]

        cur = self.conn.cursor()
        cur.execute("DELETE FROM primes")
        cur.executemany("INSERT INTO primes(name,bounty) VALUES (?,?)", data)
        self.conn.commit()

    def get_all_primes(self):
        cur = self.conn.cursor()
        cur.execute("SELECT name,bounty FROM primes")
        return cur.fetchall()

    def find_prime_for(self, display_name: str):
        for name, bounty in self.get_all_primes():
            if name_matches(display_name, name):
                return bounty
        return None

    def build_embed(self, guild: discord.Guild) -> discord.Embed:
        primes = dict(self.get_all_primes())
        entries = list(primes.keys())

        embed = discord.Embed(
            title=f"• Équipage : {guild.name} • ⚓",
            color=0x1abc9c
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        # total
        total = sum(1 for m in guild.members
                    if any(name_matches(m.display_name, e) for e in entries))
        embed.add_field(name="Effectif total", value=f"{total} membres", inline=False)

        displayed = set()
        classification = {"Puissant": [], "Fort": [], "Faible": []}

        # par rôle
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
                        val = primes[e]
                        if val >= QUOTAS["Puissant"]:
                            cat = "Puissant"
                        elif val >= QUOTAS["Fort"]:
                            cat = "Fort"
                        else:
                            cat = "Faible"
                        fleet = get_fleet_emoji(m)
                        grp.append((fleet, m, val, EMOJI_FORCE[cat]))
                        classification[cat].append(f"{fleet}{m.mention}")
                        displayed.add(m.id)
                        break

            grp.sort(key=lambda x: x[2], reverse=True)
            if grp:
                lines = [
                    f"- {fleet}{member.mention} – 💰 `{val:,} B` – {force}"
                    for fleet, member, val, force in grp
                ]
                value = "\n".join(lines)
            else:
                value = "N/A"

            embed.add_field(name=f"{emoji_role} {label} :", value=value, inline=False)
            embed.add_field(name="\u200b", value="__________________", inline=False)

        # classification globale
        lines = []
        for cat in ("Puissant", "Fort", "Faible"):
            em = EMOJI_FORCE[cat]
            mentions = " ".join(classification[cat]) or "N/A"
            lines.append(f"{em} **{cat}** ({len(classification[cat])}) : {mentions}")
        embed.add_field(name="📊 Classification Globale", value="\n".join(lines), inline=False)

        return embed

    @commands.command(name="primes")
    @commands.has_permissions(administrator=True)
    async def primes(self, ctx: commands.Context):
        """Affiche toutes les primes (admins only)."""
        await ctx.message.delete()
        await self.fetch_and_update()
        view = self.RefreshView(self)
        embed = self.build_embed(ctx.guild)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="prime")
    @commands.has_role(RECRUTEUR_ROLE_ID)
    async def prime_user(self, ctx: commands.Context):
        """Affiche votre prime (recruteurs only)."""
        await ctx.message.delete()
        bounty = self.find_prime_for(ctx.author.display_name)
        if bounty is None:
            return await ctx.send("❌ Prime introuvable pour votre Nom RP.", ephemeral=True)
        await ctx.send(f"💰 Votre prime : `{bounty:,} B`", ephemeral=True)

    class RefreshView(View):
        def __init__(self, cog: "PrimesCog"):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label="🔁 Actualiser", style=discord.ButtonStyle.secondary, custom_id="refresh_primes")
        async def refresh(self, interaction: discord.Interaction, button: Button):
            if not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message("🚫 Réservé aux administrateurs.", ephemeral=True)
            await self.cog.fetch_and_update()
            embed = self.cog.build_embed(interaction.guild)
            await interaction.message.edit(embed=embed, view=self)
            await interaction.response.send_message("✅ Primes actualisées.", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(PrimesCog(bot))
