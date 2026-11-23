# Bona Local

Bona Local is an independent desktop coding assistant. Its model requests go only to Ollama on `127.0.0.1`; there is no hosted account, subscription, or payment. It does not write to project files. Review and apply proposed changes yourself.

## Run from source

1. Install Ollama for Windows from [ollama.com/download](https://ollama.com/download).
2. Open Bona Local and select **Download model**. It will ask before downloading the default `qwen2.5-coder:3b` model. Model downloads require internet and several GB of storage; inference runs locally afterward.
3. Select a project folder and ask a coding question.

## Run the integrated website

Start the single Flask process that serves both the frontend and backend:

```powershell
python bona_server.py
```

Open `http://127.0.0.1:4173`. The browser chat calls `/api/chat`, `/api/models`, and `/api/health`; the same process also serves `/download/BonaLocal.exe`. It is bound to localhost by default.

The app reads a bounded set of text files from the selected folder when you send a request. It skips common dependency/build folders, environment files, private keys, and binary files.

## Build a Windows executable

From this directory, install the build dependency and create the executable:

```powershell
python -m pip install -r requirements-build.txt
python -m PyInstaller --onefile --windowed --name BonaLocal bona_desktop.py
```

The resulting `dist\BonaLocal.exe` still requires Ollama and a local model. The installer does not bundle model weights.

## Current limitations

- Requires Windows, Python 3.10+ when run from source, and Ollama.
- No automatic edits, shell commands, or cloud API calls.
- Local model quality and speed depend on laptop memory and hardware.
