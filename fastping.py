import customtkinter as ctk
import subprocess
import threading
import re
import sys
import os
import webbrowser
from PIL import Image
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
                                   font=("Helvetica", 16), anchor="w")
        self.ip_label.grid(row=row, column=0, padx=(5,2), pady=1, sticky="ew")

        self.latency_var = ctk.StringVar(value="...")
        self.latency_label = ctk.CTkLabel(parent, textvariable=self.latency_var,
                                        text_color="blue", font=("Helvetica", 18),
                                        width=50, anchor="w")
        self.latency_label.grid(row=row, column=1, padx=4, pady=1, sticky="w")

        self.packet_loss_var = ctk.StringVar(value="loss:0%")
        self.packet_loss_label = ctk.CTkLabel(parent, textvariable=self.packet_loss_var,
                                            text_color="red", font=("Helvetica", 14),
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
                self.latency_label._root().after(0, self.latency_var.set, f"{latency}")
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

        # Perfect circle buttons using PyQt5-inspired approach
        btn_size = 34
        btn_style = {
            "width": btn_size,
            "height": btn_size,
            "corner_radius": btn_size // 2,
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
            command=self.show_contact_options  # Updated command
        )
        self.contact_button.grid(row=0, column=0, padx=(0,5))

        # Information button with new color scheme (purple for visibility)
        self.exclaim_button = ctk.CTkButton(
            button_frame,
            text="!",
            fg_color="#9C27B0",  # Purple color for information
            hover_color="#7B1FA2",  # Darker purple
            **btn_style,
            command=self.show_info  # Add this method for information display
        )
        self.exclaim_button.grid(row=0, column=1, padx=(0,5))

        # Theme toggle button - starts as sun since default is dark
        self.moon_button = ctk.CTkButton(
            button_frame,
            text="☀",  # Starts as sun since dark mode is default
            fg_color="#757575",
            hover_color="#424242",
            **btn_style,
            command=self.toggle_theme
        )
        self.moon_button.grid(row=0, column=2)

        # Right side links with Twitch moved left of GitHub
        link_frame = ctk.CTkFrame(top_frame, fg_color="transparent")
        link_frame.pack(side="right", anchor="e")
        
        # Twitch link
        twitch_btn = ctk.CTkLabel(
            link_frame,
            text="Twitch",
            text_color="#2196F3",
            cursor="hand2",
            font=("Helvetica", 12, "bold")
        )
        twitch_btn.pack(side="left", padx=(0, 10))
        twitch_btn.bind("<Button-1>", lambda e: webbrowser.open("https://twitch.tv/your_channel"))

        # GitHub link
        github_btn = ctk.CTkLabel(
            link_frame,
            text="GitHub",
            text_color="#2196F3",
            cursor="hand2",
            font=("Helvetica", 12, "bold")
        )
        github_btn.pack(side="left")
        github_btn.bind("<Button-1>", lambda e: webbrowser.open("https://github.com/AmirHossein143/FastPing"))

        # Main content
        self.ip_frame = ctk.CTkScrollableFrame(root, fg_color="white", width=320, height=100)
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
    def show_contact_options(self):
        # Create contact dialog
        contact_dialog = ctk.CTkToplevel(self.root)
        contact_dialog.title("📱 Contact Options")
        contact_dialog.geometry("300x250")  # Increased height for additional button
        contact_dialog.resizable(False, False)
        
        # Force dialog to stay on top
        contact_dialog.grab_set()
        contact_dialog.transient(self.root)
        
        # Configure grid layout
        contact_dialog.grid_columnconfigure(0, weight=1)
        contact_dialog.grid_rowconfigure(0, weight=1)
        
        # Button frame with centered alignment
        button_frame = ctk.CTkFrame(contact_dialog, fg_color="transparent")
        button_frame.grid(row=0, column=0, padx=40, pady=20, sticky="nsew")  # Increased horizontal padding
        
        # Telegram Button
        telegram_btn = ctk.CTkButton(
            button_frame,
            text=" 📲 Telegram",
            font=("Helvetica", 13, "bold"),  # Slightly smaller font
            fg_color="#0088CC",
            hover_color="#006699",
            width=200,  # Fixed width
            command=lambda: webbrowser.open("https://t.me/amir_pdr")
        )
        telegram_btn.pack(pady=5)
        
        # Twitch Button
        twitch_btn = ctk.CTkButton(
            button_frame,
            text=" 🎮 Twitch",
            font=("Helvetica", 13, "bold"),
            fg_color="#9146FF",
            hover_color="#6E33CC",
            width=200,
            command=lambda: webbrowser.open("https://twitch.tv/your_channel")
        )
        twitch_btn.pack(pady=5)
        
        # Steam Button
        steam_btn = ctk.CTkButton(
            button_frame,
            text=" ⚙️ Steam",
            font=("Helvetica", 13, "bold"),
            fg_color="#1B2838",
            hover_color="#15202B",
            width=200,
            command=lambda: webbrowser.open("https://steamcommunity.com/id/your_profile")
        )
        steam_btn.pack(pady=5)
        
        # Website Button
        website_btn = ctk.CTkButton(
            button_frame,
            text=" 🌐 Website",
            font=("Helvetica", 13, "bold"),
            fg_color="#4CAF50",  # Green color for website
            hover_color="#388E3C",
            width=200,
            command=lambda: webbrowser.open("https://your-website.com")
        )
        website_btn.pack(pady=5)
########################################################################
    def create_ping_row(self, ip, row):
        current_mode = ctk.get_appearance_mode().lower()
        if current_mode == "dark":
            ip_text_color = "white"
            latency_text_color = "lightblue"
            packet_loss_text_color = "orange"
            bg_color = "#2b2b2b"
        else:
            ip_text_color = "black"
            latency_text_color = "blue"
            packet_loss_text_color = "red"
            bg_color = "white"
        # Ensure the scrollable frame background is updated
        self.ip_frame.configure(fg_color=bg_color)
        ping_row = PingRow(self.ip_frame, ip, row, self.remove_ip)
        # Update each label with the dynamic colors
        ping_row.ip_label.configure(text_color=ip_text_color)
        ping_row.latency_label.configure(text_color=latency_text_color)
        ping_row.packet_loss_label.configure(text_color=packet_loss_text_color)
        self.ping_rows[ip] = ping_row

#####################################################################


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
############################################################################
    def toggle_theme(self):
        current_mode = ctk.get_appearance_mode().lower()
        new_mode = "dark" if current_mode == "light" else "light"
        ctk.set_appearance_mode(new_mode)
        self.moon_button.configure(text="🌙" if new_mode == "dark" else "☀")
        bg_color = "#2b2b2b" if new_mode == "dark" else "white"
        text_color = "white" if new_mode == "dark" else "black"
        
        # Update link colors
        link_color = "#9146FF" if new_mode == "dark" else "#6A1B9A"
        github_color = "#2196F3" if new_mode == "dark" else "#1565C0"
        
        # Update all components
        self.ip_frame.configure(fg_color=bg_color)
        for pr in self.ping_rows.values():
            pr.ip_label.configure(text_color=text_color)
            pr.latency_label.configure(text_color="lightblue" if new_mode == "dark" else "blue")
            pr.packet_loss_label.configure(text_color="orange" if new_mode == "dark" else "red")

    def show_info(self):
        # Create information dialog with emojis
        info_dialog = ctk.CTkToplevel(self.root)
        info_dialog.title("App Information")
        info_dialog.geometry("360x335")
        
        info_text = """
        🚀 FastPing - Network Monitoring Tool    
        
        🌟 Features:  
        🌐 Real-time latency monitoring    
        📊 Packet loss calculation    
        🔧 Custom IP/hostname tracking    
        🌗 Dark/Light theme support    
        📁 Automatic save/load of IPs    
         
        📖 Usage:    
         Click ➕ to add new IPs/hostnames    
         Monitor real-time stats 👀    
         Remove entries with the ❌ button    
         Toggle themes with 🌙/☀ button    
        
        ⚠️ Note:    
        Timeouts show as 'Timeout' ⏳    
        Statistics update every 40 pings 📈    
        """
        

        
        info_label = ctk.CTkLabel(info_dialog, 
                                text=info_text, 
                                justify="left",
                                font=("Helvetica", 14))
        info_label.pack(padx=20, pady=20, fill="both", expand=True)
###############################################################################
def main():
    root = ctk.CTk()
    FastPingApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()