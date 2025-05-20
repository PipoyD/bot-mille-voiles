# cogs/prime.py

import re
import aiohttp
import discord
import unicodedata
from discord.ext import commands

PRIME_URL = "https://cosmos-one-piece-v2.gitbook.io/piraterie/primes-personnel/hybjaafrrbnajg"

# Les rôles et leur ordre d'affichage
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

# Rôles de flotte → emoji à afficher
FLEET_EMOJIS = {
    1371942480316203018: "<:2meflotte:1372158586951696455>",  # Écarlate
    1371942559894736916: "<:1reflotte:1372158546531324004>",  # Azur
}

# Seuils de classification et emojis
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
    for role in member.roles:
        if role.id in FLEET_EMOJIS:
            return FLEET_EMOJIS[role.id]
    return ""  # pas de flotte

class Prime(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.command(name="prime")
    @commands.has_permissions(administrator=True)
    async def prime(self, ctx: commands.Context):
        loading = await ctx.send("⏳ Récupération des primes…")

        # 1) Fetch brut HTML
        async with aiohttp.ClientSession() as sess:
            async with sess.get(PRIME_URL) as resp:
                html = await resp.text()

        # 2) Extraction Nom – Prime via regex
        matches = re.findall(r"([^\-\n\r<>]+?)\s*-\s*([\d,]+)\s*B", html)
        primes_raw = {n.strip(): int(a.replace(",", "")) for n, a in matches}
        entries = list(primes_raw.keys())

        # 3) Préparation de l'embed
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

        # 4) Parcours par rôle + classification
        displayed = set()
        classification = {"Puissant": [], "Fort": [], "Faible": []}

        for role_id, emoji_role, label in ROLE_ORDER:
            role = ctx.guild.get_role(role_id)
            if not role:
                continue

            grp = []
            for m in role.members:
                if m.id in displayed:
                    continue
                for e in entries:
                    if name_matches(m.display_name, e):
                        val = primes_raw[e]
                        if val >= QUOTAS["Puissant"]:
                            cat = "Puissant"
                        elif val >= QUOTAS["Fort"]:
                            cat = "Fort"
                        else:
                            cat = "Faible"
                        fleet_emoji = get_fleet_emoji(m)
                        grp.append((fleet_emoji, m, val, EMOJI_FORCE[cat]))
                        classification[cat].append(f"{fleet_emoji}{m.mention}")
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

        # 5) Champ de classification globale
        lines = []
        for cat in ("Puissant", "Fort", "Faible"):
            em = EMOJI_FORCE[cat]
            mentions = " ".join(classification[cat]) or "N/A"
            lines.append(f"{em} **{cat}** ({len(classification[cat])}) : {mentions}")
        embed.add_field(name="📊 Classification Globale", value="\n".join(lines), inline=False)

        # 6) Envoi
        await loading.delete()
        await ctx.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(Prime(bot))
