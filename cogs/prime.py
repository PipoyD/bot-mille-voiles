# cogs/prime.py

import re
import aiohttp
import discord
import unicodedata
from discord.ext import commands

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
    txt = unicodedata.normalize("NFD", text).lower()
    txt = "".join(ch for ch in txt if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9 ]+", "", txt)

def name_matches(dname: str, entry: str) -> bool:
    dn = normalize(dname).split()
    en = normalize(entry).split()
    return all(token in en for token in dn)

class Prime(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="prime")
    @commands.has_permissions(administrator=True)
    async def prime(self, ctx: commands.Context):
        loading = await ctx.send("⏳ Récupération des primes…")

        # 1) On récupère le HTML brut
        async with aiohttp.ClientSession() as sess:
            async with sess.get(PRIME_URL) as resp:
                html = await resp.text()

        # 2) On extrait directement Nom – Prime via regex
        #    pattern : "Quelque Chose - 12,345,678 B"
        matches = re.findall(r"([^\-\n\r<>]+?)\s*-\s*([\d,]+)\s*B", html)
        primes_raw = {
            name.strip(): int(amount.replace(",", ""))
            for name, amount in matches
        }
        entries = list(primes_raw.keys())

        # 3) Construction de l'embed
        embed = discord.Embed(
            title=f"• Équipage : {ctx.guild.name} • ⚓",
            color=0x1abc9c
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        # Effectif total
        total = sum(
            1 for m in ctx.guild.members
            if any(name_matches(m.display_name, e) for e in entries)
        )
        embed.add_field(name="Effectif total", value=f"{total} membres", inline=False)

        # 4) Par rôle
        for icon, role_name in ROLE_ORDER:
            role = discord.utils.get(ctx.guild.roles, name=role_name)
            if not role:
                continue

            grp = []
            for m in role.members:
                for e in entries:
                    if name_matches(m.display_name, e):
                        montant = primes_raw[e]
                        if montant >= QUOTAS["Puissant"]:
                            cat = "Puissant"
                        elif montant >= QUOTAS["Fort"]:
                            cat = "Fort"
                        else:
                            cat = "Faible"
                        grp.append((m, montant, EMOJI_FORCE[cat]))
                        break

            grp.sort(key=lambda x: x[1], reverse=True)

            if grp:
                lines = [f"- {m.mention} – 💰 `{val:,} B` – {emoji}" for m, val, emoji in grp]
                value = "\n".join(lines)
            else:
                value = "N/A"

            embed.add_field(name=f"{icon} :", value=value, inline=False)
            embed.add_field(name="\u200b", value="__________________", inline=False)

        await loading.delete()
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Prime(bot))
