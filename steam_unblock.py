"""Steam Unblock: local proxy that only handles Steam websites.

The ISP drops HTTPS connections whose TLS ClientHello contains a Steam
hostname (SNI). This proxy splits the ClientHello into several TLS records
so the filter cannot read the hostname. No decryption, no certificates.

Only Steam domains are routed here, via a PAC file set in Windows proxy
settings while the app runs. Everything else (games, other sites) stays DIRECT.
Stopping or closing the app restores the previous Windows setting.

Needs:  pip install pystray pillow
Build the .exe:  python -m PyInstaller --onefile --windowed --hidden-import pystray._win32 --add-data "assets;assets" --name SteamUnblock steam_unblock.py
"""
import asyncio
import ctypes
import os
import queue
import sys
import threading
import tkinter as tk
import winreg
from tkinter import messagebox

import pystray
from PIL import Image, ImageDraw

PORT = 8899
STEAM_DOMAINS = (
    "steampowered.com",
    "steamcommunity.com",
    "steamstatic.com",
    "steamusercontent.com",
    "steam-chat.com",
)
REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Internet Settings"
PAC_URL = f"http://127.0.0.1:{PORT}/steam.pac"

PAC = (
    "function FindProxyForURL(url, host) {\n"
    + "".join(
        f'  if (dnsDomainIs(host, "{d}") || host == "{d}") return "PROXY 127.0.0.1:{PORT}; DIRECT";\n'
        for d in STEAM_DOMAINS
    )
    + '  return "DIRECT";\n}\n'
)


def is_steam(host):
    host = host.lower().rstrip(".")
    return any(host == d or host.endswith("." + d) for d in STEAM_DOMAINS)


def fragment_client_hello(data, host):
    """Re-pack one TLS handshake record into several records, cutting inside the SNI."""
    if len(data) < 5 or data[0] != 0x16:
        return [data]
    rec_len = int.from_bytes(data[3:5], "big")
    payload, rest = data[5:5 + rec_len], data[5 + rec_len:]
    i = payload.find(host.encode())
    cuts = [1, i + len(host) // 2] if i > 0 else [1, len(payload) // 2]
    parts, prev = [], 0
    for c in sorted(set(cuts)) + [len(payload)]:
        if c > prev:
            chunk = payload[prev:c]
            parts.append(data[:3] + len(chunk).to_bytes(2, "big") + chunk)
            prev = c
    if rest:
        parts.append(rest)
    return parts


async def pipe(reader, writer):
    try:
        while data := await reader.read(65536):
            writer.write(data)
            await writer.drain()
    except (ConnectionError, OSError):
        pass
    finally:
        writer.close()


async def handle(c_reader, c_writer):
    try:
        head = await c_reader.readuntil(b"\r\n\r\n")
    except (asyncio.IncompleteReadError, asyncio.LimitOverrunError, ConnectionError):
        c_writer.close()
        return
    method, target, _ = head.split(b"\r\n", 1)[0].decode("latin-1").split(" ", 2)

    if method == "GET" and target == "/steam.pac":
        body = PAC.encode()
        c_writer.write(b"HTTP/1.1 200 OK\r\nContent-Type: application/x-ns-proxy-autoconfig\r\n"
                       b"Content-Length: %d\r\nConnection: close\r\n\r\n" % len(body) + body)
        await c_writer.drain()
        c_writer.close()
        return

    if method == "CONNECT":
        host, _, port = target.rpartition(":")
        port = int(port)
    else:  # plain http:// request (Steam redirects these to https)
        hostport = target.split("://", 1)[-1].split("/", 1)[0]
        host, _, port = hostport.partition(":")
        port = int(port or 80)

    # Never become an open proxy for non-Steam traffic.
    if not is_steam(host):
        c_writer.write(b"HTTP/1.1 403 Forbidden\r\nConnection: close\r\n\r\n")
        await c_writer.drain()
        c_writer.close()
        return

    try:
        s_reader, s_writer = await asyncio.wait_for(asyncio.open_connection(host, port), 15)
    except (OSError, asyncio.TimeoutError):
        c_writer.write(b"HTTP/1.1 502 Bad Gateway\r\nConnection: close\r\n\r\n")
        await c_writer.drain()
        c_writer.close()
        return

    if method == "CONNECT":
        c_writer.write(b"HTTP/1.1 200 Connection Established\r\n\r\n")
        await c_writer.drain()
        hello = await c_reader.read(65536)
        for part in fragment_client_hello(hello, host):
            s_writer.write(part)
            await s_writer.drain()
            await asyncio.sleep(0.005)  # separate TCP segments too
    else:
        s_writer.write(head)
        await s_writer.drain()

    await asyncio.gather(pipe(c_reader, s_writer), pipe(s_reader, c_writer))


def refresh_wininet():
    wininet = ctypes.windll.wininet
    wininet.InternetSetOptionW(0, 39, 0, 0)  # INTERNET_OPTION_SETTINGS_CHANGED
    wininet.InternetSetOptionW(0, 37, 0, 0)  # INTERNET_OPTION_REFRESH


def set_pac(url):
    """Set (or clear, if url is None) the Windows PAC URL. Returns the previous value."""
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, REG_PATH, 0, winreg.KEY_ALL_ACCESS) as key:
        try:
            old = winreg.QueryValueEx(key, "AutoConfigURL")[0]
        except FileNotFoundError:
            old = None
        if url:
            winreg.SetValueEx(key, "AutoConfigURL", 0, winreg.REG_SZ, url)
        else:
            try:
                winreg.DeleteValue(key, "AutoConfigURL")
            except FileNotFoundError:
                pass
    refresh_wininet()
    return old


RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_NAME = "SteamUnblock"


def startup_command():
    """Command Windows runs at login: this exe (or pythonw + this script), starting hidden in the tray."""
    if getattr(sys, "frozen", False):
        return f'"{sys.executable}" --minimized'
    pythonw = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")
    return f'"{pythonw}" "{os.path.abspath(__file__)}" --minimized'


def get_startup():
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY) as key:
            winreg.QueryValueEx(key, RUN_NAME)
        return True
    except FileNotFoundError:
        return False


def set_startup(on):
    with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_KEY, 0, winreg.KEY_SET_VALUE) as key:
        if on:
            winreg.SetValueEx(key, RUN_NAME, 0, winreg.REG_SZ, startup_command())
        else:
            try:
                winreg.DeleteValue(key, RUN_NAME)
            except FileNotFoundError:
                pass


def self_test():
    host = "store.steampowered.com"
    payload = b"\x01\x00\x00\x50" + b"x" * 20 + host.encode() + b"y" * 20
    rec = b"\x16\x03\x01" + len(payload).to_bytes(2, "big") + payload
    parts = fragment_client_hello(rec, host)
    assert len(parts) == 3
    assert b"".join(p[5:] for p in parts) == payload
    assert all(p[:3] == b"\x16\x03\x01" for p in parts)
    assert host.encode() not in b"".join(parts)
    assert is_steam("store.steampowered.com") and is_steam("steamcommunity.com")
    assert not is_steam("evilsteampowered.com") and not is_steam("google.com")
    assert startup_command().endswith(" --minimized") and startup_command().startswith('"')
    print("self-test OK")


# Inside a PyInstaller exe, bundled files are unpacked to sys._MEIPASS.
ASSETS = os.path.join(getattr(sys, "_MEIPASS", os.path.dirname(os.path.abspath(__file__))), "assets")


def tray_image(color, icon):
    """Status-colored circle with a white Kenney padlock (assets/, CC0) on top."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    ImageDraw.Draw(img).ellipse((0, 0, 63, 63), fill=color)
    glyph = Image.open(os.path.join(ASSETS, icon)).convert("RGBA").resize((40, 40), Image.LANCZOS)
    img.alpha_composite(glyph, (12, 12))
    return img


class App:
    """Small window with a Start/Stop button plus a tray icon; minimizing hides the window to the tray.
    The proxy runs on an asyncio loop in a background thread."""

    def __init__(self, minimized=False):
        self.loop = asyncio.new_event_loop()
        threading.Thread(target=self.loop.run_forever, daemon=True).start()
        self.server = None
        self.restore = None
        self.alive = True  # False once the window is destroyed

        self.root = tk.Tk()
        self.root.title("Steam Unblock")
        self.root.resizable(False, False)
        self.status = tk.Label(self.root, width=44, pady=12, font=("Segoe UI", 10))
        self.status.pack(padx=16, pady=(12, 0))
        self.button = tk.Button(self.root, width=14, font=("Segoe UI", 10), command=self.toggle)
        self.button.pack(pady=(4, 8))
        self.startup = tk.BooleanVar(value=get_startup())
        tk.Checkbutton(self.root, text="Run at Windows startup", variable=self.startup,
                       font=("Segoe UI", 9), command=self.apply_startup).pack(pady=(0, 12))
        if self.startup.get():
            set_startup(True)  # refresh the saved path in case the exe was moved
        self.root.protocol("WM_DELETE_WINDOW", self.quit)
        self.root.bind("<Unmap>", self.on_unmap)

        # Tray callbacks run on pystray's thread and Tk is not thread-safe: queue them, Tk polls.
        self.actions = queue.SimpleQueue()
        self.tray = pystray.Icon("SteamUnblock", tray_image("#888888", "locked.png"), "Steam Unblock", menu=pystray.Menu(
            pystray.MenuItem("Show", lambda: self.actions.put(self.show), default=True),
            pystray.MenuItem(lambda item: "Stop" if self.server else "Start",
                             lambda: self.actions.put(self.toggle)),
            pystray.MenuItem("Run at Windows startup", lambda: self.actions.put(self.toggle_startup),
                             checked=lambda item: self.startup.get()),
            pystray.MenuItem("Quit", lambda: self.actions.put(self.quit)),
        ))
        # start() first: pystray caches the icon it shows first and misses a change made during setup,
        # which left the icon gray while running.
        self.start()
        if self.alive:
            self.tray.run_detached()
            if minimized:
                self.root.withdraw()
            self.poll()

    def poll(self):
        while self.alive and not self.actions.empty():
            self.actions.get()()
        if self.alive:
            self.root.after(100, self.poll)

    def on_unmap(self, event):
        if event.widget is self.root and self.root.state() == "iconic":
            self.root.withdraw()  # off the taskbar; the tray icon brings it back

    def show(self):
        self.root.deiconify()
        self.root.lift()
        self.root.focus_force()

    def set_tray(self, color, icon, title):
        self.tray.icon = tray_image(color, icon)
        self.tray.title = title
        self.tray.update_menu()

    def start(self):
        try:
            self.server = asyncio.run_coroutine_threadsafe(
                asyncio.start_server(handle, "127.0.0.1", PORT), self.loop).result()
        except OSError:
            messagebox.showerror("Steam Unblock", f"Port {PORT} is busy. Is Steam Unblock already running?")
            if self.tray.visible:
                self.tray.stop()
            self.alive = False
            self.root.destroy()
            return
        old = set_pac(PAC_URL)
        self.restore = old if old != PAC_URL else None  # PAC_URL here means a previous run crashed
        self.status.config(text="Running: Steam Store unblocked.\nRestart Steam once if it still shows -101.",
                           fg="#1a7f37")
        self.button.config(text="Stop")
        self.set_tray("#1a7f37", "unlocked.png", "Steam Unblock: running")

    def stop(self):
        if self.server:
            set_pac(self.restore)
            # Don't wait for open tunnels: they end on their own, the setting is already restored.
            self.loop.call_soon_threadsafe(self.server.close)
            self.server = None
        self.status.config(text="Stopped. Windows proxy setting restored.", fg="#555555")
        self.button.config(text="Start")
        self.set_tray("#888888", "locked.png", "Steam Unblock: stopped")

    def toggle(self):
        self.stop() if self.server else self.start()

    def apply_startup(self):
        set_startup(self.startup.get())
        self.tray.update_menu()

    def toggle_startup(self):
        self.startup.set(not self.startup.get())
        self.apply_startup()

    def quit(self):
        self.stop()
        self.tray.stop()
        self.alive = False
        self.root.destroy()


if __name__ == "__main__":
    if "--test" in sys.argv:
        self_test()
    else:
        app = App(minimized="--minimized" in sys.argv)
        if app.alive:
            app.root.mainloop()
