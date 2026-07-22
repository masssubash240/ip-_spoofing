# ⚡ GOD OF CYBER — Local IP Changer

> Auto-rotate your machine's local network IP address on a timer. Built for lab/testing environments — flush your current interface IP and reassign a random one within the same subnet, hands-free.

---

## 📌 What it does

- Detects your active network interface automatically
- Flushes (removes) the current IP on that interface
- Assigns a new random IP within the same subnet
- Repeats on a configurable interval
- Restores default gateway route after each change

**Scope note:** this rotates your **local/LAN IP** on your own interface. It does not touch your public/internet-facing IP (that's assigned by your ISP), and it is not a packet-spoofing tool — it's an interface configuration utility, similar in spirit to `dhclient` or `nmcli`.

---

## 🖥️ Requirements

- Linux (tested on Kali / Debian-based distros)
- Python 3
- Root privileges (`sudo`)
- `iproute2` (`ip` command — preinstalled on most distros)

---

## 🚀 Usage

Clone and run:

```bash
git clone https://github.com/masssubash240/ip-_spoofing.git
cd god-of-cyber-spoof ip.py
sudo python3 spoof ip.py
```

**Examples:**

```bash
# Auto-detect interface, change every 10s (default)
sudo python3 auto_ip_changer.py

# Specific interface, change every 5s
sudo python3 spoof ip.py eth0 5
```

Stop anytime with `Ctrl+C`.

---

## ⚠️ Use responsibly

Run this only on interfaces/networks you own or have explicit permission to test on — an isolated lab, a VM range, or a home network you control. Reassigning IPs on a network you don't manage can knock other devices offline via address conflicts.

---

## 🧠 Part of the GOD OF CYBER toolkit

Built by [Subash](https://godofcybertech.vercel.app) — Team Anonymous.

More tools: [github.com/masssubash240](https://github.com/masssubash240)
