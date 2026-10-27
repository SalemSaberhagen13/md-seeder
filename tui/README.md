# md-seeder

A toolset (interactive Python **Textual TUI** + standalone **Bash script**) that clones a remote Git repository into a temporary folder, discovers its Markdown (`.md`) files, and seeds them into a local `.claude/` directory.

---

## Table of Contents

1. [Quick Start](#1-quick-start)
2. [Project Structure](#2-project-structure)
3. [`seed_claude_tui.py` — Complete Line-by-Line Breakdown](#3-seed_claude_tuipy--complete-line-by-line-breakdown)
   - [3.1 Shebang, Docstring & Future Imports (Lines 1–4)](#31-shebang-docstring--future-imports-lines-14)
   - [3.2 Standard Library Imports (Lines 6–14)](#32-standard-library-imports-lines-614)
   - [3.3 Textual Framework Imports (Lines 16–32)](#33-textual-framework-imports-lines-1632)
   - [3.4 Global Constants (Lines 34–36)](#34-global-constants-lines-3436)
   - [3.5 `discover_markdown_files()` Function (Lines 39–51)](#35-discover_markdown_files-function-lines-3951)
   - [3.6 `SeedClaudeApp` Class Definition & Styling (`CSS`) (Lines 54–110)](#36-seedclaudeapp-class-definition--styling-css-lines-54110)
   - [3.7 Keyboard Shortcuts (`BINDINGS`) (Lines 112–117)](#37-keyboard-shortcuts-bindings-lines-112117)
   - [3.8 Constructor (`__init__`) (Lines 119–132)](#38-constructor-__init__-lines-119132)
   - [3.9 UI Layout Builder (`compose`) (Lines 134–206)](#39-ui-layout-builder-compose-lines-134206)
   - [3.10 Lifecycle & Keyboard Event Handlers (`on_mount`, `on_key`) (Lines 208–227)](#310-lifecycle--keyboard-event-handlers-on_mount-on_key-lines-208227)
   - [3.11 Button Click Handlers (`@on`) (Lines 229–245)](#311-button-click-handlers-on-lines-229245)
   - [3.12 Validation Action (`action_fetch_repo`) (Lines 247–266)](#312-validation-action-action_fetch_repo-lines-247266)
   - [3.13 Async Worker (`_clone_and_scan`) (Lines 268–345)](#313-async-worker-_clone_and_scan-lines-268345)
   - [3.14 Select/Deselect All Action (`action_toggle_select_all`) (Lines 347–354)](#314-selectdeselect-all-action-action_toggle_select_all-lines-347354)
   - [3.15 Confirm & Copy Action (`action_copy_selected`) (Lines 356–399)](#315-confirm--copy-action-action_copy_selected-lines-356399)
   - [3.16 Temporary Directory Cleanup (`_cleanup_tmp_dir`, `on_unmount`) (Lines 401–407)](#316-temporary-directory-cleanup-_cleanup_tmp_dir-on_unmount-lines-401407)
   - [3.17 CLI Argument Parser (`parse_args`, `main`) (Lines 410–453)](#317-cli-argument-parser-parse_args-main-lines-410453)
4. [`run_tui.sh` — Complete Line-by-Line Breakdown](#4-run_tuish--complete-line-by-line-breakdown)
5. [`seed_claude.sh` — Complete Line-by-Line Breakdown](#5-seed_claudesh--complete-line-by-line-breakdown)
6. [`requirements.txt` & `.gitignore`](#6-requirementstxt--gitignore)

---

## 1. Quick Start

```bash
# Launch the interactive TUI (auto-creates .venv and installs Textual if needed)
./run_tui.sh

# Optionally pre-fill form fields via CLI flags:
./run_tui.sh -r git@github.com:SalemSaberhagen13/md-seeder.git -b master -k ~/.ssh/id_ed25519
```

---

## 2. Project Structure

| Path | Purpose |
| :--- | :--- |
| `md_files/` | Root folder containing the Markdown files (e.g. `md_files/CLAUDE.md`) to seed into `.claude/`. |
| `run_tui.sh` | Root Bash launcher that bootstraps `tui/.venv/`, installs `tui/requirements.txt`, and runs `tui/app.py`. |
| `seed_claude.sh` | Root non-interactive Bash CLI script that clones a repo and copies `.md` files directly (ignoring `tui/`). |
| `.gitignore` | Root Git ignore file preventing Git from tracking `.venv/`, `tui/.venv/`, and Python bytecode caches. |
| `tui/app.py` | Full-screen Python **Textual** TUI application for configuring, cloning, selecting, and copying `.md` files. |
| `tui/requirements.txt` | Python package dependency list (`textual>=0.80.0`). |
| `tui/README.md` | This comprehensive line-by-line documentation file (ignored during `.md` seeding because it resides under `tui/`). |

---

## 3. `tui/app.py` — Complete Line-by-Line Breakdown

### 3.1 Shebang & Docstring (Lines 1–2)

```python
#!/usr/bin/env python3
"""Interactive Textual TUI for seeding Claude markdown files from a Git repository."""
```

* **Line 1 (`#!/usr/bin/env python3`)**: Known as a **shebang**. When you run `./tui/app.py` directly from a Unix shell, the OS kernel uses `/usr/bin/env` to locate the first `python3` executable in your `PATH` and uses it to interpret the script.
* **Line 2 (`"""Interactive Textual TUI..."""`)**: The module-level **docstring**. Python attaches this string to the special `__doc__` attribute of the module for documentation tools and IDEs.

---

### 3.2 Standard Library Imports (Lines 6–14)

```python
import argparse
import asyncio
import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable
```

* **`import argparse`** (Line 6): Standard library module for parsing command-line flags (`-r`, `-b`, `-k`, `-d`, `--help`).
* **`import asyncio`** (Line 7): Python's asynchronous I/O framework. Used here to run `git clone` as a non-blocking subprocess (`asyncio.create_subprocess_exec`) and offload filesystem scanning (`asyncio.to_thread`) so the TUI never freezes while cloning.
* **`import os`** (Line 8): Operating system interfaces. Used for:
  * `os.walk()`: Recursively walking directory trees.
  * `os.path.expanduser()`: Turning `~` into the user's actual home directory (e.g., `/home/salem`).
  * `os.environ.copy()`: Copying current environment variables so we can inject `GIT_SSH_COMMAND` into the `git` child process.
* **`import shlex`** (Line 9): Shell lexical analysis tools. Specifically, `shlex.quote()` safely escapes strings (such as an SSH key path containing spaces or special characters) before embedding them in a shell command string like `GIT_SSH_COMMAND`.
* **`import shutil`** (Line 10): High-level file operations:
  * `shutil.copy2()`: Copies a file's contents **and** its metadata (modification timestamps, permissions).
  * `shutil.rmtree()`: Recursively deletes an entire directory tree (used to delete the temporary clone directory).
* **`import subprocess`** (Line 11): Provides standard subprocess constants (`subprocess.PIPE`, also aliased in `asyncio.subprocess.PIPE`).
* **`import tempfile`** (Line 12): Generates secure temporary files and directories (`tempfile.mkdtemp()`), equivalent to the `mktemp -d` command in Bash.
* **`from pathlib import Path`** (Line 13): Object-oriented filesystem paths. Allows joining paths cleanly with the `/` operator (e.g., `Path.cwd() / ".claude"`) and checking file properties (`.is_file()`, `.exists()`, `.mkdir()`).
* **`from typing import Iterable`** (Line 14): Type-checking helper indicating an object that can be looped over (passed to `SelectionList.add_options`).

---

### 3.3 Textual Framework Imports (Lines 16–32)

```python
from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.events import Key
from textual.suggester import SuggestFromList
from textual.widgets import (
    Button,
    Checkbox,
    Footer,
    Header,
    Input,
    Label,
    RichLog,
    SelectionList,
)
from textual.widgets.selection_list import Selection
```

* **`from textual import on, work`** (Line 16):
  * `@on(Event, "#selector")`: A decorator that connects a widget event (like `Button.Pressed` on button `#fetch-btn`) to a handler method, similar to `addEventListener` in web development.
  * `@work(exclusive=True)`: A decorator that turns a method into a background **Textual Worker** task so long-running tasks (like `git clone`) run in the background without locking up keyboard/mouse responsiveness.
* **`from textual.app import App, ComposeResult`** (Line 17):
  * `App`: The base class for any Textual application. Manages the screen, event loop, CSS stylesheet, keybindings, and widget tree.
  * `ComposeResult`: Return type annotation for `compose()`, representing a generator of `Widget` instances.
* **`from textual.binding import Binding`** (Line 18): Defines a keyboard shortcut mapping a key combination (like `"ctrl+a"`) to an action method (`"toggle_select_all"`) and a label displayed in the bottom `Footer`.
* **`from textual.containers import Horizontal, Vertical`** (Line 19): Layout containers that arrange their child widgets left-to-right (`Horizontal`) or top-to-bottom (`Vertical`).
* **`from textual.events import Key`** (Line 20): Event object emitted whenever the user presses a key on the keyboard.
* **`from textual.suggester import SuggestFromList`** (Line 21): Provides inline autocomplete suggestions inside an `Input` box from a predefined list of strings.
* **`from textual.widgets import ...`** (Lines 22–31): Built-in UI components:
  * `Button`: Clickable button widget.
  * `Checkbox`: Toggleable boolean checkbox (`[X]` / `[ ]`).
  * `Footer`: Bottom bar automatically displaying active keyboard shortcuts (`BINDINGS`).
  * `Header`: Top bar displaying the application `TITLE`.
  * `Input`: Single-line text box for user input.
  * `Label`: Static text label.
  * `RichLog`: Scrollable log window supporting colors and Rich markup (`[bold green]...[/]`).
  * `SelectionList`: Interactive multi-select checklist where each item can be checked/unchecked with `Space` or mouse click.
* **`from textual.widgets.selection_list import Selection`** (Line 32): Represents a single entry inside a `SelectionList`, holding `(display_label, underlying_value, initial_checked_state)`.

---

### 3.4 Global Constants (Lines 32–35)

```python
DEFAULT_REPO_URL = "git@github.com:SalemSaberhagen13/md-seeder.git"
DEFAULT_BRANCH = "master"
SUGGESTED_SSH_KEY = "~/.ssh/id_ed25519"
IGNORED_DIRS = (".git", "tui")
```

* **`DEFAULT_REPO_URL`** (Line 32): Default Git SSH URL pre-populated in the Repository URL input and `-r` CLI argument.
* **`DEFAULT_BRANCH`** (Line 33): Default Git branch (`"master"`) pre-populated in the Branch input and `-b` CLI argument.
* **`SUGGESTED_SSH_KEY`** (Line 34): Default suggested SSH private key path (`"~/.ssh/id_ed25519"`) shown as placeholder and autocomplete suggestion.
* **`IGNORED_DIRS`** (Line 35): Tuple of directory names (`(".git", "tui")`) that should be skipped when scanning a cloned repository for `.md` files so internal Git metadata and `tui/` documentation (`tui/README.md`) are never seeded.

---

### 3.5 `discover_markdown_files()` Function (Lines 38–53)

```python
def discover_markdown_files(root_dir: Path) -> list[Path]:
    """Recursively find all .md files under root_dir, skipping .git and tui."""
    md_files: list[Path] = []
    if not root_dir.exists():
        return md_files
    for dirpath, dirnames, filenames in os.walk(root_dir):
        for ignored in IGNORED_DIRS:
            if ignored in dirnames:
                dirnames.remove(ignored)
        dirnames.sort()
        for filename in sorted(filenames):
            if filename.lower().endswith(".md"):
                full_path = Path(dirpath) / filename
                if full_path.is_file():
                    md_files.append(full_path.relative_to(root_dir))
    return md_files
```

* **Line 38**: Defines a helper function accepting `root_dir` (a `Path` to the cloned repository) and returning a list of relative `Path` objects.
* **Line 40 (`md_files: list[Path] = []`)**: Initializes an empty list to collect matching `.md` paths.
* **Lines 41–42 (`if not root_dir.exists(): return md_files`)**: Safely returns an empty list if `root_dir` does not exist.
* **Line 43 (`for dirpath, dirnames, filenames in os.walk(root_dir):`)**: Walks the directory tree top-down.
* **Lines 44–46 (`for ignored in IGNORED_DIRS: if ignored in dirnames: dirnames.remove(ignored)`)**: Removes both `".git"` and `"tui"` from `dirnames` in-place so `os.walk` never descends into `.git/` or `tui/`, ignoring any `.md` files under `tui/`.
  1. `dirpath`: String path to the current directory being inspected.
  2. `dirnames`: List of subdirectory names inside `dirpath` (including hidden directories like `.claude/`!).
  3. `filenames`: List of file names inside `dirpath`.
* **Lines 43–44 (`if ".git" in dirnames: dirnames.remove(".git")`)**: Because `os.walk` traverses directories listed in `dirnames` in-place, removing `".git"` from `dirnames` prevents `os.walk` from wasting time descending into the `.git/` internal metadata folder, while still descending into other hidden folders such as `.claude/`.
* **Line 45 (`dirnames.sort()`)**: Sorts `dirnames` in-place alphabetically so subdirectories are always visited in deterministic alphabetical order.
* **Line 46 (`for filename in sorted(filenames):`)**: Loops through the files in the current directory in alphabetical order.
* **Line 47 (`if filename.lower().endswith(".md"):`)**: Converts the filename to lowercase before checking `.endswith(".md")`, so `README.md`, `notes.MD`, and `Doc.Md` all match.
* **Line 48 (`full_path = Path(dirpath) / filename`)**: Constructs the full path to the candidate file.
* **Line 49 (`if full_path.is_file():`)**: Ensures that `full_path` is an actual regular file (or symlink to a file) and **not** a directory whose name happens to end in `.md`.
* **Line 50 (`md_files.append(full_path.relative_to(root_dir))`)**: Strips the temporary directory prefix (`root_dir`) so only the clean path inside the repo (e.g. `CLAUDE.md` or `.claude/commands/review.md`) is stored.
* **Line 51 (`return md_files`)**: Returns the complete sorted list of relative `.md` paths.

---

### 3.6 `SeedClaudeApp` Class Definition & Styling (`CSS`) (Lines 54–110)

```python
class SeedClaudeApp(App[None]):
    """Textual TUI for cloning a repo and selecting .md files to copy into .claude."""

    TITLE = "md-seeder — Claude Markdown Seeder"
    CSS = """
    ...
    """
```

* **Line 54 (`class SeedClaudeApp(App[None]):`)**: Subclasses Textual's `App`. The `[None]` type parameter indicates that `app.run()` returns `None` when exiting.
* **Line 57 (`TITLE = ...`)**: Sets the title displayed in the top `Header` bar of the terminal.
* **Lines 58–110 (`CSS = """..."""`)**: Textual uses a dialect of CSS (TCSS) to position and style terminal widgets:
  * **`Screen` (Lines 59–62)**: Arranges top-level elements vertically (`layout: vertical`) and adds `1` row of top/bottom padding and `2` columns of left/right padding (`padding: 1 2`).
  * **`#main-split` (Lines 64–66)**: Gives the main horizontal split container `1fr` (one fractional unit of available vertical space), meaning it expands to fill the screen between the header and the bottom log panel.
  * **`#form-pane` (Lines 68–72)**: Left column. Takes `width: 1fr` (50% of screen width), adds `2` columns of inner right spacing (`padding-right: 2`), and draws a vertical divider line on its right edge (`border-right: solid $primary`).
  * **`#selection-pane` (Lines 74–77)**: Right column. Takes `width: 1fr` (the other 50% of screen width) and adds `2` columns of inner left spacing (`padding-left: 2`).
  * **`.section-title` (Lines 79–83)**: Styles section headers in bold (`text-style: bold`), uses the theme's `$accent` color, and leaves `1` empty line below (`margin-bottom: 1`).
  * **`.field-label` (Lines 85–88)**: Adds a `1`-line gap above each input label (`margin-top: 1`) and dims the text color (`$text-muted`).
  * **`.button-row` & `.button-row Button` (Lines 90–97)**: Sizes button bars tightly around their buttons (`height: auto`), adds `1` row of space above, and separates adjacent buttons by `1` column (`margin-right: 1`).
  * **`#md-list` (Lines 99–103)**: Expands the `SelectionList` to fill the right pane (`height: 1fr`) with a rounded border (`border: round $secondary`).
  * **`#log-panel` (Lines 105–109)**: Fixes the bottom `RichLog` panel at `10` rows tall (`height: 10`) with a subtle rounded border.

---

### 3.7 Keyboard Shortcuts (`BINDINGS`) (Lines 112–117)

```python
    BINDINGS = [
        Binding("ctrl+f", "fetch_repo", "Fetch Repo"),
        Binding("ctrl+a", "toggle_select_all", "Select/Deselect All .md", priority=True),
        Binding("ctrl+y", "copy_selected", "Confirm & Copy"),
        Binding("ctrl+q", "quit", "Quit"),
    ]
```

* When a user presses a bound key in Textual, Textual looks for a method named `action_<action_name>()`:
  * **`ctrl+f` → `"fetch_repo"`**: Calls `self.action_fetch_repo()`.
  * **`ctrl+a` → `"toggle_select_all"` (`priority=True`)**: Calls `self.action_toggle_select_all()`. Setting `priority=True` ensures `Ctrl+A` triggers Select/Deselect All for the `.md` file list globally—even if the user's cursor is currently inside an `Input` widget (which would otherwise capture `Ctrl+A` to select text).
  * **`ctrl+y` → `"copy_selected"`**: Calls `self.action_copy_selected()`.
  * **`ctrl+q` → `"quit"`**: Calls Textual's built-in `action_quit()` to cleanly exit the app.

---

### 3.8 Constructor (`__init__`) (Lines 119–132)

```python
    def __init__(
        self,
        repo_url: str = DEFAULT_REPO_URL,
        branch: str = DEFAULT_BRANCH,
        ssh_key: str = "",
        dest_dir: str | None = None,
    ) -> None:
        super().__init__()
        self.initial_repo_url = repo_url
        self.initial_branch = branch
        self.initial_ssh_key = ssh_key
        self.initial_dest_dir = dest_dir or str(Path.cwd() / ".claude")
        self.tmp_dir: Path | None = None
        self.discovered_files: list[Path] = []
```

* **Line 126 (`super().__init__()`)**: Initializes the parent `textual.app.App` internals.
* **Lines 127–130**: Stores the initial form field values (either defaults or values passed via CLI flags `-r`, `-b`, `-k`, `-d`) on `self` so `compose()` can populate the `Input` widgets when building the UI. If `dest_dir` is `None` or empty, it defaults to `<current_working_directory>/.claude`.
* **Line 131 (`self.tmp_dir: Path | None = None`)**: Tracks the path to the active temporary clone directory so it can be read during copying and deleted upon cleanup.
* **Line 132 (`self.discovered_files: list[Path] = []`)**: Stores the list of relative `.md` file paths discovered in the most recent clone.

---

### 3.9 UI Layout Builder (`compose`) (Lines 134–206)

```python
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-split"):
            with Vertical(id="form-pane"):
                ...
            with Vertical(id="selection-pane"):
                ...
        yield RichLog(id="log-panel", highlight=True, markup=True)
        yield Footer()
```

* **How `compose()` works**: Textual calls `compose()` once on startup to construct the widget tree. Using `yield` turns `compose()` into a Python **generator** that hands widgets one-by-one to Textual. Whenever `yield` occurs inside a `with Container(...):` block, Textual mounts those yielded widgets **inside** that container.
* **Line 135 (`yield Header()`)**: Renders the top title bar.
* **Line 136 (`with Horizontal(id="main-split"):`)**: Creates the two-column middle section.
* **Left Column — `#form-pane` (Lines 137–184)**:
  * **`#repo-input` (Lines 140–144)**: `Input` pre-filled with `self.initial_repo_url` (`git@github.com:SalemSaberhagen13/md-seeder.git`).
  * **`#branch-input` (Lines 149–153)**: `Input` pre-filled with `self.initial_branch` (`master`).
  * **`#ssh-input` (Lines 158–166)**: `Input` with `placeholder="~/.ssh/id_ed25519"` and `suggester=SuggestFromList(["~/.ssh/id_ed25519", "~/.ssh/id_rsa"], case_sensitive=True)`. As soon as you type `~`, Textual displays a ghost autocomplete suggestion for `~/.ssh/id_ed25519` that you can accept by pressing the Right Arrow key (`→`).
  * **`#dest-input` (Lines 168–172)**: `Input` pre-filled with `<cwd>/.claude`.
  * **`#preserve-dirs-checkbox` (Lines 173–177)**: `Checkbox` defaulting to `False` (flattening files into `.claude/`, matching `seed_claude.sh`). If checked (`True`), subdirectories like `docs/guide.md` are copied to `.claude/docs/guide.md`.
  * **Buttons (`#fetch-btn` and `#suggest-ssh-btn`, Lines 178–184)**: Side-by-side buttons to trigger cloning or immediately fill `~/.ssh/id_ed25519` into the SSH Key input.
* **Right Column — `#selection-pane` (Lines 186–203)**:
  * **`#md-list` (Line 190)**: `SelectionList[Path]` that holds the interactive checklist of discovered `.md` files.
  * **`#select-all-btn` & `#copy-btn` (Lines 191–203)**: Buttons for toggling Select All and confirming the copy operation. Both start with `disabled=True` until a repository has been fetched.
* **Bottom Panels (Lines 205–206)**:
  * **`#log-panel`**: `RichLog` widget with `highlight=True` (automatic syntax highlighting of paths/numbers) and `markup=True` (enables `[bold green]...[/]` styling tags).
  * **`Footer()`**: Bottom bar displaying keyboard shortcuts.

---

### 3.10 Lifecycle & Keyboard Event Handlers (`on_mount`, `on_key`) (Lines 208–227)

```python
    def on_mount(self) -> None:
        log = self.query_one("#log-panel", RichLog)
        log.write(
            "[bold cyan]Ready.[/] Configure repository settings and click "
            "[bold]Fetch .md Files[/] (or press [bold]Ctrl+F[/])."
        )

    def on_key(self, event: Key) -> None:
        """Allow pressing Right Arrow on empty SSH input to accept the suggested path."""
        focused = self.focused
        if (
            isinstance(focused, Input)
            and focused.id == "ssh-input"
            and not focused.value
            and event.key in ("right", "tab")
        ):
            if event.key == "right":
                focused.value = SUGGESTED_SSH_KEY
                focused.cursor_position = len(focused.value)
                event.stop()
```

* **`on_mount()` (Lines 208–213)**: Called automatically by Textual right after all widgets from `compose()` are mounted on screen. It looks up `#log-panel` using `self.query_one("#log-panel", RichLog)` (similar to `document.querySelector` in JavaScript, with type verification) and writes the initial welcome instructions.
* **`on_key()` (Lines 215–227)**: Textual's built-in `SuggestFromList` only activates after at least 1 character is typed. `on_key` enhances this: if the user focuses the empty `#ssh-input` field (`not focused.value`) and immediately presses the Right Arrow key (`event.key == "right"`), it fills in `SUGGESTED_SSH_KEY` (`"~/.ssh/id_ed25519"`), moves the cursor to the end of the text, and calls `event.stop()` so the key event isn't processed further.

---

### 3.11 Button Click Handlers (`@on`) (Lines 229–245)

```python
    @on(Button.Pressed, "#suggest-ssh-btn")
    def handle_suggest_ssh(self) -> None:
        ssh_input = self.query_one("#ssh-input", Input)
        ssh_input.value = SUGGESTED_SSH_KEY
        ssh_input.focus()

    @on(Button.Pressed, "#fetch-btn")
    def handle_fetch_button(self) -> None:
        self.action_fetch_repo()

    @on(Button.Pressed, "#select-all-btn")
    def handle_select_all_button(self) -> None:
        self.action_toggle_select_all()

    @on(Button.Pressed, "#copy-btn")
    def handle_copy_button(self) -> None:
        self.action_copy_selected()
```

* Each `@on(Button.Pressed, "#button-id")` method listens for a button click on that specific button ID and delegates to the corresponding `action_*` method so clicking the button and pressing the keyboard shortcut execute the exact same code path.

---

### 3.12 Validation Action (`action_fetch_repo`) (Lines 247–266)

```python
    def action_fetch_repo(self) -> None:
        repo_url = self.query_one("#repo-input", Input).value.strip()
        branch = self.query_one("#branch-input", Input).value.strip()
        ssh_key = self.query_one("#ssh-input", Input).value.strip()
        log = self.query_one("#log-panel", RichLog)

        if not repo_url:
            log.write("[bold red]Error:[/] Repository URL (-r) cannot be empty.")
            return

        expanded_ssh_key = ""
        if ssh_key:
            expanded_ssh_key = os.path.expanduser(ssh_key)
            if not Path(expanded_ssh_key).is_file():
                log.write(
                    f"[bold red]Error:[/] SSH key file not found: [bold]{expanded_ssh_key}[/]"
                )
                return

        self._clone_and_scan(repo_url, branch, expanded_ssh_key)
```

* **Lines 248–250**: Reads the current text inside `#repo-input`, `#branch-input`, and `#ssh-input`, calling `.strip()` to remove accidental leading/trailing whitespace.
* **Lines 253–255**: Ensures `repo_url` is not empty; if empty, logs an error and aborts.
* **Lines 257–264**: If the user entered an SSH key path:
  * Expands `~` to the user's home folder via `os.path.expanduser(ssh_key)`.
  * Verifies the key file actually exists on disk (`Path(expanded_ssh_key).is_file()`) **before** running `git clone`, giving an immediate, clear error message if the path is mistyped.
* **Line 266**: Starts the asynchronous worker `self._clone_and_scan(...)`.

---

### 3.13 Async Worker (`_clone_and_scan`) (Lines 268–345)

```python
    @work(exclusive=True)
    async def _clone_and_scan(
        self, repo_url: str, branch: str, expanded_ssh_key: str
    ) -> None:
```

* **Line 268 (`@work(exclusive=True)`)**: Runs `_clone_and_scan` as an asynchronous background worker. `exclusive=True` ensures that if a previous clone worker was somehow still running, it is automatically cancelled before starting a new one.
* **Lines 278–281**: Disables the Fetch, Select All, and Copy buttons while cloning is in progress and clears any previous items in `#md-list`.
* **Lines 283–285**:
  * Calls `self._cleanup_tmp_dir()` to delete any leftover temporary directory from an earlier fetch.
  * Creates a fresh temporary directory via `tempfile.mkdtemp(prefix="md_seeder_")` (e.g., `/tmp/md_seeder_x9a8b7c6`) and saves it to `self.tmp_dir`.
* **Lines 292–300**: Clones the current process environment (`os.environ.copy()`). If `expanded_ssh_key` was provided:
  * Quotes the path safely with `shlex.quote(expanded_ssh_key)`.
  * Sets `env["GIT_SSH_COMMAND"] = f"ssh -i {quoted_key} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"`:
    * `-i <key>`: Uses the specified private key file.
    * `-o IdentitiesOnly=yes`: Prevents SSH from trying other keys loaded in `ssh-agent` first (which can cause "Too many authentication failures").
    * `-o StrictHostKeyChecking=accept-new`: Automatically accepts the host key the first time connecting to a new server without hanging on an interactive `yes/no` prompt inside a background process.
* **Lines 302–305**: Builds the `git clone` argument list:
  * `["git", "clone", "--quiet", "--depth", "1"]`: Shallow clone of only the single latest commit (`--depth 1`) to minimize network transfer.
  * `if branch: cmd.extend(["--branch", branch])`: Only passes `--branch` if the user specified one; if blank, `git` automatically clones the remote's default `HEAD` branch.
  * `cmd.extend(["--", repo_url, str(tmp_dir)])`: The `--` end-of-options marker prevents a malformed `repo_url` starting with `-` from being misinterpreted as a `git clone` flag.
* **Lines 307–318**: Runs `git` asynchronously without shell interpolation (`asyncio.create_subprocess_exec(*cmd, ...)`), waits for completion (`await proc.communicate()`), and catches OS-level errors (e.g., `git` not installed).
* **Lines 320–325**: Re-enables the Fetch button. If `proc.returncode != 0`, decodes `stderr`, prints the exact Git error to the log panel, cleans up the failed temp directory, and returns.
* **Line 327 (`files = await asyncio.to_thread(discover_markdown_files, tmp_dir)`)**: Runs `discover_markdown_files(tmp_dir)` in a separate thread so walking a massive repo never blocks UI rendering.
* **Lines 334–340**: Wraps each relative `Path` into a `Selection(str(rel_path), rel_path, False)` (initially unchecked), populates `#md-list`, enables the **Select / Deselect All** and **Confirm & Copy** buttons, and moves keyboard focus directly to `#md-list`.

---

### 3.14 Select/Deselect All Action (`action_toggle_select_all`) (Lines 347–354)

```python
    def action_toggle_select_all(self) -> None:
        md_list = self.query_one("#md-list", SelectionList)
        if not self.discovered_files:
            return
        if len(md_list.selected) == len(self.discovered_files):
            md_list.deselect_all()
        else:
            md_list.select_all()
```

* Triggered by pressing `Ctrl+A` or clicking **Select / Deselect All**:
  * If no files have been fetched yet, it does nothing.
  * If all files are currently checked (`len(md_list.selected) == len(self.discovered_files)`), it unchecks all of them (`md_list.deselect_all()`).
  * Otherwise, it checks every file in the list (`md_list.select_all()`).

---

### 3.15 Confirm & Copy Action (`action_copy_selected`) (Lines 356–399)

```python
    def action_copy_selected(self) -> None:
        ...
```

* **Lines 357–360**: Queries the log widget, the selection list, the destination path input (`#dest-input`), and the boolean state of `#preserve-dirs-checkbox`.
* **Lines 362–372**: Verifies that a temporary clone exists and that at least one `.md` file is checked in `#md-list`.
* **Lines 374–379**: Expands `~` in the destination directory and creates it (`dest_dir.mkdir(parents=True, exist_ok=True)`), equivalent to `mkdir -p "$DEST_DIR"`.
* **Lines 381–395**: Loops through each selected relative `Path` (`rel_path`):
  * Computes `src_file = self.tmp_dir / rel_path`.
  * Computes `target_file`:
    * If **Preserve subdirectory structure** is checked (`preserve_dirs == True`), `target_file = dest_dir / rel_path` (e.g., `.claude/docs/api.md`).
    * If unchecked (`preserve_dirs == False`), `target_file = dest_dir / rel_path.name` (flattening it to `.claude/api.md`, matching `seed_claude.sh`).
  * Ensures the parent folder exists (`target_file.parent.mkdir(parents=True, exist_ok=True)`), copies the file with `shutil.copy2(src_file, target_file)`, and logs the operation.
* **Lines 397–399**: Prints the final summary (`Magic done! Copied N file(s) to ...`).

---

### 3.16 Temporary Directory Cleanup (`_cleanup_tmp_dir`, `on_unmount`) (Lines 401–407)

```python
    def _cleanup_tmp_dir(self) -> None:
        if self.tmp_dir and self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir, ignore_errors=True)
        self.tmp_dir = None

    def on_unmount(self) -> None:
        self._cleanup_tmp_dir()
```

* **`_cleanup_tmp_dir()`**: Recursively removes `self.tmp_dir` if it exists on disk and resets `self.tmp_dir = None`.
* **`on_unmount()`**: Textual lifecycle hook called when the application exits (comparable to `trap 'rm -rf "$TMP_DIR"' EXIT` in Bash), guaranteeing no temporary clone folders are left behind in `/tmp`.

---

### 3.17 CLI Argument Parser (`parse_args`, `main`) (Lines 410–453)

```python
def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TUI to seed Claude .md files from a Git repository."
    )
    parser.add_argument("-r", "--repo", default=DEFAULT_REPO_URL, ...)
    parser.add_argument("-b", "--branch", default=DEFAULT_BRANCH, ...)
    parser.add_argument("-k", "--ssh-key", default="", ...)
    parser.add_argument("-d", "--dest", default=str(Path.cwd() / ".claude"), ...)
    return parser.parse_args(argv)


def main() -> None:
    args = parse_args()
    app = SeedClaudeApp(
        repo_url=args.repo,
        branch=args.branch,
        ssh_key=args.ssh_key,
        dest_dir=args.dest,
    )
    app.run()


if __name__ == "__main__":
    main()
```

* **`parse_args()` (Lines 410–438)**: Configures `argparse` so users can optionally pass `-r`, `-b`, `-k`, and `-d` from the terminal to pre-fill the TUI form inputs.
* **`main()` (Lines 441–449)**: Parses CLI arguments, instantiates `SeedClaudeApp` with those initial values, and starts the Textual event loop via `app.run()`.
* **`if __name__ == "__main__":` (Lines 452–453)**: Standard Python idiom ensuring `main()` only runs when `seed_claude_tui.py` is executed as a script, not when another script or test imports functions/classes from it.

---

## 4. `run_tui.sh` — Complete Line-by-Line Breakdown

```bash
#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
TUI_DIR="$SCRIPT_DIR/tui"
VENV_DIR="$TUI_DIR/.venv"

if [[ ! -d "$VENV_DIR" ]]; then
    echo "Creating virtual environment in $VENV_DIR..."
    python3 -m venv "$VENV_DIR"
fi

if ! "$VENV_DIR/bin/python" -c "import textual" &>/dev/null; then
    echo "Installing dependencies into $VENV_DIR..."
    "$VENV_DIR/bin/pip" install --quiet -r "$TUI_DIR/requirements.txt"
fi

exec "$VENV_DIR/bin/python" "$TUI_DIR/app.py" "$@"
```

* **Line 1 (`#!/usr/bin/env bash`)**: Runs the script using `bash` from the user's `PATH`.
* **Line 2 (`set -euo pipefail`)**: Strict Bash error handling mode (`-e`, `-u`, `-o pipefail`).
* **Line 4 (`SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"`)**: Resolves the absolute directory where `run_tui.sh` lives.
* **Line 5 (`TUI_DIR="$SCRIPT_DIR/tui"`)**: Points to the `tui` folder containing the Python application, requirements, and virtual environment.
* **Line 6 (`VENV_DIR="$TUI_DIR/.venv"`)**: Points to the `.venv` folder inside `tui/`.
* **Lines 8–11 (`if [[ ! -d "$VENV_DIR" ]]; then ...`)**: Creates `tui/.venv` if it does not exist yet.
* **Lines 13–16 (`if ! "$VENV_DIR/bin/python" -c "import textual" &>/dev/null; then ...`)**: Installs `tui/requirements.txt` into `tui/.venv` if `textual` is not yet installed.
* **Line 18 (`exec "$VENV_DIR/bin/python" "$TUI_DIR/app.py" "$@"`)**: Replaces the shell process with `tui/.venv/bin/python tui/app.py`, forwarding all CLI flags (`"$@"`).

---

## 5. `seed_claude.sh` — Complete Line-by-Line Breakdown

```bash
#!/usr/bin/env bash
set -euo pipefail

# DEFAULT VARS
BRANCH="master"  # or tag, is the same
REPO_URL=""
SSH_KEY=""
DEST_DIR="$(pwd)/.claude"
```

* **Lines 1–2**: Shebang and strict error mode (`-e`, `-u`, `-o pipefail`).
* **Lines 5–8**: Initializes default variables:
  * `BRANCH="master"`: Default branch or tag name.
  * `REPO_URL=""`: Empty by default (must be supplied via `-r`).
  * `SSH_KEY=""`: Empty by default (optional via `-k`).
  * `DEST_DIR="$(pwd)/.claude"`: Evaluates `pwd` (present working directory) in a subshell `$(...)` and appends `/.claude`.

```bash
usage() {
    echo "Use: $0 -r <git@github.com:user/repo.git> [-b <branch>] [-k <path_ssh_key>]"
    exit 1
}
```

* **Lines 10–13 (`usage()`)**: Defines a helper function that prints how to invoke the script (`$0` expands to the script's name/path) and terminates the script with exit code `1` (indicating an error).

```bash
while getopts "r:b:k:h" opt; do
    case "$opt" in
        r) REPO_URL="$OPTARG" ;; # -r git@github...
        b) BRANCH="$OPTARG" ;;   # -b master
        k) SSH_KEY="$OPTARG" ;;  # -k ~/.ssh/id_ed25519
        *) usage ;;              # you failed
    esac
done
```

* **Lines 15–22 (`while getopts "r:b:k:h" opt`)**: Built-in POSIX option parser:
  * In the option string `"r:b:k:h"`, a colon (`:`) after a letter means that flag requires an argument (which Bash places in `$OPTARG`). `h` has no colon because `-h` takes no argument.
  * Each iteration sets `$opt` to the matched flag letter and uses `case "$opt" in` to assign `REPO_URL`, `BRANCH`, or `SSH_KEY`, or call `usage` on `-h` or any unrecognized option (`*`).

```bash
if [[ -z "$REPO_URL" ]] ; then  # You failed miserably
    usage
fi
```

* **Lines 24–26 (`[[ -z "$REPO_URL" ]]`)**: The `-z` test checks if the string length of `$REPO_URL` is zero (empty). Because `-r` is mandatory, if `REPO_URL` is still empty after parsing flags, it prints usage and exits.

```bash
TMP_DIR=$(mktemp -d)  # Creates folder under /tmp . Command is evaluated as a path.
# Cleans stuff if something fails for whatever reason. Even if it is temporary
trap 'rm -rf "$TMP_DIR"' EXIT
```

* **Line 28 (`TMP_DIR=$(mktemp -d)`)**: Creates a unique temporary directory under `/tmp` (e.g., `/tmp/tmp.AbCdEfGhIj`) and stores its path in `TMP_DIR`.
* **Line 30 (`trap 'rm -rf "$TMP_DIR"' EXIT`)**: Registers a signal handler on the `EXIT` pseudo-signal. Whether the script finishes normally on line 50 or aborts early due to `set -e` when a command fails, Bash executes `rm -rf "$TMP_DIR"` before terminating.

```bash
echo -e "Downloading branch/version $BRANCH from $REPO_URL\nPlease wait..."

if [[ -z "$SSH_KEY" ]] ; then
    echo "Hope you've set up your ssh agent"
    git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP_DIR"
else
    GIT_SSH_COMMAND="ssh -i \"$SSH_KEY\" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new" \
    git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP_DIR"
fi
```

* **Line 32 (`echo -e "..."`)**: The `-e` flag enables interpretation of backslash escapes like `\n` (newline).
* **Lines 34–40**: Checks whether `SSH_KEY` is empty (`-z`):
  * If empty, runs `git clone --quiet --depth 1 --branch "$BRANCH" "$REPO_URL" "$TMP_DIR"` relying on the user's default SSH agent/config.
  * If provided, prefixes the command with `GIT_SSH_COMMAND="..."` (which sets that environment variable **only** for the `git clone` command that follows it).

```bash
mkdir -p "$DEST_DIR"

shopt -s nullglob globstar # claude says this prevent errors in case of no md files
for file in "$TMP_DIR"/**/*.md; do
    echo "cp -f $file $DEST_DIR/"
    cp -f "$file" "$DEST_DIR/"
done

echo 'Magic done'
```

* **Line 42 (`mkdir -p "$DEST_DIR"`)**: Creates `.claude` (and any missing parent directories) if it doesn't already exist; does not error if it already exists.
* **Line 44 (`shopt -s nullglob globstar`)**: Enables (`-s` = set) two Bash shell options:
  * `nullglob`: If no files match a glob pattern (`*.md`), expand the pattern to nothing (0 words) instead of leaving the literal string `"$TMP_DIR/**/*.md"`, preventing `cp` from failing on a non-existent literal filename.
  * `globstar`: Enables the `**` recursive wildcard so `"$TMP_DIR"/**/*.md` matches `.md` files in `$TMP_DIR` and all non-hidden subdirectories.
* **Lines 45–48**: Loops over each matched `.md` path, echoes the copy command, and runs `cp -f "$file" "$DEST_DIR/"` (`-f` forces overwrite if a file with the same name already exists in `.claude/`).
* **Line 50 (`echo 'Magic done'`)**: Prints completion message before triggering the `EXIT` trap that cleans up `$TMP_DIR`.

---

## 6. `requirements.txt` & `.gitignore`

### `requirements.txt`
```text
textual>=0.80.0
```
* Declares that the project requires the `textual` package (version `0.80.0` or newer) from PyPI, which also automatically installs `rich` for terminal formatting.

### `.gitignore`
```gitignore
.venv/
__pycache__/
*.pyc
.pytest_cache/
```
* **`.venv/`**: Ignores the local Python virtual environment directory.
* **`__pycache__/` & `*.pyc`**: Ignores compiled Python bytecode cache files generated when Python imports modules.
* **`.pytest_cache/`**: Ignores test runner cache directories.
