# ui/data_entry_ui.py
from random import random
import tkinter as tk
from tkinter import ttk, messagebox
import requests
from datetime import datetime
import random

API_BASE = "http://127.0.0.1:8000"

def post_customer(data):
    try:
        r = requests.post(f"{API_BASE}/ingest/customers/", json=data, timeout=5)
        r.raise_for_status()
        return r.json(), None
    except requests.RequestException as e:
        return None, str(e)

def post_policy(data):
    try:
        r = requests.post(f"{API_BASE}/ingest/policies/", json=data, timeout=5)
        r.raise_for_status()
        return r.json(), None
    except requests.RequestException as e:
        return None, str(e)

class DarkDataEntryApp:
    def __init__(self, root):
        self.root = root
        self.root.title("AI Insurance Collection Agent – Dashboard")
        self.root.geometry("980x680")
        self.root.resizable(True, True)
        self.root.configure(bg="#0f1117")

        # Dark theme colors
        self.colors = {
            "bg": "#0f1117",
            "frame": "#161b22",
            "text": "#c9d1d9",
            "accent": "#58a6ff",
            "accent_hover": "#388bfd",
            "success": "#56d364",
            "error": "#f85149",
            "border": "#30363d",
            "table_header": "#21262d",
        }

        # Style configuration
        style = ttk.Style()
        style.theme_use("clam")

        style.configure("TLabel", background=self.colors["frame"], foreground=self.colors["text"], font=("Segoe UI", 11))
        style.configure("Header.TLabel", background=self.colors["frame"], foreground=self.colors["accent"], font=("Segoe UI", 16, "bold"))
        style.configure("TEntry", fieldbackground="#0d1117", foreground=self.colors["text"], insertcolor=self.colors["accent"])
        style.map("TEntry", fieldbackground=[("focus", "#21262d")])
        style.configure("Accent.TButton", background=self.colors["accent"], foreground="white", font=("Segoe UI", 11, "bold"), borderwidth=0)
        style.map("Accent.TButton", background=[("active", self.colors["accent_hover"])])
        style.configure("Treeview", background=self.colors["frame"], foreground=self.colors["text"], fieldbackground=self.colors["frame"])
        style.configure("Treeview.Heading", background=self.colors["table_header"], foreground=self.colors["text"])
        style.configure("TNotebook", background=self.colors["bg"], foreground=self.colors["text"])
        style.configure("TNotebook.Tab", background=self.colors["frame"], foreground=self.colors["text"], padding=[12, 6])
        style.map("TNotebook.Tab", background=[("selected", self.colors["accent"])], foreground=[("selected", "white")])

        # Header
        header = tk.Frame(root, bg=self.colors["bg"])
        header.pack(fill="x", pady=(10, 0))
        ttk.Label(header, text="AI Insurance Collection Agent – Dashboard", style="Header.TLabel").pack(side="left", padx=20)

        # Notebook
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill="both", expand=True, padx=15, pady=10)

        self.build_dashboard_tab()
        self.build_customer_tab()
        self.build_policy_tab()

    def build_dashboard_tab(self):
        f = ttk.Frame(self.notebook)
        self.notebook.add(f, text="Dashboard")

        # Quick Stats Cards
        stats_frame = tk.Frame(f, bg=self.colors["frame"])
        stats_frame.pack(fill="x", padx=10, pady=15)

        stats = [
            ("Active Targets", "12", self.colors["accent"]),
            ("Calls Today", "47", self.colors["accent"]),
            ("Promise Rate", "68%", self.colors["success"]),
            ("Escalations", "4", self.colors["error"])
        ]

        for text, value, color in stats:
            card = tk.Frame(stats_frame, bg=self.colors["frame"], bd=1, relief="solid", highlightbackground=self.colors["border"], highlightthickness=1)
            card.pack(side="left", padx=10, fill="x", expand=True)
            ttk.Label(card, text=text, font=("Segoe UI", 10)).pack(pady=5)
            ttk.Label(card, text=value, font=("Segoe UI", 18, "bold"), foreground=color).pack(pady=5)

        # Recent Activity Table
        tree_frame = tk.Frame(f, bg=self.colors["frame"])
        tree_frame.pack(fill="both", expand=True, padx=10, pady=10)

        columns = ("Timestamp", "Phone", "Policy ID", "Outcome", "Promise Date")
        tree = ttk.Treeview(tree_frame, columns=columns, show="headings", height=10)
        tree.heading("Timestamp", text="Timestamp")
        tree.heading("Phone", text="Phone")
        tree.heading("Policy ID", text="Policy ID")
        tree.heading("Outcome", text="Outcome")
        tree.heading("Promise Date", text="Promise Date")

        tree.column("Timestamp", width=140, anchor="w")
        tree.column("Phone", width=140, anchor="w")
        tree.column("Policy ID", width=100, anchor="center")
        tree.column("Outcome", width=140, anchor="w")
        tree.column("Promise Date", width=140, anchor="center")

        tree.pack(fill="both", expand=True)

        # Placeholder data – replace with real API fetch later
        for i in range(8):
            tree.insert("", "end", values=(
                datetime.now().strftime("%Y-%m-%d %H:%M"),
                f"+91{random.randrange(7000000000, 9999999999)}",
                f"P{i+100}",
                random.choice(["promise_to_pay", "voicemail", "paid", "angry_customer"]),
                random.choice(["2026-02-15", "-"])
            ))

    def build_customer_tab(self):
        f = ttk.Frame(self.notebook)
        self.notebook.add(f, text="Add Customer")

        labels = ["Name", "Phone (E.164)", "Language Pref", "Time Zone"]
        self.cust_entries = {}

        for i, label in enumerate(labels):
            ttk.Label(f, text=label + ":").grid(row=i, column=0, padx=15, pady=12, sticky="w")
            entry = ttk.Entry(f, width=50)
            entry.grid(row=i, column=1, pady=12, padx=10, sticky="ew")
            self.cust_entries[label] = entry

        self.cust_entries["Language Pref"].insert(0, "en")
        self.cust_entries["Time Zone"].insert(0, "Asia/Kolkata")

        btn = ttk.Button(f, text="Add Customer", command=self.submit_customer, style="Accent.TButton")
        btn.grid(row=len(labels), column=0, columnspan=2, pady=25, ipadx=20, ipady=8)

        self.cust_status = ttk.Label(f, text="", foreground=self.colors["success"])
        self.cust_status.grid(row=len(labels)+1, column=0, columnspan=2, pady=10)

    def build_policy_tab(self):
        f = ttk.Frame(self.notebook)
        self.notebook.add(f, text="Add Policy")

        labels = ["Customer ID", "Premium Amount", "Due Date (YYYY-MM-DD)", "Status"]
        self.pol_entries = {}

        for i, label in enumerate(labels):
            ttk.Label(f, text=label + ":").grid(row=i, column=0, padx=15, pady=12, sticky="w")
            if label == "Status":
                combo = ttk.Combobox(f, width=47, values=["active", "overdue", "paid", "canceled"])
                combo.set("overdue")
                combo.grid(row=i, column=1, pady=12, padx=10, sticky="ew")
                self.pol_entries[label] = combo
            else:
                entry = ttk.Entry(f, width=50)
                entry.grid(row=i, column=1, pady=12, padx=10, sticky="ew")
                self.pol_entries[label] = entry

        btn = ttk.Button(f, text="Add Policy", command=self.submit_policy, style="Accent.TButton")
        btn.grid(row=len(labels), column=0, columnspan=2, pady=25, ipadx=20, ipady=8)

        self.pol_status = ttk.Label(f, text="", foreground=self.colors["success"])
        self.pol_status.grid(row=len(labels)+1, column=0, columnspan=2, pady=10)

    def submit_customer(self):
        data = {
            "name": self.cust_entries["Name"].get().strip(),
            "phone": self.cust_entries["Phone (E.164)"].get().strip(),
            "language_pref": self.cust_entries["Language Pref"].get().strip() or "en",
            "time_zone": self.cust_entries["Time Zone"].get().strip() or "Asia/Kolkata"
        }

        if not data["name"] or not data["phone"]:
            self.cust_status.config(text="Name and Phone are required", foreground=self.colors["error"])
            return

        resp, err = post_customer(data)
        if resp:
            self.cust_status.config(text=f"Success! Customer ID: {resp.get('id')}", foreground=self.colors["success"])
            messagebox.showinfo("Success", f"Customer added\nID: {resp.get('id')}")
        else:
            self.cust_status.config(text=f"Error: {err}", foreground=self.colors["error"])

    def submit_policy(self):
        try:
            cust_id = int(self.pol_entries["Customer ID"].get().strip())
        except:
            self.pol_status.config(text="Invalid Customer ID", foreground=self.colors["error"])
            return

        try:
            amount = float(self.pol_entries["Premium Amount"].get().strip())
        except:
            self.pol_status.config(text="Invalid Amount", foreground=self.colors["error"])
            return

        due_date = self.pol_entries["Due Date (YYYY-MM-DD)"].get().strip()
        status = self.pol_entries["Status"].get()

        if amount <= 0 or not due_date:
            self.pol_status.config(text="Amount and Due Date required", foreground=self.colors["error"])
            return

        data = {
            "customer_id": cust_id,
            "premium_amount": amount,
            "due_date": due_date,
            "status": status
        }

        resp, err = post_policy(data)
        if resp:
            self.pol_status.config(text=f"Success! Policy ID: {resp.get('id')}", foreground=self.colors["success"])
            messagebox.showinfo("Success", f"Policy added\nID: {resp.get('id')}")
        else:
            self.pol_status.config(text=f"Error: {err}", foreground=self.colors["error"])

if __name__ == "__main__":
    root = tk.Tk()
    app = DarkDataEntryApp(root)
    root.mainloop()