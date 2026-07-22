
import subprocess
import os
import sys
import re
import time
import random


class LinuxIPChanger:
    def __init__(self):
        if os.geteuid() != 0:
            print("❌ Run as root: sudo python3 ip_changer.py")
            sys.exit(1)

        self.interface = self.get_active_interface()
        if not self.interface:
            print("❌ No active network interface found.")
            sys.exit(1)

        self.main_menu()

    # ---------- helpers ----------

    def run(self, cmd, check_output=False):
        """Run a command safely, always returning text output."""
        try:
            result = subprocess.run(cmd, capture_output=True, text=True)
            return result
        except FileNotFoundError:
            print(f"❌ Command not found: {cmd[0]} (is it installed?)")
            return None
        except Exception as e:
            print(f"❌ Error running {cmd}: {e}")
            return None

    def get_active_interface(self):
        """Get the interface used for the default route."""
        result = self.run(['ip', 'route', 'show', 'default'])
        if result and result.stdout:
            for line in result.stdout.splitlines():
                if 'default' in line:
                    parts = line.split()
                    if 'dev' in parts:
                        return parts[parts.index('dev') + 1]

        # Fallback: first UP interface that isn't loopback
        result = self.run(['ip', '-o', 'link', 'show', 'up'])
        if result and result.stdout:
            for line in result.stdout.splitlines():
                iface = line.split(':')[1].strip()
                if iface != 'lo':
                    return iface

        return None

    def get_current_ip(self, interface=None):
        interface = interface or self.interface
        result = self.run(['ip', '-4', 'addr', 'show', interface])
        if not result or not result.stdout:
            return "No IP"

        match = re.search(r'inet (\d+\.\d+\.\d+\.\d+)/(\d+)', result.stdout)
        if match:
            return match.group(1)
        return "No IP"

    def get_current_prefix(self, interface=None):
        interface = interface or self.interface
        result = self.run(['ip', '-4', 'addr', 'show', interface])
        if result and result.stdout:
            match = re.search(r'inet \d+\.\d+\.\d+\.\d+/(\d+)', result.stdout)
            if match:
                return match.group(1)
        return "24"

    def get_network_info(self):
        gateway = "Unknown"
        result = self.run(['ip', 'route', 'show', 'default'])
        if result and result.stdout:
            for line in result.stdout.splitlines():
                if 'default' in line:
                    parts = line.split()
                    if 'via' in parts:
                        gateway = parts[parts.index('via') + 1]

        current_ip = self.get_current_ip()
        subnet = "192.168.1"
        if current_ip and current_ip != "No IP":
            parts = current_ip.split('.')
            if len(parts) == 4:
                subnet = f"{parts[0]}.{parts[1]}.{parts[2]}"

        return gateway, subnet

    def is_valid_ip(self, ip):
        pattern = r'^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$'
        m = re.match(pattern, ip)
        if not m:
            return False
        return all(0 <= int(octet) <= 255 for octet in m.groups())

    # ---------- core actions ----------

    def change_ip_with_gateway(self, interface, new_ip, gateway, mask="24"):
        if not self.is_valid_ip(new_ip):
            print(f"❌ Invalid IP format: {new_ip}")
            return False

        print(f"\n🔄 Changing IP on {interface}...")

        # Remove existing IPs on the interface
        self.run(['ip', 'addr', 'flush', 'dev', interface])

        # Add new IP
        result = self.run(['ip', 'addr', 'add', f'{new_ip}/{mask}', 'dev', interface])
        if result is None or result.returncode != 0:
            err = result.stderr if result else "unknown error"
            print(f"❌ Failed to add IP: {err}")
            return False

        # Bring interface up
        self.run(['ip', 'link', 'set', interface, 'up'])

        # Add gateway route if we have one
        if gateway and gateway != "Unknown" and self.is_valid_ip(gateway):
            self.run(['ip', 'route', 'replace', 'default', 'via', gateway, 'dev', interface])

        print(f"✅ IP changed to {new_ip}")
        print(f"🌐 Gateway: {gateway}")
        return True

    def set_dhcp(self, interface):
        print(f"\n🔄 Setting DHCP on {interface}...")

        # Release any existing lease first (before flushing, so the
        # release request can actually go out with the old IP)
        self.run(['dhclient', '-r', interface])

        # Now remove the static IP
        self.run(['ip', 'addr', 'flush', 'dev', interface])

        result = self.run(['dhclient', interface])
        if result and result.returncode == 0:
            print("✅ DHCP enabled!")
            time.sleep(2)
            print(f"🌐 New IP: {self.get_current_ip(interface)}")
            return True

        print("❌ DHCP failed (is dhclient installed? try: sudo apt install isc-dhcp-client)")
        return False

    def show_status(self):
        print("\n" + "=" * 60)
        print("📊 NETWORK STATUS")
        print("=" * 60)

        print(f"Interface: {self.interface}")
        print(f"Current IP: {self.get_current_ip()}")

        gateway, _ = self.get_network_info()
        print(f"Gateway: {gateway}")

        result = self.run(['ip', 'link', 'show', self.interface])
        if result and result.stdout:
            mac = re.search(r'link/ether ([\da-f:]+)', result.stdout)
            if mac:
                print(f"MAC: {mac.group(1)}")

        print("\n📡 Testing connection...")
        try:
            result = subprocess.run(['ping', '-c', '1', '-W', '2', '8.8.8.8'],
                                     capture_output=True, timeout=5)
            print("✅ Internet: Connected" if result.returncode == 0 else "⚠️ Internet: Not responding")
        except subprocess.TimeoutExpired:
            print("⚠️ Internet: Timeout")

        print("=" * 60)

    def change_ip_auto(self):
        gateway, subnet = self.get_network_info()
        mask = self.get_current_prefix()
        last_octet = random.randint(2, 254)
        new_ip = f"{subnet}.{last_octet}"

        print(f"\n🎲 Generated IP: {new_ip}")
        return self.change_ip_with_gateway(self.interface, new_ip, gateway, mask)

    def auto_change_loop(self, interval=10):
        print(f"\n🔄 Auto changing IP every {interval} seconds")
        print("Press Ctrl+C to stop\n")

        count = 1
        try:
            while True:
                print(f"\n[{count}] Changing IP...")
                self.change_ip_auto()
                count += 1
                for i in range(interval, 0, -1):
                    print(f"\r⏳ Next change in {i}s", end='', flush=True)
                    time.sleep(1)
                print()
        except KeyboardInterrupt:
            print("\n\n⏹ Stopped")

    # ---------- menu ----------

    def main_menu(self):
        while True:
            os.system('clear')
            current_ip = self.get_current_ip()

            # Custom ASCII Header
            print("""
██████╗  ██████╗ ██████╗     ██████╗ ███████╗     ██████╗ ██╗   ██╗██████╗ ███████╗██████╗ 
██╔════╝ ██╔═══██╗██╔══██╗    ██╔══██╗██╔════╝    ██╔════╝ ╚██╗ ██╔╝██╔══██╗██╔════╝██╔══██╗
██║  ███╗██║   ██║██║  ██║    ██║  ██║█████╗      ██║       ╚████╔╝ ██████╔╝█████╗  ██████╔╝
██║   ██║██║   ██║██║  ██║    ██║  ██║██╔══╝      ██║         ╚██╔╝  ██╔══██╗██╔══╝  ██╔══██╗
╚██████╔╝╚██████╔╝██████╔╝    ██████╔╝████        ╚██████╔╝   ██║   ██████╔╝███████╗██║  ██║
 ╚═════╝  ╚═════╝ ╚═════╝     ╚═════╝ ╚══════╝     ╚═════╝    ╚═╝   ╚═════╝ ╚══════╝╚═╝  ╚═╝
                                                                                            
╔══════════════════════════════════════════════════════╗
║           🔄     SPOOF IP CHANGER                   ║
║  Author: God_OF_Cyber Team                           ║
║  License: Educational Use Only                       ║
║  Website: https://github.com/masssubash240/.git      ║
╚══════════════════════════════════════════════════════╝
            """)

            print(f"📡 Interface: {self.interface}")
            print(f"🌐 Current IP: {current_ip}")
            print("\n" + "=" * 50)
            print("📌 MENU")
            print("=" * 50)
            print("1. 📊 Show Status")
            print("2. 🔄 Change IP (Auto Random)")
            print("3. 🔄 Change IP (Manual)")
            print("4. 🔄 Auto Change (Continuous)")
            print("5. 🌐 Set DHCP")
            print("6. 🎲 Generate Random IP (preview only)")
            print("7. 🔄 Refresh Status")
            print("8. 🚪 Exit")
            print("=" * 50)

            choice = input("\nEnter choice (1-8): ").strip()

            if choice == '1':
                self.show_status()
                input("\nPress Enter...")

            elif choice == '2':
                self.change_ip_auto()
                time.sleep(1)
                input("\nPress Enter...")

            elif choice == '3':
                gateway, subnet = self.get_network_info()
                mask = self.get_current_prefix()
                print(f"\nCurrent subnet: {subnet}.0/{mask}")
                ip = input("Enter new IP (e.g., 192.168.1.100): ").strip()
                if ip:
                    self.change_ip_with_gateway(self.interface, ip, gateway, mask)
                input("\nPress Enter...")

            elif choice == '4':
                try:
                    interval = int(input("Interval in seconds (default 10): ").strip() or "10")
                    self.auto_change_loop(interval)
                except ValueError:
                    print("❌ Invalid input!")
                    time.sleep(1)

            elif choice == '5':
                self.set_dhcp(self.interface)
                time.sleep(1)
                input("\nPress Enter...")

            elif choice == '6':
                _, subnet = self.get_network_info()
                new_ip = f"{subnet}.{random.randint(2, 254)}"
                print(f"\n🎲 Random IP: {new_ip}")
                if input("Apply this IP? (y/n): ").strip().lower() == 'y':
                    gateway, _ = self.get_network_info()
                    mask = self.get_current_prefix()
                    self.change_ip_with_gateway(self.interface, new_ip, gateway, mask)
                input("\nPress Enter...")

            elif choice == '7':
                continue

            elif choice == '8':
                print("\n👋 Goodbye!")
                sys.exit(0)

            else:
                print("❌ Invalid choice!")
                time.sleep(1)


def main():
    try:
        LinuxIPChanger()
    except KeyboardInterrupt:
        print("\n\n👋 Goodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
