import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext, Menu, ttk
import subprocess
import threading
import json
import os

CONFIG_FILE = "./config.json"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r") as f:
            return json.load(f)
    return {"project_folders": []}

def save_config(config):
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f, indent=2)

class NodeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Node Server Manager")
        self.root.geometry("720x500")
        self.root.configure(bg="#f0f0f0")
        self.config = load_config()
        self.process = None
        self.project_paths = {}  # {project_name: full_path}

        # Menu
        self.menu = Menu(self.root)
        self.root.config(menu=self.menu)
        settings_menu = Menu(self.menu, tearoff=0)
        settings_menu.add_command(label="Add A New Folder With Projects", command=self.add_project_folder)
        settings_menu.add_command(label="Clear All Folders", command=self.clear_project_folders)
        settings_menu.add_command(label="Refresh Project List", command=self.refresh_project_list)
        self.menu.add_cascade(label="Settings", menu=settings_menu)

        # UI Elements
        input_frame = tk.Frame(self.root, bg="#f0f0f0")
        input_frame.pack(pady=10)

        tk.Label(input_frame, text="Select Project:", bg="#f0f0f0", font=("Arial", 12)).pack(side=tk.LEFT, padx=5)

        self.project_var = tk.StringVar()
        self.project_combobox = ttk.Combobox(input_frame, textvariable=self.project_var, state="readonly", width=35, font=("Arial", 11))
        self.project_combobox.pack(side=tk.LEFT, padx=5)

        self.start_button = tk.Button(input_frame, text="Start Server", command=self.start_server, bg="#4caf50", fg="white", font=("Arial", 11))
        self.start_button.pack(side=tk.LEFT, padx=5)

        self.stop_button = tk.Button(input_frame, text="Stop Server", command=self.stop_server, bg="#f44336", fg="white", font=("Arial", 11))

        # Server status label
        self.status_frame = tk.Frame(self.root, bg="#f0f0f0")
        self.status_frame.pack(pady=(0, 5))

        self.status_dot = tk.Label(self.status_frame, text="🔴", font=("Arial", 12), bg="#f0f0f0")
        self.status_dot.pack(side=tk.LEFT)

        self.status_label = tk.Label(self.status_frame, text="Server Stopped", font=("Arial", 12), bg="#f0f0f0")
        self.status_label.pack(side=tk.LEFT, padx=5)

        self.set_status(running=False)  # initialize

        # Log Output
        self.log_output = scrolledtext.ScrolledText(self.root, wrap=tk.WORD, height=20, width=90, font=("Courier", 10))
        self.log_output.pack(padx=10, pady=10)
        self.log_output.config(state=tk.DISABLED)

        # Populate initial project list
        self.refresh_project_list()

    def add_project_folder(self):
        folder = filedialog.askdirectory(title="Select Folder Containing Projects")
        if folder and folder not in self.config['project_folders']:
            self.config['project_folders'].append(folder)
            save_config(self.config)
            messagebox.showinfo("Folder Added", f"Added:\n{folder}")
            self.refresh_project_list()
        elif folder:
            messagebox.showinfo("Already Exists", "This folder is already in the list.")

    def clear_project_folders(self):
        confirm = messagebox.askyesno("Confirm", "Are you sure you want to remove all saved project folders?")
        if confirm:
            self.config['project_folders'] = []
            save_config(self.config)
            self.project_combobox['values'] = []
            self.project_paths = {}
            messagebox.showinfo("Cleared", "All project folders have been cleared.")

    def refresh_project_list(self):
        self.project_paths.clear()
        for folder in self.config.get('project_folders', []):
            for name in os.listdir(folder):
                full_path = os.path.join(folder, name)
                if os.path.isdir(full_path) and os.path.isfile(os.path.join(full_path, "package.json")):
                    self.project_paths[name] = full_path
        project_names = list(self.project_paths.keys())
        self.project_combobox['values'] = project_names
        if project_names:
            self.project_combobox.current(0)

    def start_server(self):
        project_name = self.project_var.get().strip()
        if not project_name:
            messagebox.showerror("Error", "Please select a project.")
            return

        project_path = self.project_paths.get(project_name)
        if not project_path:
            messagebox.showerror("Error", f"Project '{project_name}' not found.")
            return

        self.set_log_output(f"Starting server for: {project_name}\nPath: {project_path}\n\n")

        self.start_button.config(state=tk.DISABLED)
        self.stop_button.pack(side=tk.LEFT, padx=5)
        self.set_status(running=True)

        # Start in thread
        threading.Thread(target=self.run_server, args=(project_path,), daemon=True).start()

    def run_server(self, path):
        try:
            self.process = subprocess.Popen(
                ["npm", "start"],
                cwd=path,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )

            if self.process.stdout:
                for line in self.process.stdout:
                    self.append_log(line)

            self.process.wait()

        except Exception as e:
            self.append_log(f"\nError: {e}\n")

        finally:
            self.process = None
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.pack_forget()
            self.append_log("\nServer stopped.\n")
            self.set_status(running=False)


    def stop_server(self):
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.append_log("\nStopping server...\n")
            self.stop_button.pack_forget()
            self.set_status(running=False)

    def set_log_output(self, text):
        self.log_output.config(state=tk.NORMAL)
        self.log_output.delete(1.0, tk.END)
        self.log_output.insert(tk.END, text)
        self.log_output.config(state=tk.DISABLED)

    def append_log(self, text):
        self.log_output.config(state=tk.NORMAL)
        self.log_output.insert(tk.END, text)
        self.log_output.see(tk.END)
        self.log_output.config(state=tk.DISABLED)

    def set_status(self, running: bool):
        if running:
            self.status_dot.config(text="🟢")
            self.status_label.config(text="Server Running")
        else:
            self.status_dot.config(text="🔴")
            self.status_label.config(text="Server Stopped")

if __name__ == "__main__":
    root = tk.Tk()
    app = NodeApp(root)
    root.mainloop()
