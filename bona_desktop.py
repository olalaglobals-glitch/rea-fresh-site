"""Tkinter desktop client for a local Ollama coding assistant."""

from __future__ import annotations

import queue
import threading
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from bona_backend import (
    DEFAULT_MODEL,
    build_messages,
    chat_with_local_model,
    collect_project_context,
    list_local_models,
    pull_local_model,
    validate_model_name,
)


class BonaDesktop:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Bona Local")
        self.root.geometry("940x700")
        self.root.minsize(720, 560)
        self.root.configure(bg="#12151b")
        self.project_root: str | None = None
        self.history: list[dict[str, str]] = []
        self.events: queue.Queue[tuple[str, object]] = queue.Queue()
        self.busy = False

        self.model = tk.StringVar(value=DEFAULT_MODEL)
        self.project_label = tk.StringVar(value="No project selected")
        self.status = tk.StringVar(value="Checking local Ollama...")
        self._build_ui()
        self.root.after(150, self._drain_events)
        threading.Thread(target=self._check_ollama, daemon=True).start()

    def _build_ui(self) -> None:
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TCombobox", fieldbackground="#20242d", background="#20242d", foreground="#f2f0e9")

        header = tk.Frame(self.root, bg="#12151b", padx=20, pady=14)
        header.pack(fill="x")
        tk.Label(header, text="Bona Local", fg="#f2f0e9", bg="#12151b",
                 font=("Segoe UI", 18, "bold")).pack(side="left")
        tk.Label(header, text="Private local AI · no subscription", fg="#9aa0ad",
                 bg="#12151b", font=("Segoe UI", 10)).pack(side="left", padx=16, pady=(5, 0))

        controls = tk.Frame(self.root, bg="#181b22", padx=14, pady=10)
        controls.pack(fill="x", padx=20)
        tk.Button(controls, text="Choose project", command=self._choose_project,
                  bg="#282333", fg="#e8ddff", activebackground="#39304f",
                  relief="flat", padx=12, pady=7).pack(side="left")
        tk.Label(controls, textvariable=self.project_label, fg="#c1c5ce",
                 bg="#181b22", anchor="w").pack(side="left", padx=10, fill="x", expand=True)
        self.model_input = ttk.Entry(controls, textvariable=self.model, width=24)
        self.model_input.pack(side="left", padx=5)
        self.setup_button = tk.Button(controls, text="Download model", command=self._setup_model,
                                      bg="#292d37", fg="#f2f0e9", activebackground="#3a404d",
                                      relief="flat", padx=10, pady=7)
        self.setup_button.pack(side="left", padx=(5, 0))

        self.transcript = tk.Text(
            self.root, wrap="word", state="disabled", bg="#181b22", fg="#e0e2e8",
            insertbackground="#f2f0e9", relief="flat", padx=18, pady=16,
            font=("Segoe UI", 11), spacing1=4, spacing3=8,
        )
        self.transcript.pack(fill="both", expand=True, padx=20, pady=(14, 8))
        self.transcript.tag_configure("user", foreground="#c3adff", font=("Segoe UI", 10, "bold"))
        self.transcript.tag_configure("bona", foreground="#8fd3b0", font=("Segoe UI", 10, "bold"))
        self.transcript.tag_configure("error", foreground="#ff9e9e")
        self._append("Bona", "This assistant runs against Ollama on this laptop. Choose a project folder to include a small, filtered set of files as context. Suggestions are not applied automatically.")

        prompt_frame = tk.Frame(self.root, bg="#12151b", padx=20, pady=8)
        prompt_frame.pack(fill="x")
        self.prompt = tk.Text(prompt_frame, height=4, wrap="word", bg="#1c2029",
                              fg="#f2f0e9", insertbackground="#f2f0e9",
                              relief="flat", padx=12, pady=10, font=("Segoe UI", 11))
        self.prompt.pack(side="left", fill="x", expand=True)
        self.prompt.bind("<Control-Return>", self._send_shortcut)
        self.send_button = tk.Button(prompt_frame, text="Send", command=self._send,
                                     bg="#9b7bf3", fg="#17131f", activebackground="#c3adff",
                                     relief="flat", padx=20, pady=12, font=("Segoe UI", 10, "bold"))
        self.send_button.pack(side="left", padx=(10, 0), anchor="s")

        footer = tk.Frame(self.root, bg="#12151b", padx=22, pady=8)
        footer.pack(fill="x")
        tk.Label(footer, textvariable=self.status, fg="#9299a6", bg="#12151b",
                 anchor="w").pack(fill="x")

    def _append(self, speaker: str, text: str, tag: str | None = None) -> None:
        self.transcript.configure(state="normal")
        label = "You" if speaker == "You" else speaker
        self.transcript.insert("end", f"{label}\n", tag or ("user" if speaker == "You" else "bona"))
        self.transcript.insert("end", f"{text}\n\n")
        self.transcript.configure(state="disabled")
        self.transcript.see("end")

    def _choose_project(self) -> None:
        selected = filedialog.askdirectory(title="Choose a project folder")
        if not selected:
            return
        self.project_root = selected
        self.project_label.set(selected)
        self.status.set("Project selected. Source files are read only when you send a request.")

    def _send_shortcut(self, _event: tk.Event) -> str:
        self._send()
        return "break"

    def _send(self) -> None:
        if self.busy:
            return
        prompt = self.prompt.get("1.0", "end").strip()
        if not prompt:
            return
        try:
            selected_model = validate_model_name(self.model.get())
        except ValueError as error:
            messagebox.showerror("Invalid model name", str(error))
            return

        self.prompt.delete("1.0", "end")
        self._append("You", prompt)
        self.busy = True
        self.send_button.configure(state="disabled")
        self.status.set(f"Waiting for local model {selected_model}...")
        threading.Thread(target=self._run_chat, args=(selected_model, prompt), daemon=True).start()

    def _run_chat(self, model: str, prompt: str) -> None:
        try:
            context = collect_project_context(self.project_root) if self.project_root else ""
            messages = build_messages(self.history, prompt, context)
            answer = chat_with_local_model(model, messages)
            self.history.extend(({"role": "user", "content": prompt},
                                 {"role": "assistant", "content": answer}))
            self.history = self.history[-12:]
            self.events.put(("answer", answer))
        except (RuntimeError, ValueError, OSError) as error:
            self.events.put(("error", str(error)))

    def _check_ollama(self) -> None:
        try:
            names = list_local_models()
            self.events.put(("models", names))
        except RuntimeError as error:
            self.events.put(("status", str(error)))

    def _setup_model(self) -> None:
        if self.busy:
            return
        try:
            selected_model = validate_model_name(self.model.get())
        except ValueError as error:
            messagebox.showerror("Invalid model name", str(error))
            return
        accepted = messagebox.askyesno(
            "Download local model",
            f"Download {selected_model} using Ollama? This requires an internet connection and several GB of disk space. There is no API subscription or usage fee.",
        )
        if not accepted:
            return
        self.busy = True
        self.setup_button.configure(state="disabled")
        self.status.set(f"Downloading {selected_model}...")
        threading.Thread(target=self._pull_model, args=(selected_model,), daemon=True).start()

    def _pull_model(self, model: str) -> None:
        try:
            pull_local_model(model, lambda line: self.events.put(("pull", line)))
            self.events.put(("status", f"{model} is ready."))
        except (RuntimeError, ValueError, OSError) as error:
            self.events.put(("error", str(error)))
        finally:
            self.events.put(("setup_done", None))

    def _drain_events(self) -> None:
        try:
            while True:
                kind, value = self.events.get_nowait()
                if kind == "answer":
                    self._append("Bona", str(value))
                    self.status.set("Ready. Your project files have not been changed.")
                    self.busy = False
                    self.send_button.configure(state="normal")
                elif kind == "error":
                    self._append("Bona", str(value), "error")
                    self.status.set("Request failed.")
                    self.busy = False
                    self.send_button.configure(state="normal")
                    self.setup_button.configure(state="normal")
                elif kind == "status":
                    self.status.set(str(value))
                elif kind == "models":
                    names = value if isinstance(value, list) else []
                    selected = self.model.get()
                    if any(name.split(":")[0] == selected.split(":")[0] for name in names):
                        self.status.set(f"Local Ollama is ready. Models: {', '.join(names[:4])}")
                    else:
                        self.status.set("Ollama is ready. Download the selected model to start chatting.")
                elif kind == "pull":
                    line = str(value).strip()
                    if line:
                        self.status.set(line[:180])
                elif kind == "setup_done":
                    self.busy = False
                    self.setup_button.configure(state="normal")
        except queue.Empty:
            pass
        self.root.after(150, self._drain_events)


def main() -> None:
    root = tk.Tk()
    BonaDesktop(root)
    root.mainloop()


if __name__ == "__main__":
    main()
