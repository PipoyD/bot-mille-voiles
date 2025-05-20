# cogs/prime.py

import re
import aiohttp
import discord
import unicodedata
from discord.ext import commands
from bs4 import BeautifulSoup

PRIME_URL = "https://cosmos-one-piece-v2.gitbook.io/piraterie/primes-personnel/hybjaafrrbnajg"

# Ordre et noms des rôles
ROLE_ORDER = [
    ("👑 Capitaine",       "Capitaine"),
    ("⚔️ Vice-Capitaine",  "Vice-Capitaine"),
    ("🛡️ Commandant",     "Commandant"),
    ("🎖️ Lieutenant",     "Lieutenant"),
    ("⚓ Membre d’équipage","Membre d’équipage"),
]

# Seuils de classification
QUOTAS = {
    "Puissant":  50_000_000,
    "Fort":      10_000_000,
    "Faible":     1_000_000,
}
EMOJI_FORCE = {
    "Puissant": "🔥",
    "Fort":     "⚔️",
    "Faible":   "💀",
}

def normalize(text: str) -> str:
    # Unicode NFD, minuscules, on retire les diacritiques, puis on garde lettres/chiffres/espaces
    txt = unicodedata.normalize("NFD", text).lower()
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9 ]+", "", txt)

def name_matches(dname: str, entry: str) -> bool:
    """Vrai si tous les tokens de dname sont dans entry."""
    dn = normalize(dname).split()
    en = normalize(entry)
    return all(token in en.split() for token in dn)

class Prime(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="prime")
    @commands.has_permissions(administrator=True)
    async def prime(self, ctx: commands.Context):
        loading = await ctx.send("⏳ Récupération des primes…")

        # 1) On va chercher la page
        async with aiohttp.ClientSession() as sess:
            async with sess.get(PRIME_URL) as resp:
                html = await resp.text()

        # 2) On extrait Nom – Prime avec BeautifulSoup + regex
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text("\n")
        matches = re.findall(r"([^\-\n\r]+?)\s*-\s*([\d,]+)\s*B", text)
        # primes_raw : {Nom brut : montant int}
        primes_raw = {name.strip(): int(amount.replace(",", "")) for name, amount in matches}

        # 3) Pour faciliter la recherche, on garde la liste des noms bruts
        entries = list(primes_raw.keys())

        # 4) Construction de l'embed
        embed = discord.Embed(
            title=f"• Équipage : {ctx.guild.name} • ⚓",
            color=0x1abc9c
        )
        embed.set_thumbnail(url=ctx.guild.icon.url if ctx.guild.icon else None)

        # Effectif total = tous les membres qui matchent au moins un nom de prime
        total = 0
        for m in ctx.guild.members:
            if any(name_matches(m.display_name, e) for e in entries):
                total += 1
        embed.add_field(name="Effectif total", value=f"{total} membres", inline=False)

        # 5) Pour chaque rôle
        for icon, role_name in ROLE_ORDER:
            role = discord.utils.get(ctx.guild.roles, name=role_name)
            if not role:
                continue

            grp = []
            for m in role.members:
                for e in entries:
                    if name_matches(m.display_name, e):
                        montant = primes_raw[e]
                        # classification
                        if montant >= QUOTAS["Puissant"]:
                            cat = "Puissant"
                        elif montant >= QUOTAS["Fort"]:
                            cat = "Fort"
                        else:
                            cat = "Faible"
                        grp.append((m, montant, EMOJI_FORCE[cat]))
                        break

            # tri décroissant
            grp.sort(key=lambda x: x[1], reverse=True)

            if not grp:
                value = "N/A"
            else:
                lines = [
                    f"- {m.mention} – 💰 `{montant:,} B` – {emoji}"
                    for m, montant, emoji in grp
                ]
                value = "\n".join(lines)

            embed.add_field(name=f"{icon} :", value=value, inline=False)
            embed.add_field(name="\u200b", value="__________________", inline=False)

        await loading.delete()
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Prime(bot))
