# Discord Music Bot

🔶 This is a simple Discord bot with music features written in Python.

---

### ℹ️ Common features:

- Multiple server support
- Caching of playing tracks and playlists
- Playback of audio from audio and video files
- Interactive mode, allowing you to play music without using commands
- Dynamically updating music player in the form of an interactive message
- Ability to save nicknames for tracks for quick launch

## 🚀 Quick start:

1. Clone the repository:
```cmd
git clone https://github.com/denisnumb/discord-music-bot.git
```
2. Set up the configuration file (`config.json`):
```json
{
    "token": ". . .",
    "guild_ids": [78489392814341232424333],
    "playlistend": 100,
    "locale": "en_us"
}
```
3. Set up the `data/cookies.txt` file using [`Get cookies.txt LOCALLY`](https://chromewebstore.google.com/detail/get-cookiestxt-locally/cclelndahbckbenkjhflpdbgdldlbecc) (Optional)

- 🐍 Run simple
```cmd
python src/main.py
```

- 🐋 Run using docker:
```cmd
docker compose up --build
```

## 🎵 Usage example:

1. Create a new text channel to control tracks or select an existing one.

2. Set it as a music channel using the command `/set_dj_channel`

![image](https://github.com/user-attachments/assets/ffe35b12-39f3-46f5-876f-3490aa3b0f84)

![image](https://github.com/user-attachments/assets/c9a2611b-42ff-482e-baee-c79a0a4481b6)

---

3. Connect to the voice channel

ℹ️ To play tracks, you can use the command `/play` or simply send a link to a video or playlist to the selected music channel as a regular text message.

- `/play` command example:

![play](https://github.com/user-attachments/assets/b7eea43d-65d9-4433-82b7-bd7767010c90)

Other command parameters:

- `file` — attach audio/video file from your device
- `insert` — Play track next (out of order)
- `mix` — Shuffle tracks in the added playlist
- `mix_with_queue` — Shuffle added tracks with the existing playback queue

ℹ️ Or just send the link in a text channel

![play](https://github.com/user-attachments/assets/d00bb112-b6cb-4cf4-b346-13db09fe5705)

---

ℹ️ You can also send any text to the selected music channel and the bot will offer to search for a track based on the specified request.

![query](https://github.com/user-attachments/assets/4ad094e0-f42b-44cc-b986-b92ac07e71c9)

![query](https://github.com/user-attachments/assets/cbfd8363-1225-4954-acb5-427f5438311b)

![image](https://github.com/user-attachments/assets/fd6c2416-9766-4921-a2ca-2f1cb577978e)

--- 

ℹ️ You can add quick launch titles for tracks using the command `/play_save`

![image](https://github.com/user-attachments/assets/b934ed8c-a2d6-41e7-a5d2-472d0814acac)

![image](https://github.com/user-attachments/assets/ad2a00be-176e-4e0b-9b15-b86334e6ac3c)

---

ℹ️ You can view the full list of saved tracks using the command `/tracklist`

![image](https://github.com/user-attachments/assets/dd294e31-85d1-47ae-9628-d8e9564ef680)

---

ℹ️ Now you can play a track simply by sending the saved title as a regular message in the chat

![image](https://github.com/user-attachments/assets/77286d1c-037d-4717-ac98-2e1db9754de7)

![image](https://github.com/user-attachments/assets/5cac6597-6e05-4219-8567-b1087335f4c1)

---

ℹ️ You can attach audio and video files to a message and specify multiple tracks to add to the queue by separating links and titles with a comma.

![image](https://github.com/user-attachments/assets/7ef7302c-1d1f-4d96-9457-76814195f474)

In this case:

- `rickroll` — saved quick launch name
- `alan walker faded` — a track search will be performed for this request

![image](https://github.com/user-attachments/assets/35cb2299-b49d-4c12-943f-454d11f9c611)



