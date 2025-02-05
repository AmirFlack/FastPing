import customtkinter as ctk
import subprocess
import threading
import re
import sys
import os
import webbrowser

# Set appearance and theme for customtkinter
ctk.set_appearance_mode("light")
ctk.set_default_color_theme("blue")

# Determine application path for IPS_FILE
if getattr(sys, 'frozen', False):
    application_path = os.path.dirname(sys.executable)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))

IPS_FILE = os.path.join(application_path, "ips.txt")
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
        self.parent = parent
        self.ip = ip
        self.row = row
        self.remove_callback = remove_callback
        self.stop_event = threading.Event()
        self.interval_total = 0
        self.interval_received = 0

        # Create UI elements with tight spacing
        self.ip_label = ctk.CTkLabel(parent, text=ip, text_color="black",
                                   font=("Helvetica", 13), anchor="w")
        self.ip_label.grid(row=row, column=0, padx=(5,2), pady=1, sticky="ew")

        self.latency_var = ctk.StringVar(value="...")
        self.latency_label = ctk.CTkLabel(parent, textvariable=self.latency_var,
                                        text_color="blue", font=("Helvetica", 12),
                                        width=50, anchor="w")
        self.latency_label.grid(row=row, column=1, padx=0, pady=1, sticky="w")

        self.packet_loss_var = ctk.StringVar(value="loss:0%")
        self.packet_loss_label = ctk.CTkLabel(parent, textvariable=self.packet_loss_var,
                                            text_color="red", font=("Helvetica", 12),
                                            width=50, anchor="w")
        self.packet_loss_label.grid(row=row, column=2, padx=0, pady=1, sticky="w")

        # Minimal delete button
        self.delete_button = ctk.CTkButton(parent, text="✕", command=self.delete,
                                         font=("Arial", 11), width=20, height=20,
                                         fg_color="transparent", hover_color="#eeeeee",
                                         corner_radius=10, border_width=0,
                                         text_color="#ff4444")
        self.delete_button.grid(row=row, column=3, padx=(2,5), pady=1)

        self.thread = threading.Thread(target=self.ping_loop, daemon=True)
        self.thread.start()

    def ping_loop(self):
        """Continuously ping the IP and update latency until stopped."""
        cmd = get_ping_cmd(self.ip)
        if sys.platform.startswith("win"):
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, text=True,
                                            creationflags=subprocess.CREATE_NO_WINDOW)
        else:
            self.process = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                                            stderr=subprocess.PIPE, text=True)
        while not self.stop_event.is_set():
            line = self.process.stdout.readline()
            if not line:
                break
            match = TIME_REGEX.search(line)
            if match:
                self.interval_total += 1
                self.interval_received += 1
                latency = match.group(1)
                self.latency_label._root().after(0, self.latency_var.set, f"{latency}ms")
            elif TIMEOUT_REGEX.search(line):
                self.interval_total += 1
                self.latency_label._root().after(0, self.latency_var.set, "Timeout")
            if self.interval_total >= 40:
                lost = self.interval_total - self.interval_received
                loss_percent = 100 * lost / self.interval_total
                self.packet_loss_label._root().after(0, self.packet_loss_var.set, f"loss:{loss_percent:.0f}%")
                self.interval_total = 0
                self.interval_received = 0
        self.process.terminate()

    def delete(self):
        self.stop_event.set()
        try: self.process.terminate()
        except: pass
        self.ip_label.destroy()
        self.latency_label.destroy()
        self.packet_loss_label.destroy()
        self.delete_button.destroy()
        self.remove_callback(self.ip)

class FastPingApp:
    def __init__(self, root):
        self.root = root
        self.root.title("FastPing-v1.1")
        self.root.geometry("380x338")
        self.root.resizable(True, False)

        # Top controls
        top_frame = ctk.CTkFrame(root, fg_color="transparent")
        top_frame.pack(side="top", fill="x", padx=8, pady=6)

        # Left button container
        button_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        button_frame.pack(side="left", anchor="w")

        # Perfect circle buttons using precise measurements
        btn_size = 34
        btn_style = {
            "width": btn_size,
            "height": btn_size,
            "corner_radius": btn_size//2,
            "border_width": 0,
            "font": ("Arial", 16),
            "text_color": "white",
            "anchor": "center"
        }
        
        # Contact button
        self.contact_button = ctk.CTkButton(
            button_frame, 
            text="📞", 
            fg_color="#2196F3",
            hover_color="#1976D2",
            **btn_style,
            command=lambda: webbrowser.open("https://t.me/amir_pdr")
        )
        self.contact_button.grid(row=0, column=0, padx=(0,5))

        # Exclamation button
        self.exclaim_button = ctk.CTkButton(
            button_frame,
            text="!",
            fg_color="#FF5252",
            hover_color="#D32F2F",
            **btn_style
        )
        self.exclaim_button.grid(row=0, column=1, padx=(0,5))

        # Theme toggle button
        self.moon_button = ctk.CTkButton(
            button_frame,
            text="🌙",
            fg_color="#757575",
            hover_color="#424242",
            **btn_style,
            command=self.toggle_theme
        )
        self.moon_button.grid(row=0, column=2)

        # Right side links
        link_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        link_frame.pack(side="right", anchor="e")
        
        # GitHub link
        github_btn = ctk.CTkLabel(
            link_frame,
            text="GitHub",
            text_color="#2196F3",
            cursor="hand2",
            font=("Helvetica", 12, "bold")
        )
        github_btn.pack(pady=(0,2))
        github_btn.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/AmirHossein143/FastPing"))

        # Twitch link
        twitch_btn = ctk.CTkLabel(
            link_frame,
            text="Twitch",
            text_color="#9146FF",
            cursor="hand2",
            font=("Helvetica", 12, "bold")
        )
        twitch_btn.pack()
        twitch_btn.bind("<Button-1>", lambda e: webbrowser.open("https://twitch.tv/your_channel"))

        # Main content
        self.ip_frame = ctk.CTkScrollableFrame(root, fg_color="white", width=320, height=100)  # Reduced by 50px
        self.ip_frame.pack(pady=5, padx=10, fill="both", expand=False)
        self.ip_frame.columnconfigure(0, weight=1, minsize=140)
        self.ip_frame.columnconfigure(1, minsize=50)
        self.ip_frame.columnconfigure(2, minsize=50)
        self.ip_frame.columnconfigure(3, minsize=30)

        self.ips = load_ips()
        self.ping_rows = {}
        for row, ip in enumerate(self.ips):
            self.create_ping_row(ip, row)

        # Add IP section
        add_frame = ctk.CTkFrame(root, fg_color="transparent")
        add_frame.pack(pady=8, padx=10)
        self.ip_entry = ctk.CTkEntry(add_frame, placeholder_text="Enter IP/hostname",
                                   width=180, font=("Helvetica", 13))
        self.ip_entry.pack(side="left", padx=5)
        ctk.CTkButton(add_frame, text="Add", width=60, font=("Helvetica", 11, "bold"),
                    command=self.add_ip, fg_color="#4CAF50", hover_color="#388E3C").pack(side="left")

        # Credits
        ctk.CTkLabel(root, text="credits: AmirHossein_pdr", text_color="gray70",
                   font=("Helvetica", 12)).place(relx=1.0, rely=1.0, anchor="se", x=-8, y=-6)

    def create_ping_row(self, ip, row):
        pr = PingRow(self.ip_frame, ip, row, self.remove_ip)
        self.ping_rows[ip] = pr

    def add_ip(self):
        new_ip = self.ip_entry.get().strip()
        if new_ip and new_ip not in self.ips:
            self.ips.append(new_ip)
            self.create_ping_row(new_ip, len(self.ips)-1)
            update_ips_file(self.ips)
        self.ip_entry.delete(0, "end")

    def remove_ip(self, ip):
        if ip in self.ips:
            self.ips.remove(ip)
        if ip in self.ping_rows:
            del self.ping_rows[ip]
        update_ips_file(self.ips)
        self.rebuild_rows()

    def rebuild_rows(self):
        for widget in self.ip_frame.winfo_children():
            widget.destroy()
        self.ping_rows = {}
        for row, ip in enumerate(self.ips):
            self.create_ping_row(ip, row)

    def toggle_theme(self):
        current_mode = ctk.get_appearance_mode().lower()
        new_mode = "dark" if current_mode == "light" else "light"
        ctk.set_appearance_mode(new_mode)
        self.moon_button.configure(text="☀" if new_mode == "dark" else "🌙")
        bg_color = "#2b2b2b" if new_mode == "dark" else "white"
        text_color = "white" if new_mode == "dark" else "black"
        self.ip_frame.configure(fg_color=bg_color)
        for pr in self.ping_rows.values():
            pr.ip_label.configure(text_color=text_color)
            pr.latency_label.configure(text_color="lightblue" if new_mode == "dark" else "blue")
            pr.packet_loss_label.configure(text_color="orange" if new_mode == "dark" else "red")

def main():
    root = ctk.CTk()
    FastPingApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()