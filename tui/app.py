#!/usr/bin/env python3
"""Interactive Textual TUI for seeding Claude markdown files from a Git repository."""

import argparse
import asyncio
import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Iterable

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

DEFAULT_REPO_URL = "git@github.com:SalemSaberhagen13/md-seeder.git"
DEFAULT_BRANCH = "master"
SUGGESTED_SSH_KEY = "~/.ssh/id_ed25519"
IGNORED_DIRS = (".git", "tui")


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


class SeedClaudeApp(App[None]):
    """Textual TUI for cloning a repo and selecting .md files to copy into .claude."""

    TITLE = "md-seeder — Claude Markdown Seeder"
    CSS = """
    Screen {
        layout: vertical;
        padding: 1 2;
    }

    #main-split {
        height: 1fr;
    }

    #form-pane {
        width: 1fr;
        padding-right: 2;
        border-right: solid $primary;
    }

    #selection-pane {
        width: 1fr;
        padding-left: 2;
    }

    .section-title {
        text-style: bold;
        color: $accent;
        margin-bottom: 1;
    }

    .field-label {
        margin-top: 1;
        color: $text-muted;
    }

    .button-row {
        height: auto;
        margin-top: 1;
    }

    .button-row Button {
        margin-right: 1;
    }

    #md-list {
        height: 1fr;
        border: round $secondary;
        margin-top: 1;
    }

    #log-panel {
        height: 10;
        border: round $surface-lighten-2;
        margin-top: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+f", "fetch_repo", "Fetch Repo"),
        Binding("ctrl+a", "toggle_select_all", "Select/Deselect All .md", priority=True),
        Binding("ctrl+y", "copy_selected", "Confirm & Copy"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

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

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal(id="main-split"):
            with Vertical(id="form-pane"):
                yield Label("1. Repository Configuration", classes="section-title")
                yield Label("Repository URL (-r):", classes="field-label")
                yield Input(
                    value=self.initial_repo_url,
                    placeholder=DEFAULT_REPO_URL,
                    id="repo-input",
                )
                yield Label(
                    "Branch or Tag (-b) [leave blank for remote default]:",
                    classes="field-label",
                )
                yield Input(
                    value=self.initial_branch,
                    placeholder=DEFAULT_BRANCH,
                    id="branch-input",
                )
                yield Label(
                    f"SSH Key Path (-k) [optional, press → for {SUGGESTED_SSH_KEY}]:",
                    classes="field-label",
                )
                yield Input(
                    value=self.initial_ssh_key,
                    placeholder=SUGGESTED_SSH_KEY,
                    suggester=SuggestFromList(
                        [SUGGESTED_SSH_KEY, "~/.ssh/id_rsa"],
                        case_sensitive=True,
                    ),
                    id="ssh-input",
                )
                yield Label("Destination Directory (-d):", classes="field-label")
                yield Input(
                    value=self.initial_dest_dir,
                    placeholder=str(Path.cwd() / ".claude"),
                    id="dest-input",
                )
                yield Checkbox(
                    "Preserve subdirectory structure",
                    value=False,
                    id="preserve-dirs-checkbox",
                )
                with Horizontal(classes="button-row"):
                    yield Button("Fetch .md Files", variant="primary", id="fetch-btn")
                    yield Button(
                        f"Use {SUGGESTED_SSH_KEY}",
                        variant="default",
                        id="suggest-ssh-btn",
                    )

            with Vertical(id="selection-pane"):
                yield Label(
                    "2. Select Markdown Files to Copy", classes="section-title"
                )
                yield SelectionList[Path](id="md-list")
                with Horizontal(classes="button-row"):
                    yield Button(
                        "Select / Deselect All (Ctrl+A)",
                        variant="default",
                        id="select-all-btn",
                        disabled=True,
                    )
                    yield Button(
                        "Confirm & Copy Selected (Ctrl+Y)",
                        variant="success",
                        id="copy-btn",
                        disabled=True,
                    )

        yield RichLog(id="log-panel", highlight=True, markup=True)
        yield Footer()

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

    @work(exclusive=True)
    async def _clone_and_scan(
        self, repo_url: str, branch: str, expanded_ssh_key: str
    ) -> None:
        log = self.query_one("#log-panel", RichLog)
        fetch_btn = self.query_one("#fetch-btn", Button)
        select_all_btn = self.query_one("#select-all-btn", Button)
        copy_btn = self.query_one("#copy-btn", Button)
        md_list = self.query_one("#md-list", SelectionList)

        fetch_btn.disabled = True
        select_all_btn.disabled = True
        copy_btn.disabled = True
        md_list.clear_options()

        self._cleanup_tmp_dir()
        tmp_dir = Path(tempfile.mkdtemp(prefix="md_seeder_"))
        self.tmp_dir = tmp_dir

        branch_label = branch if branch else "default HEAD"
        log.write(
            f"Downloading branch/version [bold]{branch_label}[/] from [bold]{repo_url}[/]..."
        )

        env = os.environ.copy()
        if not expanded_ssh_key:
            log.write("[dim]No SSH key specified; using existing SSH agent/config.[/]")
        else:
            quoted_key = shlex.quote(expanded_ssh_key)
            env["GIT_SSH_COMMAND"] = (
                f"ssh -i {quoted_key} -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
            )
            log.write(f"[dim]Using SSH key: {expanded_ssh_key}[/]")

        cmd = ["git", "clone", "--quiet", "--depth", "1"]
        if branch:
            cmd.extend(["--branch", branch])
        cmd.extend(["--", repo_url, str(tmp_dir)])

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            _, stderr_bytes = await proc.communicate()
        except Exception as exc:
            log.write(f"[bold red]Failed to execute git:[/] {exc}")
            fetch_btn.disabled = False
            return

        fetch_btn.disabled = False
        if proc.returncode != 0:
            err_msg = stderr_bytes.decode(errors="replace").strip()
            log.write(f"[bold red]git clone failed (exit {proc.returncode}):[/] {err_msg}")
            self._cleanup_tmp_dir()
            return

        files = await asyncio.to_thread(discover_markdown_files, tmp_dir)
        self.discovered_files = files

        if not files:
            log.write("[bold yellow]Warning:[/] No .md files found in the repository.")
            return

        selections: Iterable[Selection[Path]] = [
            Selection(str(rel_path), rel_path, False) for rel_path in files
        ]
        md_list.add_options(selections)
        select_all_btn.disabled = False
        copy_btn.disabled = False
        md_list.focus()
        log.write(
            f"[bold green]Found {len(files)} markdown file(s).[/] "
            "Check the files you want, press [bold]Ctrl+A[/] to select all, "
            "then press [bold]Ctrl+Y[/] to copy."
        )

    def action_toggle_select_all(self) -> None:
        md_list = self.query_one("#md-list", SelectionList)
        if not self.discovered_files:
            return
        if len(md_list.selected) == len(self.discovered_files):
            md_list.deselect_all()
        else:
            md_list.select_all()

    def action_copy_selected(self) -> None:
        log = self.query_one("#log-panel", RichLog)
        md_list = self.query_one("#md-list", SelectionList)
        dest_raw = self.query_one("#dest-input", Input).value.strip()
        preserve_dirs = self.query_one("#preserve-dirs-checkbox", Checkbox).value

        if not self.tmp_dir or not self.tmp_dir.exists():
            log.write("[bold red]Error:[/] Please fetch a repository first.")
            return

        selected_paths: list[Path] = list(md_list.selected)
        if not selected_paths:
            log.write(
                "[bold yellow]No files selected.[/] Check at least one .md file "
                "(or press [bold]Ctrl+A[/] to select all) before copying."
            )
            return

        dest_dir = Path(os.path.expanduser(dest_raw or str(Path.cwd() / ".claude")))
        try:
            dest_dir.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            log.write(f"[bold red]Cannot create destination directory:[/] {exc}")
            return

        copied_count = 0
        for rel_path in selected_paths:
            src_file = self.tmp_dir / rel_path
            if not src_file.is_file():
                continue
            target_file = (
                dest_dir / rel_path if preserve_dirs else dest_dir / rel_path.name
            )
            try:
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src_file, target_file)
                log.write(f"cp -f {src_file} -> [bold]{target_file}[/]")
                copied_count += 1
            except OSError as exc:
                log.write(f"[bold red]Failed copying {rel_path}:[/] {exc}")

        log.write(
            f"[bold green]Magic done![/] Copied {copied_count} file(s) to [bold]{dest_dir}[/]."
        )

    def _cleanup_tmp_dir(self) -> None:
        if self.tmp_dir and self.tmp_dir.exists():
            shutil.rmtree(self.tmp_dir, ignore_errors=True)
        self.tmp_dir = None

    def on_unmount(self) -> None:
        self._cleanup_tmp_dir()


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="TUI to seed Claude .md files from a Git repository."
    )
    parser.add_argument(
        "-r",
        "--repo",
        default=DEFAULT_REPO_URL,
        help=f"Git repository URL (default: {DEFAULT_REPO_URL})",
    )
    parser.add_argument(
        "-b",
        "--branch",
        default=DEFAULT_BRANCH,
        help=f"Branch or tag to clone (default: {DEFAULT_BRANCH})",
    )
    parser.add_argument(
        "-k",
        "--ssh-key",
        default="",
        help=f"Optional SSH private key path (e.g., {SUGGESTED_SSH_KEY})",
    )
    parser.add_argument(
        "-d",
        "--dest",
        default=str(Path.cwd() / ".claude"),
        help="Destination directory (default: ./.claude)",
    )
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
