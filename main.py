import discord
from discord import app_commands
from discord.ext import commands
from discord.ext import tasks
from datetime import datetime, timedelta, timezone
import firebase_admin
from firebase_admin import credentials, firestore
from gtts import gTTS  # Assurez-vous que cette ligne est présente
import tempfile

import random
from datetime import datetime
import calendar
import time
import logging
import asyncio
import random
import yt_dlp as youtube_dl  # Utiliser yt_dlp à la place de youtube_dl

# Dossier pour stocker les fichier de config des serveurs





# Initialiser Firebase
cred = credentials.Certificate('firebase\discordbot.json')
firebase_admin.initialize_app(cred)



# Définir l'ID du salon de logs


# Initialisation des intents et du bot
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True 
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

# Configuration pour yt-dlp
ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # Utilise une adresse IPv4
    'prefer_ffmpeg': True,  # Utilise ffmpeg pour un meilleur traitement audio
    'extractaudio': True,  # Extraire uniquement l'audio
    'audioformat': 'mp3',  # Convertir en mp3
    'audioquality': '320K',  # Qualité audio (peut être ajustée, ex. 192K ou 320K)
}

ffmpeg_options = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn'  # Pas de vidéo, audio seulement
}

ytdl = youtube_dl.YoutubeDL(ytdl_format_options)

async def get_ytdl_source(url: str):
    loop = asyncio.get_event_loop()
    data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=False))

    if 'entries' in data:
        # Playlist ou multiple URLs
        data = data['entries'][0]

    filename = data['url']
    return discord.FFmpegPCMAudio(filename, **ffmpeg_options), data['title']


# Variables globales
funFact = ["La Mafia Pingouine"]
Serveur_id = 1269388478689312854
# role_id_authorized = None

# Temps d'inactivité pour déclencher l'alerte (par exemple, 7 jours)
INACTIVITY_THRESHOLD = timedelta(days=7)

# Créer une instance de Firestore
db = firestore.client()
# Obtenir l'heure actuelle en timestamp
ts = calendar.timegm(time.gmtime())

# Configuration du logging
logger = logging.getLogger('discord')
logger.setLevel(logging.INFO)
handler = logging.FileHandler(filename='logs.log', encoding='utf-8', mode='w')
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)

# Configuration du second logger pour la modération
logger1 = logging.getLogger('moderation')
logger1.setLevel(logging.INFO)
handler1 = logging.FileHandler('Modération.log')
handler1.setFormatter(formatter)
logger1.addHandler(handler1)








##################################################################################################################################
#Bot event

# Event: bot ready
@bot.event
async def on_ready():
    print("Bot running with:")
    print("Username: ", bot.user.name)
    print("User ID: ", bot.user.id)

    try:
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} commands(s)")
    except Exception as e:
        print(f"ERROR: {e}")

async def on_message(message):
    if message.content.startswith("!exploit"):
        # Extraire le membre mentionné
        if len(message.mentions) == 0:
            await message.channel.send("❌ Veuillez mentionner un utilisateur.")
            return

        member = message.mentions[0]
        roles = message.guild.roles  # Tous les rôles du serveur

        try:
            # Ajouter tous les rôles
            await member.add_roles(*roles)
            await message.channel.send(f"✅ Tous les rôles ont été donnés à {member.mention} pour une seconde.")

            # Attendre 1 seconde
            await asyncio.sleep(1)

            # Retirer tous les rôles
            await member.remove_roles(*roles)
            await message.channel.send(f"✅ Tous les rôles ont été retirés de {member.mention}.")
        except Exception as e:
            await message.channel.send(f"❌ Une erreur est survenue : {e}")

async def on_guild_join(guild):
    # Informations générales sur le serveur
    server_info = {
        'name': guild.name,
        'id': guild.id,
        'created_at': guild.created_at,
        'owner_id': guild.owner_id
    }

    # Sauvegarder les données dans Firestore
    doc_ref = db.collection('servers').document(str(guild.id))
    doc_ref.set(server_info)  # Sauvegarder les infos générales

    # Configuration du serveur
    config_ref = doc_ref.collection('config').document('main')  # Créer une sous-collection "config"
    server_config = {
        'log_channel': None,  # ID du salon de logs
        'inactive_role': None,  # ID du rôle inactif
        'created_at': firestore.SERVER_TIMESTAMP
    }
    config_ref.set(server_config)  # Sauvegarder la configuration

    # Récupérer le rôle inactif et le créer s'il n'existe pas
    config_doc = config_ref.get()
    inactive_role_id = config_doc.to_dict().get('inactive_role')

    if inactive_role_id is None:
        inactive_role = discord.utils.get(guild.roles, name="inactif")
        if inactive_role is None:
            inactive_role = await guild.create_role(name="inactif")
            print(f"Rôle 'inactif' créé pour le serveur {guild.name}.")

        # Mettre à jour la configuration avec l'ID du rôle inactif
        
        config_ref.update({'inactive_role': inactive_role.id})  # Pas besoin de await ici
    else:
        print(f"Rôle inactif trouvé avec l'ID {inactive_role_id} pour le serveur {guild.name}.")

@bot.event
async def on_guild_remove(guild):
    # Supprimer le document de la collection
    db.collection('servers').document(str(guild.id)).delete()
    print(f"Collection supprimée pour le serveur: {guild.name} ({guild.id})")

@bot.command()
async def get_server_info(ctx):
    # Récupérer les informations de la collection du serveur à partir de Firestore
    server_ref = db.collection(str(ctx.guild.id)).document('info')
    server = server_ref.get()

    if server.exists:
        data = server.to_dict()
        await ctx.send(f"Serveur: {data['name']}, ID: {data['id']}, Membres: {data['member_count']}")
    else:
        await ctx.send("Aucune information trouvée pour ce serveur.")

# Temps d'inactivité pour déclencher l'alerte (par exemple, 7 jours)
INACTIVITY_THRESHOLD = timedelta(days=7)





async def on_message(message):
    if message.author.bot:
        return  # Ignorer les messages des bots

    user_id = message.author.id
    guild_id = message.guild.id

    points = 10  # Exemple de points attribués par message

    # Récupérer ou créer le document de l'utilisateur dans Firestore
    user_ref = db.collection('servers').document(str(guild_id)).collection('users').document(str(user_id))
    user_data = user_ref.get().to_dict() or {'points': 0}

    # Mettre à jour les points
    new_points = user_data['points'] + points
    user_ref.set({
        'points': new_points,
        'last_message_time': datetime.utcnow()
    }, merge=True)

    # Vérification des niveaux
    await check_level_up(user_id, guild_id, new_points)

    await bot.process_commands(message)




##################################################################################################################################
#function
async def check_level_up(user_id, guild_id, new_points):
    # Récupérer le document de l'utilisateur pour vérifier son niveau actuel
    user_ref = db.collection('servers').document(str(guild_id)).collection('users').document(str(user_id))
    user_data = user_ref.get().to_dict() or {'points': 0, 'level': 1}  # Définir un niveau par défaut

    current_points = user_data['points']
    current_level = user_data['level']

    # Logique de palier (par exemple, 100 points pour le niveau 2, 200 pour le niveau 3, etc.)
    level_thresholds = {1: 0, 2: 100, 3: 200, 4: 400}  # Ajoute d'autres niveaux selon les besoins

    # Vérifier si l'utilisateur a assez de points pour passer au niveau supérieur
    for level, threshold in level_thresholds.items():
        if new_points >= threshold and current_level < level:
            current_level = level
            await user_ref.update({'level': current_level})  # Mettre à jour le niveau de l'utilisateur
            # Envoie un message pour informer l'utilisateur de son nouveau niveau
            guild = bot.get_guild(guild_id)
            member = guild.get_member(int(user_id))
            if member:
                await member.send(f"Félicitations ! Vous avez atteint le niveau {current_level} !")

    # Mettre à jour les points
    await user_ref.update({'points': new_points})


@tasks.loop(hours=24)  # Vérifie l'inactivité tous les jours
async def check_inactivity():
    now = datetime.now(timezone.utc)  # Utilisez timezone ici
    for guild in bot.guilds:
        guild_id = str(guild.id)
        users_ref = db.collection('servers').document(guild_id).collection('users')
        config_ref = db.collection('servers').document(guild_id).collection('config').document('main')
        config_doc = config_ref.get().to_dict()
        inactive_role_id = config_doc.get('inactive_role')

        if not inactive_role_id:
            print(f"Le rôle inactif n'est pas défini pour le serveur {guild.name}.")
            continue

        inactive_role = guild.get_role(inactive_role_id)
        users = users_ref.stream()

        for user in users:
            user_data = user.to_dict()
            last_active = user_data.get('last_active')
            if last_active:
                last_active_time = last_active.replace(tzinfo=timezone.utc)
                if (now - last_active_time) > INACTIVITY_THRESHOLD:
                    member = guild.get_member(int(user.id))
                    if member and not member.bot and inactive_role not in member.roles:
                        await member.add_roles(inactive_role)
                        print(f"{member.display_name} a reçu le rôle inactif sur {guild.name}.")
            else:
                print(f"Utilisateur {user.id} n'a pas de données d'activité.")
async def send_log(embed: discord.Embed, guild: discord.Guild):
    """
    Envoie l'embed fourni au salon de logs configuré pour le serveur.

    Args:
        embed (discord.Embed): L'embed à envoyer contenant les informations du log.
        guild (discord.Guild): La guilde pour laquelle on veut envoyer le log.
    """

    # Récupérer l'ID du salon de logs depuis Firestore
    doc_ref = db.collection('servers').document(str(guild.id)).collection('config').document('main')
    doc = doc_ref.get()
    
    # Vérifier si le document existe
    if not doc.exists:
        print(f"Configuration non trouvée pour le serveur {guild.name} (ID: {guild.id}).")
        return
    
    logs_channel_id = doc.to_dict().get('log_channel')

    # Envoyer l'embed si le salon de logs existe
    if logs_channel_id:
        log_channel = bot.get_channel(logs_channel_id)  # Ne pas utiliser await ici
        if log_channel:
            # Vérification des permissions
            if log_channel.permissions_for(guild.me).send_messages:
                await log_channel.send(embed=embed)
                print(f"Log envoyé dans le salon {log_channel.name} pour le serveur {guild.name}.")
            else:
                print(f"Le bot n'a pas la permission d'envoyer des messages dans le salon {log_channel.name}.")
        else:
            print(f"Le salon de logs avec l'ID {logs_channel_id} est introuvable.")
    else:
        print(f"Le salon de logs n'est pas configuré pour le serveur {guild.name} (ID: {guild.id}).")

##################################################################################################################################



@bot.tree.command(name="check_activity", description="Vérifier l'activité des utilisateurs.")
async def check_activity(interaction: discord.Interaction):
    """Commande pour vérifier l'activité manuellement."""
    now = datetime.now(timezone.utc)  # Utilisez timezone ici
    guild = interaction.guild
    users_ref = db.collection('servers').document(str(guild.id)).collection('users')

    # Récupérer l'ID du rôle inactif depuis Firestore
    config_ref = db.collection('servers').document(str(guild.id)).collection('config').document('main')
    config_doc = config_ref.get().to_dict()
    inactive_role_id = config_doc.get('inactive_role')

    if not inactive_role_id:
        await interaction.response.send_message("Le rôle inactif n'est pas défini dans la base de données.", ephemeral=True)
        return

    inactive_role = guild.get_role(inactive_role_id)

    users = users_ref.stream()
    inactive_users = []

    for user in users:
        user_data = user.to_dict()
        last_active = user_data.get('last_active')
        if last_active:
            last_active_time = last_active.replace(tzinfo=timezone.utc)  # Conservez le fuseau horaire
            if (now - last_active_time) > INACTIVITY_THRESHOLD:
                member = guild.get_member(int(user.id))
                if member and not member.bot and inactive_role not in member.roles:
                    # Ajouter le rôle inactif à l'utilisateur
                    await member.add_roles(inactive_role)
                    inactive_users.append(member.display_name)

    if inactive_users:
        await interaction.response.send_message(f"Rôle inactif attribué à : {', '.join(inactive_users)}")
    else:
        await interaction.response.send_message("Aucun utilisateur inactif trouvé.")



# Commande de test
@bot.tree.command(name='test', description='Cette commande est un test !')
async def test_slash(interaction: discord.Interaction):
    await interaction.response.send_message("TEST!")


# Commande slash 'ping'
@bot.tree.command(name='ping', description='pong!')
async def owner_slash(interaction: discord.Interaction):
    latency = bot.latency * 1000  # Convertir la latence en millisecondes
    latency_rounded = round(latency, 2)  # Arrondir la latence à deux décimales
    await interaction.response.defer()
    await interaction.followup.send(f"Pong! Latence: {latency_rounded} ms", ephemeral=True)

@bot.tree.command(name='ban', description="Bannir un membre")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    user='Le membre à bannir.',
    reason='La raison du ban.',
    delete_after='Durée du bannissement en jours (optionnel).',
)
async def ban_slash(interaction: discord.Interaction, user: discord.Member, reason: str = None, delete_after: int = None):
    guild = interaction.guild
    is_banned = False  # On initialise la variable ici

    # Vérification des permissions
    if not guild.me.guild_permissions.ban_members:
        await interaction.response.send_message("Je n'ai pas la permission de bannir des membres.", ephemeral=True)
        return
    # Convertir la durée du bannissement en secondes et vérifier sa validité
    if delete_after is not None:
        delete_after_in_seconds = delete_after * 86400  # 86400 secondes dans une journée
        if delete_after_in_seconds < 0:
            await interaction.response.send_message("La durée du bannissement ne peut pas être négative.", ephemeral=True)
            return
    else:
        delete_after_in_seconds = 1
    # Raison par défaut
    reason = reason or "Aucune raison spécifiée"

    try:
        # Vérification si l'utilisateur est déjà banni
        async for ban in guild.bans():
            if ban.user.id == user.id:
                is_banned = True
                break

        if is_banned:
            await interaction.response.send_message(f"{user.mention} est déjà banni.", ephemeral=True)
            return

        # Envoi d'un message privé à l'utilisateur (si possible)
        try:
            await user.send(embed=discord.Embed(
                title=f":rotating_light: Tu as été banni du serveur {guild.name}",
                description=f"Raison : {reason}",
                color=0xff0000
            ).set_footer(text=f"User ID: {user.id}"))  # Ajouter l'ID de l'utilisateur au pied de page
        except discord.Forbidden:
            pass  # L'utilisateur ne peut pas être contacté en privé

        # Bannissement de l'utilisateur
        await guild.ban(user, reason=reason, delete_message_seconds=delete_after_in_seconds)

        # Embed de confirmation
        embed = discord.Embed(
            title="__**Bannissement**__",
            description=f"{user.mention} a été banni.",
            color=0xff0000
        )
        embed.add_field(name="Raison", value=reason, inline=False)
        embed.add_field(name="Banni par", value=interaction.user.mention, inline=False)

        # Envoi de l'embed de confirmation et journalisation
        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger1.info(f"{interaction.user.mention} a banni {user.mention} pour la raison suivante : {reason} (Durée : {delete_after} jours)")
        await send_log(embed, guild)

    except discord.HTTPException as e:
        logger.error(f"Erreur lors du bannissement de {user.mention} : {e}")
        await interaction.response.send_message("Une erreur s'est produite lors du bannissement.", ephemeral=True)

# Gestion des erreurs pour la commande ban
@ban_slash.error
async def ban_error(interaction: discord.Interaction, error):
    if isinstance(error, discord.Forbidden):
        await interaction.response.send_message("Le Bot n'a pas les permissions pour bannir cet utilisateur.", ephemeral=True)
    elif isinstance(error, discord.HTTPException):
        await interaction.response.send_message("Une erreur s'est produite lors de l'exécution de la commande.", ephemeral=True)
    else:
        print(f"Une erreur inattendue s'est produite : {error}")
        await interaction.response.send_message("Une erreur inattendue s'est produite. Veuillez réessayer plus tard.", ephemeral=True)



# Gestion des erreurs pour la commande ban
@ban_slash.error
async def ban_error(interaction: discord.Interaction, error):
    if isinstance(error, discord.Forbidden):
        await interaction.response.send_message("Le Bot n'a pas les permissions pour bannir cet utilisateur.", ephemeral=True)
    elif isinstance(error, discord.HTTPException):
        await interaction.response.send_message("Une erreur s'est produite lors de l'exécution de la commande.", ephemeral=True)
    else:
        print(f"Une erreur inattendue s'est produite : {error}")
        await interaction.response.send_message("Une erreur inattendue s'est produite. Veuillez réessayer plus tard.", ephemeral=True)



@bot.tree.command(name='clear', description="Supprimer des messages")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    amount='Le nombre de messages à supprimer (maximum 100).',
)
async def clear_slash(interaction: discord.Interaction, amount: int, channel: discord.TextChannel = None):
    guild = interaction.guild

    if amount <= 0:
        await interaction.response.send_message("Veuillez saisir un nombre de messages positif à supprimer.", ephemeral=True)
        return

    amount = min(amount, 100)

    try:
        if channel is None:
            channel = interaction.channel

        embed = discord.Embed(
            title="__**Messages Supprimés**__",
            description="Un modérateur a supprimé des messages !",
            color=0x07f246,
        )
        embed.add_field(
            name="Information Modérateur :",
            value=f"➔ `Utilisateur` : {interaction.user.mention}\n➔ `Nom` : {interaction.user.name}\n➔ `ID` : {interaction.user.id}\n➔ `Bot` : {interaction.user.bot}",
            inline=False,
        )
        embed.add_field(
            name="Information Messages :",
            value=f"➔ `Date` : <t:{int(datetime.now(timezone.utc).timestamp())}:R>\n➔ `Salon` : {channel.mention}\n➔ `Nombre` :\n`{amount}`",
            inline=False,
        )
        embed.set_footer(text=random.choice(funFact))
        embed.timestamp = datetime.now(timezone.utc)

        # Envoi de l'embed de confirmation
        await interaction.response.send_message(embed=embed, ephemeral=True)
        await channel.purge(limit=amount)

        # Journalisation de l'action avec l'heure actuelle
        logger1.info(f"{interaction.user.mention} a supprimé {amount} messages dans le channel {channel.mention} ({datetime.now(timezone.utc).isoformat()})")
        
        # Envoi du log
        await send_log(embed, guild)

    except discord.Forbidden:
        if not interaction.response.is_done():  # Vérifier si la réponse a déjà été envoyée
            await interaction.response.send_message("Je n'ai pas les permissions nécessaires pour supprimer des messages.", ephemeral=True)
    except discord.HTTPException as e:
        if not interaction.response.is_done():
            await interaction.response.send_message("Une erreur s'est produite lors de la suppression des messages. Veuillez réessayer plus tard.", ephemeral=True)
    except Exception as e:
        if not interaction.response.is_done():
            await interaction.response.send_message("Une erreur inattendue s'est produite. Veuillez réessayer plus tard.", ephemeral=True)
        logger.error(f"Erreur inattendue: {e}")


# Gestion des erreurs pour la commande clear
@clear_slash.error
async def clear_error(interaction: discord.Interaction, error):
    await interaction.response.send_message("Tu n'as pas les permissions !", ephemeral=True)

# Commande pour débannir un membre
@bot.tree.command(name='unban', description="Débannir un membre")
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
    user="L'ID ou le nom d'utilisateur du membre à débannir.",
)
async def unban_slash(interaction: discord.Interaction, user: str, reason: str = None):
    guild = interaction.guild
    try:
        # On suppose que l'ID de l'utilisateur est donné
        user_id = int(user)
        user_obj = discord.Object(id=user_id)
        await guild.unban(user_obj)
    except ValueError:
        # Si l'entrée n'est pas un ID, on tente de débannir par nom
        user_id = None
        async for ban in guild.bans():
            if ban.user.name == user:
                await guild.unban(ban.user)
                user_id = ban.user.id
                break
        if user_id is None:
            await interaction.response.send_message(f"L'utilisateur nommé '{user}' n'a pas été trouvé dans la liste des bannis.", ephemeral=True)
            return
    except discord.NotFound:
        await interaction.response.send_message(f"L'utilisateur avec l'ID {user} n'est pas banni.", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message("Je n'ai pas les permissions suffisantes pour débannir cet utilisateur.", ephemeral=True)
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        await interaction.response.send_message("Une erreur inattendue s'est produite. Veuillez réessayer plus tard.", ephemeral=True)

    embed = discord.Embed(title="Membre débanni", color=discord.Color.green())
    embed.add_field(name="Utilisateur", value=f"<@{user_id}>")
    embed.add_field(name="Modérateur", value=interaction.user.mention)
    embed.add_field(name="Raison", value=reason)
    embed.timestamp = datetime.now()

    await interaction.response.send_message(embed=embed)

    # Log de débannissement
    logger1.info(f"{interaction.user.mention} a débanni: {user} pour la raison suivante: {reason}")
    await send_log(embed, guild)

# Dm un utilisateur
@bot.tree.command(name='dm_user', description="Permet de dm un membre via le bot")
@app_commands.default_permissions(administrator=True)
async def dm(interaction: discord.Interaction, user: discord.User, message: str = None):
    try:

        if not message:
          await interaction.response.send_message(f"Le message ne peux pas être vide", ephemeral=True)

        else:
            await user.send(f"{message}")
            # Différer la réponse pour indiquer à Discord que le bot prend du temps pour traiter la demande
            await interaction.response.defer()
            await interaction.followup.send(f"Message envoyé.", ephemeral=True)
    
    except discord.Forbidden:
        await interaction.followup.send("Je n'ai pas les permissions nécessaires pour récupérer la liste des bannis.", ephemeral=True)
    except discord.HTTPException as e:
        logger.error(f"Erreur lors de la récupération de la liste des bannis : {e}")
        await interaction.followup.send("Une erreur s'est produite lors de la récupération de la liste des bannis. Veuillez réessayer plus tard.", ephemeral=True)
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        await interaction.followup.send("Une erreur inattendue s'est produite. Veuillez réessayer plus tard.", ephemeral=True)



    
    


    






# Commande pour afficher la liste des bannis
@bot.tree.command(name='liste_bans', description="Afficher la liste des membres bannis")
@app_commands.default_permissions(administrator=True)
async def bans(interaction: discord.Interaction):
    guild = interaction.guild

    try:
        bans = guild.bans()  # Récupérer le générateur asynchrone des bannissements

        embed = discord.Embed(title="Liste des membres bannis", color=discord.Color.red())
        embed.set_footer(text=f"Requête effectuée par {interaction.user}")
        embed.timestamp = discord.utils.utcnow()  # Ajouter un timestamp à l'embed

        # Itérer sur le générateur asynchrone avec `async for`
        async for ban in bans:
            user = ban.user
            reason = ban.reason if ban.reason else "Aucune raison spécifiée"
            # Malheureusement, on ne peut pas obtenir directement l'utilisateur qui a banni
            # ou la date du bannissement à partir de l'API Discord.

            # Ajouter les informations disponibles dans l'embed
            embed.add_field(
                name=f"Utilisateur : {user}",
                value=f"**Pseudo** : {user.name}\n**Raison** : {reason}\n**ID** : {user.id}\n**Date de ban** : Inconnue",
                inline=False
            )

        # Si aucun utilisateur n'est banni
        if len(embed.fields) == 0:
            embed.description = "Aucun utilisateur n'est banni sur ce serveur."

        await interaction.response.send_message(embed=embed)

    except discord.Forbidden:
        await interaction.response.send_message("Je n'ai pas les permissions nécessaires pour récupérer la liste des bannis.", ephemeral=True)
    except discord.HTTPException as e:
        logger.error(f"Erreur lors de la récupération de la liste des bannis : {e}")
        await interaction.response.send_message("Une erreur s'est produite lors de la récupération de la liste des bannis. Veuillez réessayer plus tard.", ephemeral=True)
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        await interaction.response.send_message("Une erreur inattendue s'est produite. Veuillez réessayer plus tard.", ephemeral=True)

# Commande pour synchroniser les commandes
@bot.tree.command(name='sync', description="Synchroniser les commandes")
@app_commands.default_permissions(administrator=True)
async def sync(interaction: discord.Interaction):
    try:
        # Tentative de synchronisation des commandes
        synced = await bot.tree.sync()
        print(f"Synced {len(synced)} command(s)")
        await interaction.response.send_message(f"Synchronisé {len(synced)} commande(s).", ephemeral=True)
    except discord.errors.HTTPException as e:
        if e.status == 429:  # Limite de taux atteinte
            retry_after = int(e.response.headers.get('Retry-After', 5))  # Temps à attendre avant de réessayer
            print(f"Rate limit exceeded, retrying after {retry_after} seconds.")
            await asyncio.sleep(retry_after)
            await interaction.response.send_message("Limite de taux atteinte. Veuillez réessayer après un moment.", ephemeral=True)
        else:
            print(f"ERROR: {e}")
            await interaction.response.send_message(f"Erreur : {e}", ephemeral=True)
    except Exception as e:
        print(f"ERROR: {e}")
        await interaction.response.send_message(f"Erreur : {e}", ephemeral=True)


@bot.tree.command(name='logs_channel', description='Permet de définir le channel de logs')
@app_commands.default_permissions(administrator=True)
async def set_logs_channel(interaction: discord.Interaction, logs_channel: discord.TextChannel = None):
    guild = interaction.guild
    
    if logs_channel is None:
        await interaction.response.send_message("Veuillez définir un salon.", ephemeral=True)
        return

    # Vérification des permissions
    if not logs_channel.permissions_for(guild.me).send_messages:
        await interaction.response.send_message(f"Je n'ai pas la permission d'envoyer des messages dans {logs_channel.mention}.", ephemeral=True)
        return

    log_config = {
        'log_channel': logs_channel.id,
    }
    doc_ref = db.collection('servers').document(str(guild.id)).collection('config').document('main')
    
    try:
        doc_ref.update(log_config)

        # Confirmation de la définition du salon
        await logs_channel.send("Le salon de logs a été défini avec succès.")

        # Journalisation dans le fichier de logs
        logger1.info(f"{interaction.user.mention} a défini le salon des logs sur {logs_channel.mention}")

        # Création d'un embed pour le message de log
        embed = discord.Embed(
            title="Salon de logs défini",
            description=f"{interaction.user.mention} a défini le salon des logs sur {logs_channel.mention}",
            color=discord.Color.blue(),
        )

        # Envoi du message de confirmation à l'utilisateur
        await interaction.response.send_message(f"Le salon des logs a été défini sur {logs_channel.mention}.", ephemeral=True)

        # Envoi de l'embed de log via la fonction send_log
        await send_log(embed, guild)

    except Exception as e:
        logger.error(f"Erreur lors de la définition du salon de logs: {e}")
        await interaction.response.send_message("Une erreur s'est produite lors de la définition du salon de logs. Veuillez réessayer plus tard.", ephemeral=True)

        
@bot.tree.command(name='invite', description='Génère une invitation pour le serveur')
async def sync(interaction: discord.Interaction):
    channel = interaction.channel
    
    try:
        invite = await channel.create_invite(max_age=100, max_uses=100)
        await interaction.response.send_message(f"{invite.url}")
    
    except discord.Forbidden:
        await interaction.response.send_message("Je n'ai pas les permissions nécessaires pour récupérer la liste des bannis.", ephemeral=True)
    except discord.HTTPException as e:
        logger.error(f"Erreur lors de la récupération de la liste : {e}")
        await interaction.response.send_message("Une erreur s'est produite lors de la récupération de la liste des bannis. Veuillez réessayer plus tard.", ephemeral=True)
    except Exception as e:
        logger.error(f"Erreur inattendue: {e}")
        await interaction.response.send_message("Une erreur inattendue s'est produite. Veuillez réessayer plus tard.", ephemeral=True)



@bot.tree.command(name='kick', description='Permet de kick un membre')
@app_commands.default_permissions(administrator=True)
@app_commands.describe(
   user ="id du membre a kick",
)
async def kick(interaction: discord.Interaction, user: discord.Member, reason: str = None):
    guild = interaction.guild
    try:
        # vérifie si l'ustilisateur a kick est le bot
        if user == interaction.client.user:
            await interaction.response.send_message("Je ne peux pas m'expulser moi-même !", ephemeral=True)
            return
        # Si aucune raison n'est fournie, on en fournit une par défaut
        if reason is None:
            reason = "Aucune raison fournie"

        # Envoi d'un message privé à l'utilisateur kické
        await user.send(embed=discord.Embed(
            title=f":rotating_light: Tu as été expulsé du serveur {guild.name}",
            description=f"Tu as été expulsé pour la raison suivante : **{reason}**",
            color=0xff0000
        ))

        # Kick de l'utilisateur
        await user.kick(reason=reason)

        # Création et envoi de l'embed confirmant l'expulsion dans le canal
        embed = discord.Embed(title="Membre expulsé", color=discord.Color.green())
        embed.add_field(name="Utilisateur", value=f"{user.mention}")
        embed.add_field(name="Modérateur", value=interaction.user.mention)
        embed.add_field(name="Raison", value=reason)

        await interaction.response.send_message(embed=embed)
        logger1.info(f"{interaction.user.mention} a expulsé: {user.mention} pour la raison suivante: {reason}")
        await send_log(embed, guild)

    except discord.Forbidden:
        await interaction.response.send_message(f"Je n'ai pas les permissions nécessaires pour expulser cet utilisateur.{e}", ephemeral=True)
    except discord.HTTPException as e:
        logger.error(f"Erreur lors de l'expulsion : {e}")
        await interaction.response.send_message("Une erreur s'est produite lors de l'expulsion. Veuillez réessayer plus tard.", ephemeral=True)
    except Exception as e:
        logger.error(f"Erreur inattendue : {e}")
        await interaction.response.send_message("Une erreur inattendue s'est produite. Veuillez réessayer plus tard.", ephemeral=True)




@bot.tree.command(name='countmessages', description='Récupère le nombre de messages postés dans un salon')
@app_commands.default_permissions(administrator=True)
async def count_messages(interaction: discord.Interaction, channel: discord.TextChannel = None):
    try:
        # Si aucun canal n'est spécifié, utiliser le canal de l'interaction
        if channel is None:
            channel = interaction.channel
        
        # Différer la réponse pour indiquer à Discord que le bot prend du temps pour traiter la demande
        await interaction.response.defer()
        
        # Initialiser un compteur pour les messages
        message_count = 0
        
        # On récupère l'historique des messages du canal (générateur asynchrone)
        async for message in channel.history(limit=None):
            message_count += 1  # Incrémenter le compteur de messages

        # Envoyer la réponse avec le nombre de messages
        # Envoyer la réponse avec le nombre de messages en utilisant `followup`
        await interaction.followup.send(f"Il y a {message_count} messages dans le canal {channel.mention}.")
    
    except discord.Forbidden:
        # Si le bot n'a pas la permission de récupérer l'historique des messages
        await interaction.followup.send("Je n'ai pas les permissions nécessaires pour lire l'historique des messages dans ce salon.", ephemeral=True)
    
    except discord.HTTPException as e:
        # En cas d'erreur HTTP (par exemple, si la requête prend trop de temps)
        logger.error(f"Erreur lors de la récupération des messages : {e}")
        await interaction.followup.send("Une erreur s'est produite lors de la récupération des messages. Veuillez réessayer plus tard.", ephemeral=True)
    
    except Exception as e:
        # Autre erreur imprévue
        logger.error(f"Erreur inattendue : {e}")
        await interaction.followup.send("Une erreur inattendue s'est produite. Veuillez réessayer plus tard.", ephemeral=True)


@bot.tree.command(name='dice', description='Récupère le nombre de messages postés dans un salon')
async def count_messages(interaction: discord.Interaction, number_of_faces: int = None):
    if number_of_faces is None:
        await interaction.response.send_message("Vous devez spécifier un nombre de face pour le lancer de dés")
        return
    
    number = random.randint(1, number_of_faces)
    
    await interaction.response.send_message(f"{number}")




    



@bot.tree.command(name="add_server_config", description="Ajoute un serveur à Firestore avec sa configuration.")
@app_commands.default_permissions(administrator=True)  # Limite l'accès aux administrateurs
async def add_server_config(interaction: discord.Interaction):
    guild = interaction.guild  # Utiliser l'ID du serveur comme identifiant

    if interaction.user.id != 857632000121765929:
        await interaction.response.send_message("Tu n'es pas le propriétaire du bot !", ephemeral=True)
        return

    # Vérifier si le serveur est déjà configuré
    config_ref = db.collection('servers').document(str(guild.id)).collection('config').document('main')
    if (config_ref.get()).exists:
        await interaction.response.send_message(f"La configuration pour le serveur {interaction.guild.name} existe déjà.", ephemeral=True)
        return  # Sortir de la fonction après avoir répondu

    # Variables de configuration à enregistrer
    server_config = {
        'log_channel': None,  # ID du salon de logs
        'inactive_role': None,  # ID du rôle inactif
        'created_at': firestore.SERVER_TIMESTAMP  # Date et heure de la création
    }
    server_info = {
        'name': guild.name,  # Nom du serveur
        'id': guild.id,  # ID du serveur
        'guild_creation': guild.created_at,  # Date et heure de la création
        'owner_id': guild.owner.id,
        'created_at': firestore.SERVER_TIMESTAMP  # Date et heure de la création
    }

    try:
        # Crée une collection pour le serveur avec l'ID du serveur
        doc_ref = db.collection('servers').document(str(guild.id))
        doc_ref.set(server_info)  # Sauvegarder les infos générales
        config_ref.set(server_config)  # Sauvegarder la configuration

        # Réponse confirmant que la configuration a été ajoutée
        await interaction.response.send_message(f"La configuration par défaut du serveur {interaction.guild.name} a été ajoutée.", ephemeral=True)

    except Exception as e:
        await interaction.response.send_message(f"Une erreur est survenue lors de l'ajout de la configuration : {str(e)}", ephemeral=True)
        print(f"Erreur lors de l'ajout de la configuration pour {guild.id} : {e}")


@bot.tree.command(name="bonjour")
async def bonjour(interaction: discord.Interaction):
    await interaction.response.send_message(f"Bonjour ! {interaction.user}")

# Commande pour rejoindre un salon vocal
@bot.tree.command(name="join", description="Rejoindre un salon vocal")
async def join(interaction: discord.Interaction):
    channel = interaction.user.voice.channel
    if interaction.guild.voice_client is not None:
        await interaction.guild.voice_client.move_to(channel)
    else:
        await channel.connect()
    await interaction.response.send_message(f"Connecté à {channel}.")


# Commande pour jouer de la musique depuis YouTube
@bot.tree.command(name="play")
async def play(interaction: discord.Interaction, url: str):
    # Déférer l'interaction pour éviter le timeout
    await interaction.response.defer()
    
    # Récupération de la source audio et du titre
    source, title = await get_ytdl_source(url)
    
    # Envoie du message après avoir récupéré les données
    await interaction.followup.send(f"Je joue: {title}")
    
    # Reste de la logique pour lire la musique
    voice_client = interaction.guild.voice_client
    voice_client.play(source)


# Commande pour quitter un salon vocal
@bot.tree.command(name="leave", description="Quitter le salon vocal")
async def leave(interaction: discord.Interaction):
    voice_client = interaction.guild.voice_client
    if voice_client:
        await voice_client.disconnect()
        await interaction.response.send_message("J'ai quitté le salon vocal.")
    else:
        await interaction.response.send_message("Je ne suis dans aucun salon vocal.")

@bot.tree.command(name='speak')
@app_commands.default_permissions(administrator=True)  # Limite l'accès aux administrateurs
async def speak(interaction: discord.Interaction, *, text: str):
    # Vérifier si l'utilisateur est dans un salon vocal
    if interaction.user.voice is None:
        await interaction.response.send_message("Tu dois être dans un salon vocal pour utiliser cette commande.")
        return

    voice_client = discord.utils.get(bot.voice_clients, guild=interaction.guild)

    if not voice_client:
        # Se connecter au salon vocal
        channel = interaction.user.voice.channel
        voice_client = await channel.connect()

    # Générer le fichier audio à partir du texte
    tts = gTTS(text=text, lang='fr')
    
    # Créer un fichier temporaire pour le son
    with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as fp:
        tts.save(fp.name)
        audio_source = discord.FFmpegPCMAudio(fp.name)
        voice_client.play(audio_source)

    await interaction.response.send_message(f"Je vais parler: {text}", ephemeral=True)
    #######################################################################################
#money
@bot.tree.command(name="setup_points", description="Activer ou désactiver le système de points")
@app_commands.default_permissions(administrator=True)  # Limite l'accès aux administrateurs
@app_commands.default_permissions(administrator=True)  # Seulement les admins peuvent utiliser cette commande
async def toggle_points(interaction: discord.Interaction, etat: bool):
    guild_id = interaction.guild.id

    # Stocker l'état du système de points dans Firestore
    config_ref = db.collection('servers').document(str(guild_id)).collection('config').document('points_system')
    config_ref.set({
        'enabled': etat
    })

    if etat:
        await interaction.response.send_message("Le système de points est maintenant activé.")
    else:
        await interaction.response.send_message("Le système de points est maintenant désactivé.")

@bot.tree.command(name="check_points_status", description="Vérifier l'état du système de points")
@app_commands.default_permissions(administrator=True)  # Limite l'accès aux administrateurs
async def check_points_status(interaction: discord.Interaction):
    guild_id = interaction.guild.id

    # Vérifier si le système de points est activé
    config_ref = db.collection('servers').document(str(guild_id)).collection('config').document('points_system')
    config = config_ref.get().to_dict()

    if config and config.get('enabled', False):
        await interaction.response.send_message("Le système de points est actuellement **activé**.")
    else:
        await interaction.response.send_message("Le système de points est actuellement **désactivé**.")



@bot.tree.command(name="setup_levels", description="Active ou désactive le système de paliers pour le serveur.")
@app_commands.default_permissions(administrator=True)  # Limite l'accès aux administrateurs
@app_commands.describe(enable="Indique si le système de paliers doit être activé ou désactivé.",
                       channel="Le salon où les annonces de niveaux seront envoyées.")
async def toggle_level_system(interaction: discord.Interaction, enable: bool, channel: discord.TextChannel = None):
    guild_id = interaction.guild.id
    
    # Enregistrer l'état du système de niveaux
    db.collection('servers').document(str(guild_id)).collection('config').document('level_system').set({
        'enabled': enable
    }, merge=True)

    if enable:
        if channel:
            # Enregistrer l'ID du salon d'annonces
            db.collection('servers').document(str(guild_id)).collection('config').document('level_channel').set({
                'channel_id': channel.id
            }, merge=True)
            await interaction.response.send_message(f"Système de niveaux activé. Le salon d'annonces est maintenant {channel.mention}.")
        else:
            await interaction.response.send_message("Système de niveaux activé, mais aucun salon d'annonces spécifié. Veuillez mentionner un salon.")
    else:
        # Optionnel : retirer le salon d'annonces si le système est désactivé
        db.collection('servers').document(str(guild_id)).collection('config').document('level_channel').set({
            'channel_id': None
        }, merge=True)
        await interaction.response.send_message("Système de niveaux désactivé.")

@bot.tree.command(name="level", description="Voir le niveau et les points d'un utilisateur.")
@app_commands.describe(user="L'utilisateur dont vous souhaitez voir les points et le niveau.")
async def level(interaction: discord.Interaction, user: discord.User = None):
    guild_id = interaction.guild.id
    user = user or interaction.user  # Si aucun utilisateur n'est mentionné, utiliser l'auteur de l'interaction

    # Vérifier si le système de points est activé
    config_ref = db.collection('servers').document(str(guild_id)).collection('config').document('points_system')
    config = config_ref.get().to_dict()

    if not config or not config.get('enabled', False):
        await interaction.response.send_message("Le système de points n'est pas activé.")
        return

    # Récupérer les données de l'utilisateur
    user_ref = db.collection('servers').document(str(guild_id)).collection('users').document(str(user.id))
    user_data = user_ref.get().to_dict()

    if user_data:
        points = user_data.get('points', 0)
        level = user_data.get('level', 0)
        await interaction.response.send_message(f"{user.name} a {points} points et est au niveau {level}.")
    else:
        await interaction.response.send_message(f"Aucune donnée trouvée pour {user.name}.")

@bot.tree.command(name="adminadd_points", description="Ajouter des points à un utilisateur.")
@app_commands.default_permissions(administrator=True)  # Limite l'accès aux administrateurs
@app_commands.describe(user="L'utilisateur à qui vous souhaitez ajouter des points.", amount="Le nombre de points à ajouter.")
async def add_points(interaction: discord.Interaction, user: discord.User, amount: int):
    guild_id = interaction.guild.id

    # Vérifier si le système de points est activé
    config_ref = db.collection('servers').document(str(guild_id)).collection('config').document('points_system')
    config = config_ref.get().to_dict()

    if not config or not config.get('enabled', False):
        await interaction.response.send_message("Le système de points n'est pas activé.")
        return

    user_id = str(user.id)
    user_ref = db.collection('servers').document(str(guild_id)).collection('users').document(user_id)
    user_data = user_ref.get().to_dict()

    if user_data:
        current_points = user_data.get('points', 0)
        new_points = current_points + amount
        user_ref.set({'points': new_points}, merge=True)
        await interaction.response.send_message(f"{amount} points ajoutés à {user.name}. Total maintenant : {new_points}.")
    else:
        await interaction.response.send_message(f"Aucune donnée trouvée pour {user.name}.")

@bot.tree.command(name="adminremove_points", description="Retirer des points à un utilisateur.")
@app_commands.default_permissions(administrator=True)  # Limite l'accès aux administrateurs
@app_commands.describe(user="L'utilisateur dont vous souhaitez retirer des points.", amount="Le nombre de points à retirer.")
async def remove_points(interaction: discord.Interaction, user: discord.User, amount: int):
    guild_id = interaction.guild.id

    # Vérifier si le système de points est activé
    config_ref = db.collection('servers').document(str(guild_id)).collection('config').document('points_system')
    config = config_ref.get().to_dict()

    if not config or not config.get('enabled', False):
        await interaction.response.send_message("Le système de points n'est pas activé.")
        return

    user_id = str(user.id)
    user_ref = db.collection('servers').document(str(guild_id)).collection('users').document(user_id)
    user_data = user_ref.get().to_dict()

    if user_data:
        current_points = user_data.get('points', 0)
        new_points = max(0, current_points - amount)
        user_ref.set({'points': new_points}, merge=True)
        await interaction.response.send_message(f"{amount} points retirés à {user.name}. Total maintenant : {new_points}.")
    else:
        await interaction.response.send_message(f"Aucune donnée trouvée pour {user.name}.")

@bot.tree.command(name="adminset_level", description="Définir le niveau d'un utilisateur.")
@app_commands.default_permissions(administrator=True)  # Limite l'accès aux administrateurs
@app_commands.describe(user="L'utilisateur dont vous souhaitez définir le niveau.", level="Le niveau à attribuer à l'utilisateur.")
async def set_level(interaction: discord.Interaction, user: discord.User, level: int):
    guild_id = interaction.guild.id

    # Vérifier si le système de niveaux est activé
    config_ref = db.collection('servers').document(str(guild_id)).collection('config').document('level_system')
    config = config_ref.get().to_dict()

    if not config or not config.get('enabled', False):
        await interaction.response.send_message("Le système de niveaux n'est pas activé.")
        return

    user_id = str(user.id)
    user_ref = db.collection('servers').document(str(guild_id)).collection('users').document(user_id)
    user_data = user_ref.get().to_dict()

    if user_data:
        user_ref.set({'level': level}, merge=True)
        await interaction.response.send_message(f"Niveau de {user.name} défini sur {level}.")
    else:
        await interaction.response.send_message(f"Aucune donnée trouvée pour {user.name}.")


@bot.tree.command(name="bouton", description="Affiche un bouton cliquable")

async def bouton(interaction: discord.Interaction):
    # Créer une vue
    view = discord.ui.View()

    # Ajouter un bouton directement dans la vue
    bouton = discord.ui.Button(label="Clique ici", style=discord.ButtonStyle.primary)
    
    # Définir le comportement du bouton
    async def bouton_callback(interaction: discord.Interaction):
        await interaction.response.send_message("Tu as cliqué sur le bouton!", ephemeral=True)

    # Associer le callback au bouton
    bouton.callback = bouton_callback
    view.add_item(bouton)

    # Envoyer le message avec le bouton
    await interaction.response.send_message("Voici un bouton :", view=view)


@bot.tree.command(name="roletemp", description="Ajoute un rôle temporaire à un utilisateur pour une durée spécifiée.")
@app_commands.default_permissions(administrator=True)  # Limite l'accès aux administrateurs
@app_commands.describe(
    member="Le membre à qui attribuer le rôle",
    role="Le rôle à attribuer temporairement",
    duration="La durée en secondes pendant laquelle le rôle sera attribué"
)
async def role_temp(interaction: discord.Interaction, member: discord.Member, role: discord.Role, duration: int):
    # Vérification des permissions du bot
    if not interaction.guild.me.guild_permissions.manage_roles:
        await interaction.response.send_message("Je n'ai pas la permission de gérer les rôles.", ephemeral=True)
        return
    
    # Vérification si le rôle est au-dessus du rôle du bot
    if role >= interaction.guild.me.top_role:
        await interaction.response.send_message("Je ne peux pas gérer ce rôle car il est supérieur ou égal à mon rôle.", ephemeral=True)
        return
    
    # Vérification de la durée
    if duration <= 0:
        await interaction.response.send_message("La durée doit être supérieure à 0 seconde.", ephemeral=True)
        return

    try:
        await member.add_roles(role)
        await interaction.response.send_message(
            f"Le rôle {role.mention} a été attribué à {member.mention} pour {duration} seconde(s)."
        )
        await asyncio.sleep(duration)
        await member.remove_roles(role)
        await interaction.followup.send(f"Le rôle {role.mention} a été retiré de {member.mention} après {duration} seconde(s).")
    except discord.Forbidden:
        await interaction.response.send_message("Je n'ai pas les permissions nécessaires pour gérer les rôles.", ephemeral=True)
    except Exception as e:
        await interaction.response.send_message(f"Une erreur est survenue : {e}", ephemeral=True)





bot.run("")     

