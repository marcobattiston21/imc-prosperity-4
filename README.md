# Prosperity 4 — Stochastic Bulls
 
We use **uv** to manage Python and all dependencies.
 
---
 
## 1. Install uv
 
**Windows** — open PowerShell and run:
 
```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```
 
**macOS** — open Terminal and run:
 
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```
 
Close and reopen your terminal after it finishes. Verify it worked:
 
```bash
uv --version
```
 
You should see something like `uv 0.x.x`. If the command isn't found, restart your terminal and rerun it.
 
---
 
## 2. Clone the repo
 
```bash
git clone https://github.com/marcobattiston21/imc-prosperity-4.git
cd imc-prosperity-4
```
 
---
 
## 3. Create the environment and install dependencies
 
Because we already have a `pyproject.toml` and `uv.lock`, this is a single command. uv will automatically download the right Python version and install every dependency at the exact pinned versions:
 
```bash
uv sync
```
 
That's it. uv creates a `.venv` folder in the project root — you don't need to activate it for most things (uv handles it transparently), but if you need to activate it manually:
 
**Windows:**
```powershell
.venv\Scripts\activate
```
 
**macOS:**
```bash
source .venv/bin/activate
```
 
> **Never run `pip install` directly.** If you need a new package, add it with `uv add <package>` so the lockfile stays in sync for everyone.
 
---
 
## Troubleshooting
 
**Someone added a new dependency and your imports are breaking**
After pulling the latest changes, run `uv sync` again to bring your environment up to date with the lockfile.
 
---
 
## Project structure (quick reference)
 
```
.
├── pyproject.toml        # project metadata and dependencies
├── uv.lock               # pinned dependency versions — do not edit manually
├── prosperity4/          # main package (trader logic + utilities)
│   └── round0/
│       └── data/         # CSV price and trade data per round
│       └── notebooks/    # analysis notebooks (.ipynb)
└── README.md
```