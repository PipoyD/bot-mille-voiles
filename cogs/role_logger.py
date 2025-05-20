# cogs/role_logger.py

import discord
from discord import Embed
from discord.ext import commands
from datetime import datetime, timezone

# Remplace par l'ID de ton canal de logs
ROLE_LOG_CHANNEL_ID = 123456789012345678  

class RoleLogger(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        # 1️⃣ Détecte les rôles ajoutés et retirés
        before_roles = set(before.roles)
        after_roles  = set(after.roles)

        added_roles   = after_roles - before_roles
        removed_roles = before_roles - after_roles

        if not added_roles and not removed_roles:
            return  # pas de changement

        guild = after.guild
        log_chan = guild.get_channel(ROLE_LOG_CHANNEL_ID)
        if log_chan is None:
            return  # canal non trouvé

        # 2️⃣ Cherche dans les logs d’audit qui a fait le changement
        executor = None
        async for entry in guild.audit_logs(limit=5, action=discord.AuditLogAction.member_role_update):
            if entry.target.id == after.id:
                # On prend la première entrée correspondante
                executor = entry.user
                break

        # 3️⃣ Pour chaque rôle ajouté, envoie un embed "Ajout"
        for role in added_roles:
            embed = Embed(
                title="🔧 Rôle ajouté",
                color=0x00ff00,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Membre",        value=f"{after.mention} (`{after.id}`)", inline=False)
            embed.add_field(name="Rôle ajouté",   value=f"{role.name} (`{role.id}`)", inline=False)
            embed.add_field(
                name="Par", 
                value=f"{executor.mention if executor else 'Inconnu'} (`{getattr(executor,'id','')}`)",
                inline=False
            )
            await log_chan.send(embed=embed)

        # 4️⃣ Pour chaque rôle retiré, envoie un embed "Retrait"
        for role in removed_roles:
            embed = Embed(
                title="🚫 Rôle retiré",
                color=0xff0000,
                timestamp=datetime.now(timezone.utc)
            )
            embed.add_field(name="Membre",        value=f"{after.mention} (`{after.id}`)", inline=False)
            embed.add_field(name="Rôle retiré",   value=f"{role.name} (`{role.id}`)", inline=False)
            embed.add_field(
                name="Par", 
                value=f"{executor.mention if executor else 'Inconnu'} (`{getattr(executor,'id','')}`)",
                inline=False
            )
            await log_chan.send(embed=embed)

async def setup(bot: commands.Bot):
    await bot.add_cog(RoleLogger(bot))
