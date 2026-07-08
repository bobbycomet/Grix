"""
Grix Linux Academy - Sandbox Terminal
========================================

A small, in-memory simulated filesystem and command interpreter.
This lets beginners practice commands like cd, ls, mkdir, rm, cat,
grep, etc. WITHOUT touching their real computer.

Only a safe subset of commands is implemented. Anything not
recognized returns a friendly "not available in the sandbox"
message rather than an error that looks like a real failure.

This is intentionally simple - it is a teaching tool, not a real
shell. Commands are parsed with shlex and matched against a small
dispatch table.
"""

from __future__ import annotations

import shlex
from dataclasses import dataclass, field


@dataclass
class SandboxNode:
    """A file or directory in the simulated filesystem."""
    name: str
    is_dir: bool
    content: str = ""              # for files
    children: dict[str, "SandboxNode"] = field(default_factory=dict)
    hidden: bool = False


def _default_filesystem() -> SandboxNode:
    """Build the starting simulated home directory."""
    home = SandboxNode("user", is_dir=True)
    home.children["Documents"] = SandboxNode("Documents", is_dir=True)
    home.children["Pictures"] = SandboxNode("Pictures", is_dir=True)
    home.children["Downloads"] = SandboxNode("Downloads", is_dir=True)
    home.children[".bashrc"] = SandboxNode(
        ".bashrc", is_dir=False,
        content="# ~/.bashrc: executed by bash for non-login shells\n"
                "export PATH=$HOME/bin:$PATH\n",
        hidden=True,
    )
    home.children[".config"] = SandboxNode(".config", is_dir=True, hidden=True)
    home.children["Documents"].children["report.txt"] = SandboxNode(
        "report.txt", is_dir=False,
        content="Quarterly Report\n=================\nEverything is on track.\n",
    )
    return home


class SandboxTerminal:
    """A safe, simulated terminal session for Grix Academy lessons."""

    def __init__(self):
        self.root = SandboxNode("/", is_dir=True)
        home_user = _default_filesystem()
        home_dir = SandboxNode("home", is_dir=True)
        home_dir.children["user"] = home_user
        self.root.children["home"] = home_dir
        for sysdir in ("etc", "var", "usr", "tmp"):
            self.root.children[sysdir] = SandboxNode(sysdir, is_dir=True)

        self.home_path = ["home", "user"]
        self.cwd = list(self.home_path)  # path components from root
        self.username = "user"
        self.hostname = "grix-sandbox"
        self.env = {
            "PATH": "/usr/local/bin:/usr/bin:/bin",
            "HOME": "/home/user",
            "USER": "user",
            "SHELL": "/bin/bash",
        }
        self.aliases: dict[str, str] = {}

    # -- path helpers --------------------------------------------------

    def _resolve(self, path: str) -> list[str] | None:
        """Resolve a path string to a list of components from root.
        Returns None if invalid."""
        if path in ("~", ""):
            parts = list(self.home_path)
        elif path.startswith("~/"):
            parts = list(self.home_path) + path[2:].split("/")
        elif path.startswith("/"):
            parts = path.strip("/").split("/")
        else:
            parts = list(self.cwd) + path.split("/")

        resolved: list[str] = []
        for part in parts:
            if part in ("", "."):
                continue
            elif part == "..":
                if resolved:
                    resolved.pop()
            else:
                resolved.append(part)
        return resolved

    def _get_node(self, parts: list[str]) -> SandboxNode | None:
        node = self.root
        for part in parts:
            if not node.is_dir or part not in node.children:
                return None
            node = node.children[part]
        return node

    def _prompt_path(self) -> str:
        full = "/" + "/".join(self.cwd)
        if self.cwd[: len(self.home_path)] == self.home_path:
            rest = self.cwd[len(self.home_path):]
            return "~" + ("/" + "/".join(rest) if rest else "")
        return full

    @property
    def prompt(self) -> str:
        return f"{self.username}@{self.hostname}:{self._prompt_path()}$"

    # -- public API ------------------------------------------------------

    def run(self, line: str) -> str:
        """Run one command line, return output text (no trailing prompt)."""
        line = line.strip()
        if not line:
            return ""

        try:
            tokens = shlex.split(line)
        except ValueError as exc:
            return f"bash: syntax error: {exc}"

        if not tokens:
            return ""

        # Handle a single pipe: cmd1 | cmd2
        if "|" in tokens:
            idx = tokens.index("|")
            left = tokens[:idx]
            right = tokens[idx + 1:]
            if not left or not right:
                return "bash: syntax error near unexpected token `|'"
            left_out = self._dispatch(left)
            return self._dispatch(right, stdin=left_out)

        # Handle redirection: cmd > file or cmd >> file
        if ">>" in tokens or ">" in tokens:
            append = ">>" in tokens
            sep = ">>" if append else ">"
            idx = tokens.index(sep)
            cmd_tokens = tokens[:idx]
            target_tokens = tokens[idx + 1:]
            if not target_tokens:
                return f"bash: syntax error near unexpected token `{sep}'"
            target = target_tokens[0]
            output = self._dispatch(cmd_tokens)
            if output.startswith("bash:") or output.startswith("ERROR:"):
                return output
            return self._write_file(target, output, append=append)

        return self._dispatch(tokens)

    # -- command dispatch --------------------------------------------------

    def _dispatch(self, tokens: list[str], stdin: str | None = None) -> str:
        cmd, *args = tokens
        # Command names with hyphens (e.g. "ssh-keygen") map to methods
        # with underscores, since Python identifiers can't contain "-".
        handler = getattr(self, f"_cmd_{cmd.replace('-', '_')}", None)
        if handler is None:
            return (
                f"bash: {cmd}: command not found in the sandbox.\n"
                f"This sandbox supports a safe subset of commands for "
                f"practice (pwd, cd, ls, mkdir, touch, rm, rmdir, cat, "
                f"echo, mv, cp, grep, wc, head, tail, whoami, find, which, "
                f"sed, awk, xargs, tar, alias, export, env, ssh, "
                f"ssh-keygen, rsync, nano, lsb_release, uname, df, du, ps, "
                f"systemctl, journalctl, lspci, ip, clear, help)."
            )
        try:
            return handler(args, stdin)
        except Exception as exc:  # pragma: no cover
            return f"bash: {cmd}: {exc}"

    # -- individual command implementations --------------------------------

    def _cmd_help(self, args, stdin):
        return (
            "Sandbox commands available:\n"
            "  pwd, cd, ls, mkdir, touch, rm, rmdir, cat, echo, mv, cp,\n"
            "  grep, wc, head, tail, whoami, find, which, sed, awk, xargs,\n"
            "  tar, alias, export, env, ssh, ssh-keygen, rsync, nano,\n"
            "  lsb_release, uname, df, du, ps, systemctl, journalctl,\n"
            "  lspci, ip, clear\n\n"
            "This is a simulated filesystem - nothing you do here affects\n"
            "your real computer."
        )

    def _cmd_clear(self, args, stdin):
        return "\x1bCLEAR\x1b"  # special marker the UI intercepts

    def _cmd_pwd(self, args, stdin):
        return "/" + "/".join(self.cwd)

    def _cmd_whoami(self, args, stdin):
        return self.username

    def _cmd_cd(self, args, stdin):
        target = args[0] if args else "~"
        parts = self._resolve(target)
        if parts is None:
            return f"bash: cd: {target}: No such file or directory"
        node = self._get_node(parts)
        if node is None:
            return f"bash: cd: {target}: No such file or directory"
        if not node.is_dir:
            return f"bash: cd: {target}: Not a directory"
        self.cwd = parts
        return ""

    def _cmd_ls(self, args, stdin):
        show_all = False
        long_fmt = False
        paths = []
        for a in args:
            if a.startswith("-"):
                if "a" in a:
                    show_all = True
                if "l" in a:
                    long_fmt = True
            else:
                paths.append(a)

        if not paths:
            parts = self.cwd
        else:
            # wildcard support for *.ext patterns against current dir only
            pattern = paths[0]
            parts = self._resolve(pattern)
            if parts is None:
                return f"ls: cannot access '{pattern}': No such file or directory"

        # If the path is actually a wildcard pattern targeting current dir
        if any(p in paths[0] for p in ("*", "?")) if paths else False:
            return self._ls_glob(paths[0], show_all)

        node = self._get_node(parts)
        if node is None:
            return f"ls: cannot access '{paths[0]}': No such file or directory"
        if not node.is_dir:
            return paths[0]

        names = []
        for name, child in node.children.items():
            if child.hidden and not show_all:
                continue
            names.append(name)
        if show_all:
            names = [".", ".."] + sorted(names)
        else:
            names = sorted(names)

        if long_fmt:
            lines = []
            for name in names:
                if name in (".", ".."):
                    perms = "drwxr-xr-x"
                    size = 4096
                else:
                    child = node.children[name]
                    perms = "drwxr-xr-x" if child.is_dir else "-rw-r--r--"
                    size = len(child.content) if not child.is_dir else 4096
                lines.append(f"{perms} 1 {self.username} {self.username} {size:>6} Jan  1 12:00 {name}")
            return "\n".join(lines) if lines else ""

        return "  ".join(names)

    def _ls_glob(self, pattern: str, show_all: bool) -> str:
        import fnmatch
        node = self._get_node(self.cwd)
        if node is None:
            return ""
        matches = [
            name for name in node.children
            if fnmatch.fnmatch(name, pattern)
            and (show_all or not node.children[name].hidden)
        ]
        return "  ".join(sorted(matches)) if matches else f"ls: cannot access '{pattern}': No such file or directory"

    def _cmd_mkdir(self, args, stdin):
        parents = False
        paths = []
        for a in args:
            if a in ("-p", "--parents"):
                parents = True
            elif a.startswith("-"):
                continue
            else:
                paths.append(a)
        if not paths:
            return "mkdir: missing operand"

        results = []
        for path in paths:
            if parents:
                parts = self._resolve(path)
                if parts is None:
                    results.append(f"mkdir: cannot create directory '{path}'")
                    continue
                node = self.root
                for i, part in enumerate(parts):
                    if part not in node.children:
                        node.children[part] = SandboxNode(part, is_dir=True)
                    node = node.children[part]
                    if not node.is_dir:
                        results.append(f"mkdir: cannot create directory '{path}': Not a directory")
                        break
            else:
                parts = self._resolve(path)
                if parts is None or not parts:
                    results.append(f"mkdir: cannot create directory '{path}'")
                    continue
                parent_parts, name = parts[:-1], parts[-1]
                parent = self._get_node(parent_parts)
                if parent is None or not parent.is_dir:
                    results.append(f"mkdir: cannot create directory '{path}': No such file or directory")
                    continue
                if name in parent.children:
                    results.append(f"mkdir: cannot create directory '{path}': File exists")
                    continue
                parent.children[name] = SandboxNode(name, is_dir=True)
        return "\n".join(results)

    def _cmd_touch(self, args, stdin):
        paths = [a for a in args if not a.startswith("-")]
        if not paths:
            return "touch: missing file operand"
        results = []
        for path in paths:
            parts = self._resolve(path)
            if parts is None or not parts:
                results.append(f"touch: cannot touch '{path}'")
                continue
            parent_parts, name = parts[:-1], parts[-1]
            parent = self._get_node(parent_parts)
            if parent is None or not parent.is_dir:
                results.append(f"touch: cannot touch '{path}': No such file or directory")
                continue
            if name not in parent.children:
                parent.children[name] = SandboxNode(name, is_dir=False, content="",
                                                      hidden=name.startswith("."))
        return "\n".join(results)

    def _cmd_rm(self, args, stdin):
        recursive = False
        paths = []
        for a in args:
            if a.startswith("-"):
                if "r" in a or "R" in a:
                    recursive = True
            else:
                paths.append(a)
        if not paths:
            return "rm: missing operand"

        results = []
        for path in paths:
            import fnmatch
            if any(c in path for c in "*?"):
                node = self._get_node(self.cwd)
                if node is None:
                    continue
                matches = [n for n in list(node.children) if fnmatch.fnmatch(n, path)]
                for m in matches:
                    target = node.children[m]
                    if target.is_dir and not recursive:
                        results.append(f"rm: cannot remove '{m}': Is a directory")
                    else:
                        del node.children[m]
                continue

            parts = self._resolve(path)
            if parts is None or not parts:
                results.append(f"rm: cannot remove '{path}': No such file or directory")
                continue
            parent_parts, name = parts[:-1], parts[-1]
            parent = self._get_node(parent_parts)
            if parent is None or name not in parent.children:
                results.append(f"rm: cannot remove '{path}': No such file or directory")
                continue
            target = parent.children[name]
            if target.is_dir and not recursive:
                results.append(f"rm: cannot remove '{path}': Is a directory")
                continue
            del parent.children[name]
        return "\n".join(results)

    def _cmd_rmdir(self, args, stdin):
        paths = [a for a in args if not a.startswith("-")]
        if not paths:
            return "rmdir: missing operand"
        results = []
        for path in paths:
            parts = self._resolve(path)
            if parts is None or not parts:
                results.append(f"rmdir: failed to remove '{path}': No such file or directory")
                continue
            parent_parts, name = parts[:-1], parts[-1]
            parent = self._get_node(parent_parts)
            if parent is None or name not in parent.children:
                results.append(f"rmdir: failed to remove '{path}': No such file or directory")
                continue
            target = parent.children[name]
            if not target.is_dir:
                results.append(f"rmdir: failed to remove '{path}': Not a directory")
                continue
            if target.children:
                results.append(f"rmdir: failed to remove '{path}': Directory not empty")
                continue
            del parent.children[name]
        return "\n".join(results)

    def _cmd_find(self, args, stdin):
        # Simplified: find [path] [-name pattern] [-type f|d]
        import fnmatch
        start = "."
        name_pattern = None
        type_filter = None
        i = 0
        positional_seen = False
        while i < len(args):
            a = args[i]
            if a == "-name" and i + 1 < len(args):
                name_pattern = args[i + 1]
                i += 2
                continue
            if a == "-type" and i + 1 < len(args):
                type_filter = args[i + 1]
                i += 2
                continue
            if not a.startswith("-") and not positional_seen:
                start = a
                positional_seen = True
            i += 1

        start_parts = self._resolve(start)
        start_node = self._get_node(start_parts) if start_parts is not None else None
        if start_node is None:
            return f"find: '{start}': No such file or directory"

        results = []

        def walk(node: SandboxNode, path_parts: list[str]):
            display = "/".join(path_parts) if path_parts else "."
            display = "./" + display if display != "." else "."
            matches_name = name_pattern is None or fnmatch.fnmatch(node.name, name_pattern)
            matches_type = (
                type_filter is None
                or (type_filter == "f" and not node.is_dir)
                or (type_filter == "d" and node.is_dir)
            )
            if matches_name and matches_type:
                results.append(display)
            if node.is_dir:
                for child_name, child in sorted(node.children.items()):
                    walk(child, path_parts + [child_name])

        # find always includes the start path itself in real find;
        # mirror that, using the literal start argument as the base label
        base_label = start if start not in (".", "") else "."
        if name_pattern is None or fnmatch.fnmatch(start_node.name or base_label, name_pattern):
            if type_filter is None or (type_filter == "d") == start_node.is_dir:
                results.append(base_label)
        if start_node.is_dir:
            for child_name, child in sorted(start_node.children.items()):
                walk(child, [child_name] if base_label == "." else [base_label, child_name])

        return "\n".join(results) if results else ""

    def _cmd_which(self, args, stdin):
        if not args:
            return "which: missing operand"
        known_commands = {
            "ls", "cd", "pwd", "mkdir", "touch", "rm", "rmdir", "cat", "echo",
            "mv", "cp", "grep", "wc", "head", "tail", "whoami", "find",
            "which", "sed", "awk", "xargs", "tar", "alias", "export", "env",
            "ssh", "ssh-keygen", "rsync", "nano",
        }
        results = []
        for cmd in args:
            if cmd in known_commands:
                results.append(f"/usr/bin/{cmd}")
            else:
                results.append(f"which: no {cmd} in ({self.env.get('PATH', '')})")
        return "\n".join(results)

    def _cmd_sed(self, args, stdin):
        # Simplified: only supports sed 's/pattern/replacement/' [flags] [file]
        if not args:
            return "sed: missing script"
        global_flag = False
        expr = None
        files = []
        for a in args:
            if a.startswith("s/") or a.startswith("s|"):
                expr = a
            elif not a.startswith("-"):
                files.append(a)
        if expr is None:
            return "sed: -e expression #1, char 0: no previous regular expression"

        delim = expr[1]
        parts = expr.split(delim)
        if len(parts) < 3:
            return f"sed: -e expression #1, char {len(expr)}: unterminated `s' command"
        pattern, replacement = parts[1], parts[2]
        flags = parts[3] if len(parts) > 3 else ""
        global_flag = "g" in flags

        def apply_sed(text: str) -> str:
            lines = []
            for line in text.splitlines():
                if global_flag:
                    lines.append(line.replace(pattern, replacement))
                else:
                    lines.append(line.replace(pattern, replacement, 1))
            return "\n".join(lines)

        if files:
            outputs = []
            for path in files:
                parts_p = self._resolve(path)
                node = self._get_node(parts_p) if parts_p is not None else None
                if node is None:
                    outputs.append(f"sed: can't read {path}: No such file or directory")
                    continue
                outputs.append(apply_sed(node.content))
            return "\n".join(outputs)

        if stdin is not None:
            return apply_sed(stdin)
        return ""

    def _cmd_awk(self, args, stdin):
        # Simplified: only supports awk '{print $N}' [file]
        if not args:
            return "awk: missing program"
        program = args[0]
        files = args[1:]

        import re as _re
        m = _re.match(r"^\{?\s*print\s+(\$\d+(?:,\s*\$\d+)*)\s*\}?$", program.strip())
        if not m:
            return f"awk: this sandbox only supports simple '{{print $N}}' column extraction"
        field_nums = [int(tok.strip().lstrip("$")) for tok in m.group(1).split(",")]

        def apply_awk(text: str) -> str:
            out_lines = []
            for line in text.splitlines():
                cols = line.split()
                picked = []
                for n in field_nums:
                    picked.append(cols[n - 1] if 0 < n <= len(cols) else "")
                out_lines.append(" ".join(picked))
            return "\n".join(out_lines)

        if files:
            outputs = []
            for path in files:
                parts_p = self._resolve(path)
                node = self._get_node(parts_p) if parts_p is not None else None
                if node is None:
                    outputs.append(f"awk: can't open file {path}")
                    continue
                outputs.append(apply_awk(node.content))
            return "\n".join(outputs)

        if stdin is not None:
            return apply_awk(stdin)
        return ""

    def _cmd_xargs(self, args, stdin):
        if not args:
            # xargs with no command just echoes its stdin args, like real xargs
            items = (stdin or "").split()
            return " ".join(items)
        sub_cmd, *sub_args = args
        items = (stdin or "").split()
        # Run the sub-command once per item, like real xargs (simplified:
        # no -I{} placeholder support, just appends each item as an arg)
        outputs = []
        for item in items:
            outputs.append(self._dispatch([sub_cmd, *sub_args, item]))
        return "\n".join(o for o in outputs if o)

    def _cmd_tar(self, args, stdin):
        # Simplified, simulated tar - doesn't actually compress, just
        # reports what it "would do" so learners can practice the flags.
        if not args:
            return "tar: missing operand"
        flags = args[0]
        rest = args[1:]
        if "c" in flags:
            archive_name = rest[0] if rest else "archive.tar"
            sources = rest[1:] if len(rest) > 1 else []
            verbose = "v" in flags
            if verbose:
                return "\n".join(sources) if sources else ""
            return ""
        if "x" in flags:
            archive_name = rest[0] if rest else "archive.tar"
            return f"tar: extracted contents of {archive_name} (simulated)"
        if "t" in flags:
            archive_name = rest[0] if rest else "archive.tar"
            return f"tar: would list contents of {archive_name} (simulated)"
        return "tar: this sandbox supports -c (create), -x (extract), and -t (list) with common flags like -z, -v, -f"

    def _cmd_export(self, args, stdin):
        if not args:
            return "\n".join(f"declare -x {k}=\"{v}\"" for k, v in self.env.items())
        for assignment in args:
            if "=" in assignment:
                key, _, value = assignment.partition("=")
                self.env[key] = value
        return ""

    def _cmd_alias(self, args, stdin):
        if not args:
            return "\n".join(f"alias {k}='{v}'" for k, v in self.aliases.items())
        for assignment in args:
            if "=" in assignment:
                key, _, value = assignment.partition("=")
                self.aliases[key] = value.strip("'\"")
                return ""
        return ""

    def _cmd_env(self, args, stdin):
        return "\n".join(f"{k}={v}" for k, v in self.env.items())

    def _cmd_ssh(self, args, stdin):
        if not args:
            return "usage: ssh [user@]hostname"
        target = args[0]
        return (
            f"This sandbox can't make real network connections, but in "
            f"real life this would attempt to open a secure shell session "
            f"to '{target}', prompting for a password or using your SSH "
            f"key if one is set up."
        )

    def _cmd_ssh_keygen(self, args, stdin):
        return (
            "Generating public/private rsa key pair (simulated).\n"
            "Your identification has been saved in ~/.ssh/id_rsa\n"
            "Your public key has been saved in ~/.ssh/id_rsa.pub\n"
            "(This sandbox simulates the output - no real keys were created.)"
        )

    def _cmd_rsync(self, args, stdin):
        sources = [a for a in args if not a.startswith("-")]
        return (
            f"This sandbox can't perform a real file transfer, but in real "
            f"life this would sync {' '.join(sources) if sources else 'the given paths'}, "
            f"copying only what's new or changed."
        )

    def _cmd_nano(self, args, stdin):
        target = args[0] if args else "(new file)"
        return (
            f"This sandbox can't open a real interactive editor for "
            f"'{target}'. On your real system, this would open {target} in "
            f"nano - type to edit, Ctrl+O then Enter to save, Ctrl+X to "
            f"exit."
        )

    def _cmd_cat(self, args, stdin):
        paths = [a for a in args if not a.startswith("-")]
        if not paths:
            return stdin or ""
        outputs = []
        for path in paths:
            parts = self._resolve(path)
            node = self._get_node(parts) if parts is not None else None
            if node is None:
                outputs.append(f"cat: {path}: No such file or directory")
            elif node.is_dir:
                outputs.append(f"cat: {path}: Is a directory")
            else:
                outputs.append(node.content.rstrip("\n"))
        return "\n".join(outputs)

    def _cmd_echo(self, args, stdin):
        # shlex already stripped quotes
        return " ".join(args)

    def _cmd_mv(self, args, stdin):
        paths = [a for a in args if not a.startswith("-")]
        if len(paths) < 2:
            return "mv: missing file operand"
        *sources, dest = paths
        dest_parts = self._resolve(dest)
        dest_node = self._get_node(dest_parts) if dest_parts is not None else None

        results = []
        for src in sources:
            src_parts = self._resolve(src)
            if src_parts is None or not src_parts:
                results.append(f"mv: cannot stat '{src}': No such file or directory")
                continue
            src_parent_parts, src_name = src_parts[:-1], src_parts[-1]
            src_parent = self._get_node(src_parent_parts)
            if src_parent is None or src_name not in src_parent.children:
                results.append(f"mv: cannot stat '{src}': No such file or directory")
                continue
            node = src_parent.children[src_name]

            if dest_node is not None and dest_node.is_dir:
                dest_node.children[src_name] = node
            else:
                if dest_parts is None or not dest_parts:
                    results.append(f"mv: invalid destination '{dest}'")
                    continue
                d_parent_parts, d_name = dest_parts[:-1], dest_parts[-1]
                d_parent = self._get_node(d_parent_parts)
                if d_parent is None:
                    results.append(f"mv: cannot move to '{dest}': No such file or directory")
                    continue
                node.name = d_name
                node.hidden = d_name.startswith(".")
                d_parent.children[d_name] = node
            del src_parent.children[src_name]
        return "\n".join(results)

    def _cmd_cp(self, args, stdin):
        import copy
        paths = [a for a in args if not a.startswith("-")]
        if len(paths) < 2:
            return "cp: missing file operand"
        *sources, dest = paths
        dest_parts = self._resolve(dest)
        dest_node = self._get_node(dest_parts) if dest_parts is not None else None

        results = []
        for src in sources:
            src_parts = self._resolve(src)
            node = self._get_node(src_parts) if src_parts is not None else None
            if node is None:
                results.append(f"cp: cannot stat '{src}': No such file or directory")
                continue
            new_node = copy.deepcopy(node)

            if dest_node is not None and dest_node.is_dir:
                new_node.name = node.name
                dest_node.children[node.name] = new_node
            else:
                if dest_parts is None or not dest_parts:
                    results.append(f"cp: invalid destination '{dest}'")
                    continue
                d_parent_parts, d_name = dest_parts[:-1], dest_parts[-1]
                d_parent = self._get_node(d_parent_parts)
                if d_parent is None:
                    results.append(f"cp: cannot create '{dest}': No such file or directory")
                    continue
                new_node.name = d_name
                new_node.hidden = d_name.startswith(".")
                d_parent.children[d_name] = new_node
        return "\n".join(results)

    def _cmd_grep(self, args, stdin):
        ignore_case = False
        invert = False
        pattern = None
        files = []
        for a in args:
            if a.startswith("-"):
                if "i" in a:
                    ignore_case = True
                if "v" in a:
                    invert = True
            elif pattern is None:
                pattern = a
            else:
                files.append(a)

        if pattern is None:
            return "grep: missing pattern"

        def matches(line: str) -> bool:
            hay, needle = line, pattern
            if ignore_case:
                hay, needle = hay.lower(), needle.lower()
            found = needle in hay
            return (not found) if invert else found

        if files:
            outputs = []
            for path in files:
                parts = self._resolve(path)
                node = self._get_node(parts) if parts is not None else None
                if node is None:
                    outputs.append(f"grep: {path}: No such file or directory")
                    continue
                for line in node.content.splitlines():
                    if matches(line):
                        outputs.append(line)
            return "\n".join(outputs)

        if stdin is not None:
            return "\n".join(l for l in stdin.splitlines() if matches(l))

        return ""

    def _cmd_wc(self, args, stdin):
        lines_only = "-l" in args
        files = [a for a in args if not a.startswith("-")]

        def count(text: str):
            lines = text.splitlines()
            words = text.split()
            chars = len(text)
            return len(lines), len(words), chars

        if files:
            outputs = []
            for path in files:
                parts = self._resolve(path)
                node = self._get_node(parts) if parts is not None else None
                if node is None:
                    outputs.append(f"wc: {path}: No such file or directory")
                    continue
                l, w, c = count(node.content)
                outputs.append(f"{l if lines_only else f'{l:>4} {w:>4} {c:>5}'} {path}")
            return "\n".join(outputs)

        text = stdin or ""
        l, w, c = count(text)
        return str(l) if lines_only else f"{l:>4} {w:>4} {c:>5}"

    def _cmd_head(self, args, stdin):
        n = 10
        files = []
        i = 0
        while i < len(args):
            if args[i] == "-n" and i + 1 < len(args):
                n = int(args[i + 1])
                i += 2
                continue
            if not args[i].startswith("-"):
                files.append(args[i])
            i += 1

        if files:
            outputs = []
            for path in files:
                parts = self._resolve(path)
                node = self._get_node(parts) if parts is not None else None
                if node is None:
                    outputs.append(f"head: cannot open '{path}'")
                    continue
                outputs.append("\n".join(node.content.splitlines()[:n]))
            return "\n".join(outputs)
        if stdin is not None:
            return "\n".join(stdin.splitlines()[:n])
        return ""

    def _cmd_tail(self, args, stdin):
        n = 10
        files = []
        i = 0
        while i < len(args):
            if args[i] == "-n" and i + 1 < len(args):
                n = int(args[i + 1])
                i += 2
                continue
            if args[i] == "-f":
                i += 1
                continue
            if not args[i].startswith("-"):
                files.append(args[i])
            i += 1

        if files:
            outputs = []
            for path in files:
                parts = self._resolve(path)
                node = self._get_node(parts) if parts is not None else None
                if node is None:
                    outputs.append(f"tail: cannot open '{path}'")
                    continue
                outputs.append("\n".join(node.content.splitlines()[-n:]))
            return "\n".join(outputs)
        if stdin is not None:
            return "\n".join(stdin.splitlines()[-n:])
        return ""

    # -- read-only "system info" commands that return realistic fake data --

    def _cmd_lsb_release(self, args, stdin):
        return (
            "Distributor ID:\tUbuntu\n"
            "Description:\tUbuntu 24.04.2 LTS\n"
            "Release:\t24.04\n"
            "Codename:\tnoble"
        )

    def _cmd_uname(self, args, stdin):
        if "-r" in args:
            return "6.8.0-45-generic"
        if "-a" in args:
            return "Linux grix-sandbox 6.8.0-45-generic #45-Ubuntu SMP x86_64 GNU/Linux"
        return "Linux"

    def _cmd_df(self, args, stdin):
        return (
            "Filesystem      Size  Used Avail Use% Mounted on\n"
            "/dev/sda1       100G   42G   53G  45% /\n"
            "/dev/sda2       500G  120G  355G  26% /home"
        )

    def _cmd_du(self, args, stdin):
        paths = [a for a in args if not a.startswith("-")]
        target = paths[0] if paths else "."
        return f"24K\t{target}"

    def _cmd_ps(self, args, stdin):
        return (
            "USER       PID %CPU %MEM COMMAND\n"
            "user         1  0.0  0.1 /sbin/init\n"
            "user       842  0.2  1.4 /usr/bin/gnome-shell\n"
            "user      1190  0.0  0.3 NetworkManager\n"
            "user      2031  1.2  2.8 firefox"
        )

    def _cmd_systemctl(self, args, stdin):
        if not args:
            return "systemctl: missing command"
        sub = args[0]
        if sub == "--failed":
            return "0 loaded units listed."
        if sub == "status" and len(args) > 1:
            svc = args[1]
            return (
                f"\u25cf {svc} - {svc.replace('.service', '')} service\n"
                f"     Loaded: loaded\n"
                f"     Active: active (running)\n"
                f"   Main PID: 1190 ({svc.split('.')[0]})"
            )
        return ""

    def _cmd_journalctl(self, args, stdin):
        if "--disk-usage" in args:
            return "Archived and active journals take up 412.0M in the file system."
        return (
            "-- Journal begins at Mon 2026-06-01 --\n"
            "Jun 13 09:00:01 grix-sandbox systemd[1]: Started Daily apt download activities.\n"
            "Jun 13 09:00:02 grix-sandbox systemd[1]: Finished Daily apt download activities."
        )

    def _cmd_lspci(self, args, stdin):
        return (
            "00:02.0 VGA compatible controller: Intel Corporation UHD Graphics\n"
            "02:00.0 Network controller: Intel Corporation Wi-Fi 6 AX200"
        )

    def _cmd_ip(self, args, stdin):
        if args and args[0] == "a":
            return (
                "1: lo: <LOOPBACK,UP> mtu 65536\n"
                "    inet 127.0.0.1/8 scope host lo\n"
                "2: wlan0: <BROADCAST,MULTICAST,UP> mtu 1500\n"
                "    inet 192.168.1.42/24 scope global wlan0"
            )
        return "Usage: ip a"

    # -- internal helper: write to a simulated file --

    def _write_file(self, path: str, content: str, append: bool) -> str:
        parts = self._resolve(path)
        if parts is None or not parts:
            return f"bash: {path}: No such file or directory"
        parent_parts, name = parts[:-1], parts[-1]
        parent = self._get_node(parent_parts)
        if parent is None or not parent.is_dir:
            return f"bash: {path}: No such file or directory"
        if name in parent.children and parent.children[name].is_dir:
            return f"bash: {path}: Is a directory"

        node = parent.children.get(name)
        if node is None:
            node = SandboxNode(name, is_dir=False, content="", hidden=name.startswith("."))
            parent.children[name] = node

        new_text = content if content.endswith("\n") or content == "" else content + "\n"
        if append:
            node.content += new_text
        else:
            node.content = new_text
        return ""
