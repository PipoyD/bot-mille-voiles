# cogs/prime.py

import re
import aiohttp
import discord
import unicodedata
from discord.ext import commands

PRIME_URL = "https://cosmos-one-piece-v2.gitbook.io/piraterie/primes-personnel/hybjaafrrbnajg"

# On reprend la même table de rôles que ton cog flotte.py
ROLE_IDS = {
    "CAPITAINE":       1317851007358734396,
    "VICE_CAPITAINE":  1358079100203569152,
    "COMMANDANT":      1358031308542181382,
    "VICE_COMMANDANT": 1358032259596288093,
    "LIEUTENANT":      1358030829225381908,
    "MEMBRE":          1317850709948891177,
}

# Ordre d’affichage (id, icône, label)
ROLE_ORDER = [
    (ROLE_IDS["CAPITAINE"],       "👑", "Capitaine"),
    (ROLE_IDS["VICE_CAPITAINE"],  "⚔️", "Vice-Capitaine"),
    (ROLE_IDS["COMMANDANT"],      "🛡️", "Commandant"),
    (ROLE_IDS["VICE_COMMANDANT"], "🗡️", "Vice-Commandant"),
    (ROLE_IDS["LIEUTENANT"],      "🎖️", "Lieutenant"),
    (ROLE_IDS["MEMBRE"],          "⚓", "Membre d’équipage"),
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
    return all(tok in en for tok in dn)

class Prime(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="prime")
    @commands.has_permissions(administrator=True)
    async def prime(self, ctx: commands.Context):
        loading = await ctx.send("⏳ Récupération des primes…")

        # 1) fetch brut HTML
        async with aiohttp.ClientSession() as sess:
            async with sess.get(PRIME_URL) as resp:
                html = await resp.text()

        # 2) regex "Nom - 12,345,678 B"
        matches = re.findall(r"([^\-\n\r<>]+?)\s*-\s*([\d,]+)\s*B", html)
        primes_raw = {n.strip(): int(a.replace(",", "")) for n, a in matches}
        entries = list(primes_raw.keys())

        # 3) construction de l'embed
        embed = discord.Embed(
            title=f"• Équipage : {ctx.guild.name} • ⚓",
            color=0x1abc9c
        )
        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)

        # total des membres qui ont une prime
        total = sum(
            1 for m in ctx.guild.members
            if any(name_matches(m.display_name, e) for e in entries)
        )
        embed.add_field(name="Effectif total", value=f"{total} membres", inline=False)

        # 4) par rôle (ID)
        for role_id, emoji, label in ROLE_ORDER:
            role = ctx.guild.get_role(role_id)
            if not role:
                continue

            grp = []
            for m in role.members:
                for e in entries:
                    if name_matches(m.display_name, e):
                        val = primes_raw[e]
                        if val >= QUOTAS["Puissant"]:
                            cat = "Puissant"
                        elif val >= QUOTAS["Fort"]:
                            cat = "Fort"
                        else:
                            cat = "Faible"
                        grp.append((m, val, EMOJI_FORCE[cat]))
                        break

            grp.sort(key=lambda x: x[1], reverse=True)
            if grp:
                lines = [
                    f"- {m.mention} – 💰 `{val:,} B` – {emoji}"
                    for m, val, emoji in grp
                ]
                value = "\n".join(lines)
            else:
                value = "N/A"

            embed.add_field(name=f"{emoji} {label} :", value=value, inline=False)
            embed.add_field(name="\u200b", value="__________________", inline=False)

        await loading.delete()
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Prime(bot))
