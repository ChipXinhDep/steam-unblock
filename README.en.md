# Steam Unblock

> [!TIP]
> 🇻🇳 **Tiếng Việt (bản chính): [README.md](README.md)**

A small Windows tray app that gets the Steam Store and Community pages working again
when an ISP blocks them, **without a VPN and without touching games or any other traffic.**

Typical symptom: the Steam client shows **Error Code: -101** on the Store/Community tabs
and the browser shows `ERR_CONNECTION_RESET` for `store.steampowered.com`, while games
still play fine.

> **Not affiliated with or endorsed by Valve Corporation.** "Steam" is a trademark of Valve Corporation.

## How it works

Some ISPs block Steam by reading the website name (SNI) in the first packet of an HTTPS
connection and resetting the connection. This app runs a tiny proxy on `127.0.0.1:8899`
that splits that first packet into several pieces, so the filter can't read the name.
Nothing is decrypted, no certificate is installed, and traffic goes straight to Steam's
own servers (no third-party server in between).

Only these domains are routed through it, using a Windows proxy auto-config (PAC) file:

`steampowered.com`, `steamcommunity.com`, `steamstatic.com`, `steamusercontent.com`, `steam-chat.com`

Everything else, including games and game downloads, connects directly as before.
The proxy also refuses any request that is not for those domains.

## Usage

1. Download `SteamUnblock.exe` from [Releases](../../releases) and run it.
2. Restart Steam once.
3. Minimize to send it to the tray (open padlock on green = running, closed padlock on gray = stopped).
   Right-click the tray icon for Show / Stop / Quit.

**What it changes on your PC:** while running, it sets the Windows "automatic proxy
setup script" (`AutoConfigURL` under `HKCU\...\Internet Settings`). Stopping or closing
the app restores your previous setting. If the app is killed, the leftover setting is
harmless: Steam pages just go direct again (blocked as before), other sites are unaffected.
Running the app again and closing it cleans it up.

Windows SmartScreen or antivirus may warn about an unsigned PyInstaller app. The exe in
Releases is built from this source by GitHub Actions, see `.github/workflows/release.yml`.

## Limitations

- Works only against SNI-based blocking (the case on the networks it was tested on).
  An ISP that changes its filtering method can make it stop working.
- Windows only.

## Run from source / build

```
pip install -r requirements.txt
python steam_unblock.py          # run
python steam_unblock.py --test   # self-test
pip install pyinstaller
python -m PyInstaller --onefile --windowed --hidden-import pystray._win32 --add-data "assets;assets" --name SteamUnblock steam_unblock.py
```

## Disclaimer

Provided "as is", without warranty (see [LICENSE](LICENSE)). You are responsible for
making sure using it is allowed where you live.

## License

MIT, see [LICENSE](LICENSE). Third-party components: [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md).
