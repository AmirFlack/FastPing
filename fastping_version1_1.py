import customtkinter as ctk
import subprocess
import threading
import re
import sys
import os
import webbrowser

#######################################
# Set appearance and theme for customtkinter
ctk.set_appearance_mode("light")  # Light mode uses a white background
ctk.set_default_color_theme("blue")

# Determine application path for IPS_FILE
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

IPS_FILE = os.path.join(application_path, "ips.txt")

# Default IPs if file doesn't exist
DEFAULT_IPS = [
    "5.200.200.200",
    "8.8.8.8",
    "4.2.2.4",
    "ac-client-ws.faceit.com",
    "104.19.156.82"
]
# OS-specific command and regex patterns
if sys.platform.startswith("win"):
    def get_ping_cmd(ip):
        # Use full path to system ping.exe so that any local ping.exe is not used.
        return [r"C:\Windows\System32\ping.exe", "-t", ip]
    TIME_REGEX = re.compile(r"time=(\d+)ms")
    TIMEOUT_REGEX = re.compile(r"Request timed out", re.IGNORECASE)
else:
    def get_ping_cmd(ip):
        return ["ping", ip]
    TIME_REGEX = re.compile(r"time=(\d+(?:\.\d+)?) ms")
    TIMEOUT_REGEX = re.compile(r"Request timeout", re.IGNORECASE)

def load_ips():
    """Load IPs from file, or create file with defaults if missing."""
    if os.path.exists(IPS_FILE):
        with open(IPS_FILE, "r", encoding="utf-8") as f:
            ips = [line.strip() for line in f if line.strip()]
    else:
        ips = DEFAULT_IPS.copy()
        update_ips_file(ips)
    return ips

def update_ips_file(ips):
    """Write the current list of IPs to the file."""
    with open(IPS_FILE, "w", encoding="utf-8") as f:
        for ip in ips:
            f.write(ip + "\n")

class PingRow:
    def __init__(self, parent, ip, row, remove_callback):
        """
        parent: container (CTkScrollableFrame) for the row.
        ip: IP address/hostname.
        row: grid row index.
        remove_callback: function to call when row is deleted.
        """
        self.parent = parent
        self.ip = ip
        self.row = row
        self.remove_callback = remove_callback
        self.stop_event = threading.Event()

        # Create UI elements with modern styling
        self.ip_label = ctk.CTkLabel(
            parent, text=ip, text_color="black", font=("Helvetica", 12, "bold"), fg_color="transparent"
        )
        self.ip_label.grid(row=row, column=0, padx=10, pady=8, sticky="w")

        self.latency_var = ctk.StringVar(value="...")
        self.latency_label = ctk.CTkLabel(
            parent, textvariable=self.latency_var, text_color="blue", font=("Helvetica", 12), fg_color="transparent"
        )
        self.latency_label.grid(row=row, column=1, padx=10, pady=8, sticky="w")

        self.delete_button = ctk.CTkButton(
            parent,
            text="Delete",
            command=self.delete,
            font=("Helvetica", 10, "bold"),
            fg_color="tomato",
            hover_color="#ff7f7f",
            corner_radius=8,
            width=80
        )
        self.delete_button.grid(row=row, column=2, padx=10, pady=8)

        # Start the ping thread for this IP
        self.thread = threading.Thread(target=self.ping_loop, daemon=True)
        self.thread.start()

    def ping_loop(self):
        """Continuously ping the IP and update latency until stopped."""
        cmd = get_ping_cmd(self.ip)
        # For Windows: Suppress CMD window for subprocess
        if sys.platform.startswith("win"):
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW  # Hides CMD window
            )
        else:
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        while not self.stop_event.is_set():
            line = self.process.stdout.readline()
            if not line:
                break

            match = TIME_REGEX.search(line)
            if match:
                latency = match.group(1)
                # Schedule UI update on the main thread
                self.latency_label._root().after(0, self.latency_var.set, latency)
            elif TIMEOUT_REGEX.search(line):
                self.latency_label._root().after(0, self.latency_var.set, "Timeout")
        self.process.terminate()

    def delete(self):
        """Stop ping thread, remove UI elements, and notify parent."""
        self.stop_event.set()
        try:
            self.process.terminate()
        except Exception:
            pass

        self.ip_label.destroy()
        self.latency_label.destroy()
        self.delete_button.destroy()
        self.remove_callback(self.ip)

class FastPingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FastPing-v1.0")
        self.root.geometry("500x500")
        self.root.resizable(False, False)  # Fixed size window

        # Top frame for contact label (top-left) and GitHub button (top-right)
        top_frame = ctk.CTkFrame(root, fg_color="transparent")
        top_frame.pack(side="top", fill="x", padx=9, pady=6)

        # Contact label (top-left)
        contact_label = ctk.CTkLabel(
            top_frame, text="Contact me", text_color="dodgerblue", font=("Helvetica", 14, "bold"),
            fg_color="transparent", cursor="hand2"
        )
        contact_label.pack(side="left")
        contact_label.bind("<Button-1>", lambda e: webbrowser.open("https://t.me/amir_pdr"))

        # GitHub button (top-right)
        github_label = ctk.CTkLabel(
            top_frame, text="GitHub", text_color="dodgerblue", font=("Helvetica", 14, "bold"),
            fg_color="transparent", cursor="hand2"
        )
        github_label.pack(side="right")
        github_label.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/AmirHossein143"))

        # Main title
        title_label = ctk.CTkLabel(root, text="FastPing", text_color="black", font=("Helvetica", 18, "bold"))
        title_label.pack(pady=(0, 10))

        # Scrollable frame for IP rows
        self.ip_frame = ctk.CTkScrollableFrame(root, fg_color="white", height=300)
        self.ip_frame.pack(pady=10, padx=10, fill="both", expand=True)

        # Load IPs from file
        self.ips = load_ips()
        self.ping_rows = {}   # Map IP -> PingRow
        self.row_index = 0
        for ip in self.ips:
            self.create_ping_row(ip)

        # Frame for adding new IPs
        add_frame = ctk.CTkFrame(root, fg_color="transparent")
        add_frame.pack(pady=15, padx=10, fill="x")

        self.ip_entry = ctk.CTkEntry(add_frame, placeholder_text="Enter IP or hostname", width=200, font=("Helvetica", 12))
        self.ip_entry.pack(side="left", padx=10)
        self.add_button = ctk.CTkButton(
            add_frame,
            text="Add IP",
            command=self.add_ip,
            font=("Helvetica", 12, "bold"),
            fg_color="dodgerblue",
            hover_color="#4da6ff",
            corner_radius=8,
            width=100
        )
        self.add_button.pack(side="left", padx=5)

        # Bottom frame for credit label (bottom-right)
        bottom_frame = ctk.CTkFrame(root, fg_color="transparent")
        bottom_frame.pack(side="bottom", fill="x", padx=0, pady=0)

        credit_label = ctk.CTkLabel(
            bottom_frame, text="credits: AmirHossein_pdr", text_color="black", font=("Helvetica", 14, "bold"), fg_color="transparent"
        )
        credit_label.pack(side="right")

    def create_ping_row(self, ip):
        """Create a PingRow for the given IP and add it to the scrollable frame."""
        row = self.row_index
        pr = PingRow(self.ip_frame, ip, row, self.remove_ip)
        self.ping_rows[ip] = pr
        self.row_index += 1

    def add_ip(self):
        """Add a new IP from the entry box."""
        new_ip = self.ip_entry.get().strip()
        if new_ip and new_ip not in self.ips:
            self.ips.append(new_ip)
            self.create_ping_row(new_ip)
            update_ips_file(self.ips)
        self.ip_entry.delete(0, "end")

    def remove_ip(self, ip):
        """Remove the IP from the list and update file when deleted."""
        if ip in self.ips:
            self.ips.remove(ip)
        if ip in self.ping_rows:
            del self.ping_rows[ip]
        update_ips_file(self.ips)

def main():
    root = ctk.CTk()
    app = FastPingApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
