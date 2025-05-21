# cogs/prime.py

import os
import re
import unicodedata
import aiohttp
import asyncpg
import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput

# Préfixe fixe de l'URL GitBook
URL_PREFIX = "https://cosmos-one-piece-v2.gitbook.io/piraterie/primes-personnel/"

# IDs et ordre des rôles
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

# Emojis de flotte
FLEET_EMOJIS = {
    1371942480316203018: "<:1reflotte:1372158546531324004>",
    1371942559894736916: "<:2meflotte:1372158586951696455>",
}

# Seuils et emojis de classification
QUOTAS = {
    "Très Dangereux": 1_150_000_000,
    "Dangereux":       300_000_000,
    "Très Puissant":   150_000_000,
    "Puissant":         30_000_000,
    "Fort":              5_000_000,
    "Faible":                   0,
}
EMOJI_FORCE = {
    "Très Dangereux": "🏹",
    "Dangereux":      "🏹",
    "Très Puissant":  "🔥",
    "Puissant":       "🔥",
    "Fort":           "⚔️",
    "Faible":         "💀",
}

def normalize(text: str) -> str:
    """NFD + casefold → retire accents, met en minuscules, ne garde que a-z0-9 et espace."""
    nfkd = unicodedata.normalize("NFD", text).casefold()
    stripped = "".join(ch for ch in nfkd if not unicodedata.combining(ch))
    return re.sub(r"[^a-z0-9 ]+", "", stripped)

def name_matches(dname: str, entry: str) -> bool:
    """Vérifie que chaque mot de dname apparaît dans entry après normalisation."""
    dn = normalize(dname).split()
    en = normalize(entry).split()
    return all(tok in en for tok in dn)

def get_fleet_emoji(member: discord.Member) -> str:
    """Retourne l'emoji de flotte si le membre a l'un des rôles de flotte."""
    for r in member.roles:
        if r.id in FLEET_EMOJIS:
            return FLEET_EMOJIS[r.id]
    return ""

class SlugModal(Modal):
    slug = TextInput(
        label="Identifiant de la page primes (slug)",
        placeholder="gvednstndtrsdd",
        style=discord.TextStyle.short,
        required=True,
    )

    def __init__(self, cog: "Prime", message: discord.Message):
        super().__init__(title="Actualiser les primes")
        self.cog = cog
        self.message = message

    async def on_submit(self, interaction: discord.Interaction):
        slug = self.slug.value.strip()
        url  = URL_PREFIX + slug
        try:
            # Mise à jour de la base
            await self.cog.fetch_and_upsert(url)
            # Construction des deux embeds
            roles_embed, classif_embed = await self.cog.build_all_embeds(interaction.guild)
            # Édition du message initial (embed rôles seul, plus de view)
            await self.message.edit(content=None, embed=roles_embed, view=None)
            # Envoi du embed classification avec le bouton Actualiser
            await self.message.channel.send(embed=classif_embed, view=self.cog.RefreshView(self.cog))
            await interaction.response.send_message("✅ Primes actualisées.", ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Échec mise à jour : {e}", ephemeral=True)

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

    async def fetch_and_upsert(self, url: str):
        """Scrape l’URL donnée, extrait les primes, et upserte en base."""
        timeout = aiohttp.ClientTimeout(total=15)
        async with aiohttp.ClientSession(timeout=timeout) as sess:
            async with sess.get(url) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"HTTP {resp.status} pour {url}")
                html = await resp.text()

        rows = re.findall(r"([^\-<>\r\n]+?)\s*[–-]\s*([\d,]+)\s*B", html)
        if not rows:
            raise RuntimeError("Aucune prime trouvée dans le HTML")

        data = [(n.strip(), int(b.replace(",", ""))) for n, b in rows]
        async with self.pool.acquire() as conn:
            await conn.executemany("""
                INSERT INTO primes(name, bounty)
                VALUES($1, $2)
                ON CONFLICT(name) DO UPDATE
                  SET bounty = EXCLUDED.bounty
            """, data)

    async def get_all_primes(self):
        async with self.pool.acquire() as conn:
            return await conn.fetch("SELECT name, bounty FROM primes")

    async def find_prime_for(self, display_name: str):
        best = (None, -1)
        for r in await self.get_all_primes():
            if name_matches(display_name, r["name"]) and r["bounty"] > best[1]:
                best = (r["name"], r["bounty"])
        return best if best[0] else (None, None)

    async def build_roles_embed(self, guild: discord.Guild) -> discord.Embed:
        """Embed détaillant les primes par rôle."""
        rows       = await self.get_all_primes()
        primes_raw = {r["name"]: r["bounty"] for r in rows}
        entries    = sorted(primes_raw, key=lambda k: primes_raw[k], reverse=True)

        embed = discord.Embed(
            title=f"• Primes par rôle – {guild.name} •",
            color=0x1abc9c
        )
        if guild.icon:
            embed.set_thumbnail(url=guild.icon.url)

        displayed = set()
        def safe(t): return t if len(t) <= 1024 else t[:1020] + "…"

        for role_id, emoji_role, label in ROLE_ORDER:
            role = guild.get_role(role_id)
            if not role:
                continue
            lines = []
            for m in role.members:
                if m.id in displayed:
                    continue
                for e in entries:
                    if name_matches(m.display_name, e):
                        bounty = primes_raw[e]
                        # catégorie
                        if bounty >= QUOTAS["Très Dangereux"]:
                            cat = "Très Dangereux"
                        elif bounty >= QUOTAS["Dangereux"]:
                            cat = "Dangereux"
                        elif bounty >= QUOTAS["Très Puissant"]:
                            cat = "Très Puissant"
                        elif bounty >= QUOTAS["Puissant"]:
                            cat = "Puissant"
                        elif bounty >= QUOTAS["Fort"]:
                            cat = "Fort"
                        else:
                            cat = "Faible"
                        mention = f"{get_fleet_emoji(m)}{m.mention}"
                        lines.append(f"- {mention} – 💰 `{bounty:,} B` – *{EMOJI_FORCE[cat]} {cat}*")
                        displayed.add(m.id)
                        break
            txt = "\n".join(lines) or "N/A"
            embed.add_field(name=f"{emoji_role} {label}", value=safe(txt), inline=False)
            embed.add_field(name="\u200b", value="—", inline=False)

        return embed

    async def build_classification_embed(self, guild: discord.Guild) -> discord.Embed:
        """Embed de la classification globale, triée et chunkée par catégorie."""
        rows = await self.get_all_primes()
        primes_raw = {r["name"]: r["bounty"] for r in rows}
        # trier entrées par prime décroissante
        sorted_entries = sorted(primes_raw.items(), key=lambda kv: kv[1], reverse=True)

        # remplir classification dans le bon ordre
        classification = {cat: [] for cat in QUOTAS}
        for entry, bounty in sorted_entries:
            if bounty >= QUOTAS["Très Dangereux"]:
                cat = "Très Dangereux"
            elif bounty >= QUOTAS["Dangereux"]:
                cat = "Dangereux"
            elif bounty >= QUOTAS["Très Puissant"]:
                cat = "Très Puissant"
            elif bounty >= QUOTAS["Puissant"]:
                cat = "Puissant"
            elif bounty >= QUOTAS["Fort"]:
                cat = "Fort"
            else:
                cat = "Faible"

            # cherche le member correspondant
            member_obj = discord.utils.find(
                lambda m: name_matches(m.display_name, entry),
                guild.members
            )
            if member_obj:
                mention = f"{get_fleet_emoji(member_obj)}{member_obj.mention}"
                classification[cat].append(mention)

        embed = discord.Embed(
            title=f"📊 Classification Globale – {guild.name}",
            color=0x1abc9c
        )

        # un field par catégorie non vide, chunké en 10 mentions max
        for cat, mentions in classification.items():
            if not mentions:
                continue
            for i in range(0, len(mentions), 10):
                chunk = mentions[i:i+10]
                embed.add_field(
                    name=f"{EMOJI_FORCE[cat]} {cat} ({len(mentions)})",
                    value=" ".join(chunk),
                    inline=False
                )

        return embed

    async def build_all_embeds(self, guild: discord.Guild):
        """Retourne [roles_embed, classification_embed]."""
        return [
            await self.build_roles_embed(guild),
            await self.build_classification_embed(guild)
        ]

    @commands.command(name="primes")
    @commands.has_permissions(administrator=True)
    async def primes(self, ctx: commands.Context):
        """!primes — affiche le bouton Actualiser pour démarrer."""
        await ctx.message.delete()
        await ctx.send(
            "Cliquez sur « 🔁 Actualiser » pour saisir l’identifiant de la page primes.",
            view=self.RefreshView(self)
        )

    @commands.command(name="prime")
    @commands.has_role(ROLE_IDS["MEMBRE"])
    async def prime_user(self, ctx: commands.Context):
        """!prime — affiche votre prime et votre nom RP."""
        await ctx.message.delete()
        name, bounty = await self.find_prime_for(ctx.author.display_name)
        if bounty is None:
            return await ctx.send("❌ Prime introuvable pour votre Nom RP.", ephemeral=True)
        await ctx.send(f"📜 **Nom RP :** {name}\n💰 **Prime :** {bounty:,} B", ephemeral=True)

    class RefreshView(View):
        def __init__(self, cog: "Prime"):
            super().__init__(timeout=None)
            self.cog = cog

        @discord.ui.button(label="🔁 Actualiser", style=discord.ButtonStyle.secondary, custom_id="refresh_primes")
        async def refresh(self, interaction: discord.Interaction, button: Button):
            if not interaction.user.guild_permissions.administrator:
                return await interaction.response.send_message("🚫 Réservé aux administrateurs.", ephemeral=True)
            await interaction.response.send_modal(SlugModal(self.cog, interaction.message))

    @commands.command(name="clearprimes")
    @commands.has_permissions(administrator=True)
    async def clear_primes(self, ctx: commands.Context):
        """Vide entièrement la table primes."""
        await ctx.message.delete()
        async with self.pool.acquire() as conn:
            await conn.execute("DELETE FROM primes")
        await ctx.send("✅ Table `primes` vidée.", delete_after=5)

async def setup(bot: commands.Bot):
    await bot.add_cog(Prime(bot))
