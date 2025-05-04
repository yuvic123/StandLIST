from dotenv import load_dotenv
import discord
import requests
import json
import base64
import re
import os
from keep_alive import keep_alive

load_dotenv()

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

GITHUB_API_URL = "https://api.github.com/repos/yuvic123/StandLIST/contents/LISTSTAND"
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
DISCORD_TOKEN = os.getenv("DISCORD_TOKEN")

ALLOWED_USERS = [
    1279868613628657860,
    598460565387476992,
    1272478153201422420,
    1197823319123165218,
    835401509373476885
]

def update_github_file(new_content, sha):
    updated_content = base64.b64encode(new_content.encode('utf-8')).decode('utf-8')
    data = {
        "message": "Update Stand Roblox ID list",
        "content": updated_content,
        "sha": sha
    }
    response = requests.put(
        GITHUB_API_URL,
        headers={"Authorization": f"token {GITHUB_TOKEN}"},
        json=data
    )
    if response.status_code == 200:
        print("File updated successfully!")
    else:
        print(f"Failed to update file: {response.status_code} - {response.text}")

def get_roblox_usernames(user_ids):
    url = "https://users.roblox.com/v1/users"
    data = {"userIds": user_ids}
    try:
        response = requests.post(url, json=data)
        if response.status_code == 200:
            return {user['id']: user['name'] for user in response.json()['data']}
        else:
            return {}
    except Exception as e:
        print(f"Error fetching usernames: {e}")
        return {}

@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    await client.change_presence(activity=discord.Game(name="Listening to Commands"))

@client.event
async def on_message(message):
    if not message.content.startswith((".addstand", ".standreplace", ".antistandcheck")):
        return

    response = requests.get(GITHUB_API_URL, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    if response.status_code != 200:
        await message.channel.send(f"❌ Error fetching file: {response.status_code} - {response.text}")
        return

    file_data = response.json()
    file_content = base64.b64decode(file_data["content"]).decode('utf-8')
    existing_ids = list(map(int, re.findall(r'\d+', file_content)))
    id_map = {}
    for line in file_content.splitlines():
        match = re.match(r'(\d+) -- (.+)', line)
        if match:
            id_map[int(match.group(1))] = match.group(2)

    if message.content.startswith(".addstand"):
        try:
            parts = message.content.split()
            target_discord_user = message.mentions[0]
            roblox_id = int(parts[2])
        except (IndexError, ValueError):
            await message.channel.send("❌ Invalid format. Use .addstand @user <robloxid>")
            return

        if roblox_id in existing_ids:
            await message.channel.send(f"⚠️ Roblox ID {roblox_id} is already in the list.")
        else:
            existing_ids.append(roblox_id)
            user_tag = f"@{target_discord_user.name}#{target_discord_user.discriminator}"
            id_map[roblox_id] = user_tag
            usernames = get_roblox_usernames([roblox_id])
            username = usernames.get(roblox_id, "Unknown User")
            embed = discord.Embed(
                title="✅ Successfully Added!",
                description=f"**{roblox_id}** - **{username}** has been added to the whitelist for {user_tag}.",
                color=discord.Color.blue()
            )
            await message.channel.send(embed=embed)

    elif message.content.startswith(".standreplace"):
        try:
            _, old_id, new_id = message.content.split(" ")
            old_id, new_id = int(old_id), int(new_id)
        except (ValueError, IndexError):
            await message.channel.send("❌ Invalid format. Use .standreplace <old_id> <new_id>")
            return

        user_tag = f"@{message.author.name}#{message.author.discriminator}"
        if id_map.get(old_id) != user_tag:
            await message.channel.send("❌ You can only replace your own Roblox ID.")
            return

        if new_id in existing_ids:
            await message.channel.send("⚠️ The new ID is already whitelisted.")
            return

        existing_ids.remove(old_id)
        id_map.pop(old_id)
        existing_ids.append(new_id)
        id_map[new_id] = user_tag
        await message.channel.send(f"✅ Successfully replaced **{old_id}** with **{new_id}**.")

    elif message.content.startswith(".antistandcheck"):
        user_tag = f"@{message.author.name}#{message.author.discriminator}"
        matched_ids = [uid for uid, owner in id_map.items() if owner == user_tag]
        if not matched_ids:
            await message.channel.send("❌ You don't have any Roblox ID whitelisted.")
            return

        usernames = get_roblox_usernames(matched_ids)
        description = "\n".join([f"{uid} - **{usernames.get(uid, 'Unknown User')}**" for uid in matched_ids])
        embed = discord.Embed(title=f"🌟 Stand Check for {user_tag}", description=description, color=discord.Color.gold())
        await message.channel.send(embed=embed)

    updated_lines = []
    for uid in sorted(existing_ids):
        if uid in id_map:
            updated_lines.append(f"  {uid} -- \"{id_map[uid]}\"")
        else:
            print(f"Warning: No entry for {uid} in id_map.")
            updated_lines.append(f"  {uid} -- \"Unknown User\"")

    updated_lua_content = "\n".join(updated_lines) + "\nreturn {"
    update_github_file(updated_lua_content, file_data["sha"])

keep_alive()
client.run(DISCORD_TOKEN)
