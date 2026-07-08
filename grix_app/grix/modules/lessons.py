"""
Grix Linux Academy - Lesson Content
=====================================

Lessons are organized into tracks (Beginner, Intermediate) made of
individual lessons. Each lesson has:
  - an id, title, and short description
  - a list of "blocks" which are rendered in order:
      ("text", markdown-ish string)
      ("command", command-string, explanation-string)
      ("quiz", question, [options], correct-index, explanation)
      ("practice", prompt, expected-command-or-list, hint)

The "practice" blocks are evaluated against the safe sandbox
terminal in modules/sandbox.py, which simulates a tiny filesystem
so users can practice without touching their real system.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Union


@dataclass
class Lesson:
    id: str
    title: str
    summary: str
    blocks: list[tuple] = field(default_factory=list)


@dataclass
class Track:
    id: str
    title: str
    description: str
    lessons: list[Lesson] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Beginner Track
# ---------------------------------------------------------------------------

beginner_lessons = [
    Lesson(
        id="b1_what_is_linux",
        title="1. What Is Linux?",
        summary="Understand what makes up a Linux system - the distro, the kernel, and the desktop.",
        blocks=[
            ("text",
             "Welcome! Before touching the terminal, let's understand what "
             "you're actually working with.\n\n"
             "A Linux system is made of layers:\n\n"
             "- **Distribution (distro)** - the overall Linux version, like "
             "Ubuntu, Debian, or Fedora. It bundles everything else together.\n"
             "- **Kernel** - the core program that talks directly to your "
             "hardware (CPU, memory, disks, network cards).\n"
             "- **Desktop environment** - the graphical interface you see "
             "and click on, like GNOME, KDE Plasma, or XFCE.\n\n"
             "Windows bundles all of this into one product. On Linux, these "
             "pieces are more separate - which is part of why Linux is so "
             "flexible."),
            ("command", "lsb_release -a",
             "This prints information about your distribution: its name, "
             "version, and codename. 'lsb' stands for Linux Standard Base."),
            ("command", "uname -r",
             "This prints your kernel version. The kernel is updated "
             "separately from the rest of your system."),
            ("quiz",
             "Which part of a Linux system talks directly to your hardware?",
             ["The desktop environment", "The kernel", "The distribution name", "The terminal"],
             1,
             "The kernel is the core that communicates with your CPU, "
             "memory, and devices. The desktop environment sits on top of "
             "it and is what you actually see and click on."),
        ],
    ),
    Lesson(
        id="b2_opening_terminal",
        title="2. Opening and Using the Terminal",
        summary="Learn what the terminal is, how to open it, and what the prompt means.",
        blocks=[
            ("text",
             "The terminal (also called the shell, console, or command "
             "line) is a text-based way to control your computer. It can "
             "look intimidating, but it's just a window where you type "
             "instructions and read responses.\n\n"
             "On most Linux desktops you can open a terminal with the "
             "keyboard shortcut **Ctrl+Alt+T**, or by searching for "
             "'Terminal' in your applications menu.\n\n"
             "When you open it, you'll see something like:\n\n"
             "`user@computer:~$`\n\n"
             "This is called the **prompt**. It tells you:\n"
             "- `user` - your username\n"
             "- `computer` - your computer's name\n"
             "- `~` - your current location (more on this soon)\n"
             "- `$` - means you're a regular user (a `#` would mean "
             "administrator/root)\n\n"
             "After the prompt, you type a command and press **Enter** to "
             "run it."),
            ("command", "whoami",
             "Prints your username. Useful for confirming who you're logged "
             "in as, especially after switching users."),
            ("text",
             "**A note on case:** Linux is case-sensitive. `PWD` and `pwd` "
             "are different commands - only one of them works! Always type "
             "commands exactly as shown."),
            ("text",
             "**Two habits that will save you enormous amounts of time:**\n\n"
             "**Tab completion** - start typing a command or filename and "
             "press **Tab**. The shell will either complete it automatically "
             "or, if there are multiple matches, show you the options when "
             "you press Tab twice. This saves typing and avoids typos in "
             "long filenames - use it constantly.\n\n"
             "**Command history** - press the **Up arrow** to bring back "
             "your previous command, and keep pressing it to go further "
             "back. **Down arrow** moves forward again. This means you "
             "rarely need to retype a command you just ran - just recall "
             "it and edit it if needed. You can also press **Ctrl+R** to "
             "search backward through your history by typing part of a "
             "command you remember running."),
            ("quiz",
             "You want to re-run a command you typed two commands ago, with one small change. What's the fastest way?",
             ["Retype the whole command from scratch", "Press the Up arrow twice, then edit it", "Close and reopen the terminal", "There is no way to do this"],
             1,
             "Pressing Up cycles backward through your command history. "
             "Once it's showing, use the arrow keys to move the cursor and "
             "edit just the part you need to change, then press Enter."),
            ("quiz",
             "In the prompt 'user@computer:~$', what does the '~' represent?",
             ["The computer's name", "An error", "Your current location (home directory)", "The root account"],
             2,
             "The tilde (~) is shorthand for your home directory - your "
             "personal folder, usually /home/yourname."),
        ],
    ),
    Lesson(
        id="b3_where_am_i",
        title="3. Finding Your Way: pwd and the Filesystem",
        summary="Learn about the working directory and how Linux organizes files.",
        blocks=[
            ("text",
             "Every terminal session has a **working directory** - the "
             "folder it currently 'is in'. Any file operations you run will "
             "happen relative to this folder unless you specify otherwise.\n\n"
             "The command `pwd` (print working directory) tells you exactly "
             "where you are."),
            ("command", "pwd",
             "Prints the full path of your current location, like "
             "/home/yourname."),
            ("text",
             "Unlike Windows, which splits storage into drives like C: and "
             "D:, Linux has a single unified filesystem starting at `/` - "
             "called the **root directory** (not to be confused with the "
             "root *user*, which we'll cover later).\n\n"
             "Everything branches out from `/`:\n\n"
             "```\n"
             "/\n"
             "├── home    Your personal files live here\n"
             "├── etc     System configuration files\n"
             "├── var     Logs and changing data\n"
             "├── usr     Installed programs\n"
             "└── tmp     Temporary files, cleared on reboot\n"
             "```"),
            ("practice",
             "Try it in the sandbox: print your current working directory.",
             "pwd",
             "Just type 'pwd' and press Enter."),
        ],
    ),
    Lesson(
        id="b4_moving_around",
        title="4. Moving Around with cd",
        summary="Practice changing directories using absolute and relative paths.",
        blocks=[
            ("text",
             "The `cd` (change directory) command moves your working "
             "directory.\n\n"
             "- `cd /` moves to the root directory.\n"
             "- `cd foldername` moves into a folder inside your current "
             "location (a **relative path**).\n"
             "- `cd /full/path/here` jumps straight to a location no matter "
             "where you are (an **absolute path** - it always starts with "
             "`/`).\n"
             "- `cd ..` moves up one level to the parent folder.\n"
             "- `cd` with nothing after it takes you straight back to your "
             "home directory.\n"
             "- `cd ~` also goes to your home directory - `~` is shorthand "
             "for it."),
            ("practice",
             "Move into the 'Documents' folder, then check where you are.",
             ["cd Documents", "pwd"],
             "First type 'cd Documents', press Enter, then type 'pwd'."),
            ("practice",
             "Now go back up to the parent directory.",
             "cd ..",
             "Two dots represent the parent folder. Don't forget the space "
             "between 'cd' and '..'."),
            ("quiz",
             "Which of these is an absolute path?",
             ["Documents", "../Pictures", "/home/user/Documents", "."],
             2,
             "An absolute path always starts with '/', meaning 'start from "
             "the root directory and follow this route'. The others are "
             "relative to wherever you currently are."),
        ],
    ),
    Lesson(
        id="b5_listing_files",
        title="5. Looking Around with ls",
        summary="List files and folders, and learn useful ls options.",
        blocks=[
            ("text",
             "The `ls` (list) command shows the contents of a directory.\n\n"
             "On its own, `ls` lists the current directory. You can also "
             "give it a path to list somewhere else: `ls /etc`.\n\n"
             "Options (also called switches or flags) change how it "
             "behaves:\n\n"
             "- `ls -a` shows **all** files, including hidden ones (files "
             "starting with a dot, like `.bashrc`)\n"
             "- `ls -l` shows a detailed **long** listing with "
             "permissions, owner, size, and date\n"
             "- `ls -la` combines both\n\n"
             "Hidden files aren't secret - they're just kept out of the way "
             "because they're usually configuration files you rarely need "
             "to touch."),
            ("practice",
             "List the contents of the current directory.",
             "ls",
             "Just type 'ls' and press Enter."),
            ("practice",
             "Now list everything, including hidden files.",
             "ls -a",
             "Add the -a option after ls."),
            ("quiz",
             "What does a filename starting with a dot (like .config) mean?",
             ["It's a system file you must never touch", "It's corrupted", "It's hidden from normal directory listings", "It's a temporary file"],
             2,
             "A leading dot simply hides the file from a normal 'ls'. "
             "These are usually configuration files for apps - perfectly "
             "normal, just tucked out of the way."),
        ],
    ),
    Lesson(
        id="b6_files_and_folders",
        title="6. Creating and Removing Files & Folders",
        summary="Use mkdir, touch, rm, and rmdir safely.",
        blocks=[
            ("text",
             "Now let's create things:\n\n"
             "- `mkdir name` makes a new folder ('make directory')\n"
             "- `mkdir -p path/to/nested/folder` creates nested folders in "
             "one go, including any missing parent folders\n"
             "- `touch filename` creates an empty file (or updates its "
             "timestamp if it already exists)\n\n"
             "And removing things:\n\n"
             "- `rmdir name` removes an **empty** folder only - a small "
             "safety net\n"
             "- `rm filename` removes a file\n"
             "- `rm -r foldername` removes a folder **and everything "
             "inside it** - use with care!\n\n"
             "⚠️ **Important:** Unlike a graphical file manager, `rm` does "
             "not move things to a Trash bin. Deleted files are gone "
             "immediately and permanently. Always double-check what you're "
             "deleting, especially when using wildcards like `*`."),
            ("practice",
             "Create a new folder called 'practice'.",
             "mkdir practice",
             "Type 'mkdir practice' and press Enter."),
            ("practice",
             "Move into it, then create an empty file called 'notes.txt'.",
             ["cd practice", "touch notes.txt"],
             "First 'cd practice', then 'touch notes.txt'."),
            ("practice",
             "List the folder contents to confirm the file was created.",
             "ls",
             "Just 'ls' on its own."),
            ("text",
             "`touch` creates an *empty* file - useful, but eventually "
             "you'll want to actually type something into a file without "
             "leaving the terminal (for example, editing a configuration "
             "file over SSH, where there's no graphical text editor "
             "available at all).\n\n"
             "**`nano`** is a simple, beginner-friendly terminal text "
             "editor installed by default on almost every Linux system. "
             "Unlike some other terminal editors, it's **modeless** - "
             "you just start typing immediately, no special mode to enter "
             "first.\n\n"
             "Open a file with `nano filename`. The bottom of the screen "
             "shows the available shortcuts (the `^` symbol means "
             "**Ctrl**):\n\n"
             "- `Ctrl+O` then **Enter** - save the file (\"Write Out\")\n"
             "- `Ctrl+X` - exit nano (it'll ask to save first if you have "
             "unsaved changes)\n"
             "- `Ctrl+K` - cut the current line\n"
             "- `Ctrl+U` - paste it back\n\n"
             "If you ever open a file by mistake and just want out without "
             "changing anything: `Ctrl+X`, then answer **N** (no) when "
             "asked to save.\n\n"
             "💡 You may also see **vim** or **emacs** mentioned online - "
             "both are far more powerful, but have a steeper learning "
             "curve (vim, in particular, has separate 'modes' for typing "
             "vs. issuing commands, which trips up a lot of beginners). "
             "`nano` is the safer place to start."),
            ("quiz",
             "You opened a config file in nano just to look at it, and want to leave WITHOUT saving any changes. What do you press?",
             ["Ctrl+O then Enter", "Ctrl+X, then answer No to saving", "Ctrl+C", "Just close the terminal window"],
             1,
             "Ctrl+X exits nano. If there are unsaved changes it asks "
             "whether to save them first - answering No discards them and "
             "leaves the file untouched."),
            ("quiz",
             "Which command would permanently delete a folder and everything inside it?",
             ["rmdir myfolder", "rm myfolder", "rm -r myfolder", "del myfolder"],
             2,
             "'rm -r' removes a folder recursively, deleting its contents "
             "too. Plain 'rm' refuses to delete folders, and 'rmdir' only "
             "works on empty ones - both are safety nets."),
        ],
    ),
    Lesson(
        id="b7_viewing_files",
        title="7. Viewing File Contents",
        summary="Read files with cat, less, and head/tail.",
        blocks=[
            ("text",
             "To look inside a text file without opening an editor:\n\n"
             "- `cat filename` prints the whole file to the screen. Good "
             "for short files.\n"
             "- `less filename` opens the file in a scrollable viewer. Use "
             "arrow keys, Page Up/Down, and press `q` to quit. Better for "
             "long files.\n"
             "- `head filename` shows the first 10 lines.\n"
             "- `tail filename` shows the last 10 lines - handy for "
             "checking the end of a log file.\n"
             "- `tail -f filename` 'follows' a file, showing new lines as "
             "they're added in real time. Press Ctrl+C to stop."),
            ("practice",
             "View the contents of notes.txt using cat.",
             "cat notes.txt",
             "Type 'cat notes.txt'. It will be empty since we just created "
             "it, but the command still runs successfully."),
            ("text",
             "**cat** is short for 'concatenate' - it can also join "
             "multiple files together: `cat file1.txt file2.txt` prints "
             "both, one after another."),
        ],
    ),
    Lesson(
        id="b8_redirection",
        title="8. Redirecting Output: > and >>",
        summary="Send command output into files instead of the screen.",
        blocks=[
            ("text",
             "Normally, a command's output appears on screen. The `>` "
             "symbol **redirects** that output into a file instead.\n\n"
             "- `command > file.txt` writes the output to file.txt, "
             "**replacing** anything already in it\n"
             "- `command >> file.txt` **appends** the output to the end of "
             "file.txt instead of replacing it\n\n"
             "Combined with `echo` (which just prints back whatever you "
             "give it), this is a quick way to create text files:\n\n"
             "`echo \"Hello, Linux!\" > greeting.txt`\n\n"
             "⚠️ Be careful with `>` - if the file already exists, its "
             "previous content is gone immediately. If you're not sure, use "
             "`>>` to append instead."),
            ("practice",
             "Create a file called greeting.txt containing the text 'Hello, Linux!'",
             'echo "Hello, Linux!" > greeting.txt',
             "Use echo with the text in quotes, then > and the filename."),
            ("practice",
             "View the file to confirm it worked.",
             "cat greeting.txt",
             "cat followed by the filename."),
            ("practice",
             "Append a second line to the same file.",
             'echo "Second line" >> greeting.txt',
             "Use >> this time so you don't erase the first line."),
            ("quiz",
             "What's the difference between > and >>?",
             ["No difference", "> appends, >> replaces", "> replaces the file's contents, >> adds to the end", ">> only works with echo"],
             2,
             "A single > overwrites the file completely. Double >> adds "
             "new content to the end, keeping what was already there."),
        ],
    ),
    Lesson(
        id="b9_moving_copying",
        title="9. Moving, Copying, and Renaming",
        summary="Use mv and cp to organize files.",
        blocks=[
            ("text",
             "- `cp source destination` copies a file. The original stays "
             "put.\n"
             "- `mv source destination` moves a file. The original is "
             "gone from its old location.\n"
             "- Renaming is just a special case of moving: `mv oldname.txt "
             "newname.txt` renames a file in place.\n\n"
             "Both commands can also work with folders, and `mv` can move "
             "multiple files at once if the last argument is a folder:\n\n"
             "`mv file1.txt file2.txt myfolder/`\n\n"
             "moves both files into myfolder."),
            ("practice",
             "Make a copy of greeting.txt called greeting_backup.txt.",
             "cp greeting.txt greeting_backup.txt",
             "cp, then the original name, then the new name."),
            ("practice",
             "Rename greeting_backup.txt to old_greeting.txt.",
             "mv greeting_backup.txt old_greeting.txt",
             "mv works for renaming too - just give it the old and new "
             "names."),
            ("practice",
             "List the folder to see both files.",
             "ls",
             "Just 'ls'."),
        ],
    ),
    Lesson(
        id="b10_wildcards",
        title="10. Wildcards: * and ?",
        summary="Match multiple files at once with wildcard patterns.",
        blocks=[
            ("text",
             "Wildcards let you refer to multiple files that match a "
             "pattern, without typing each name:\n\n"
             "- `*` matches **zero or more** of any characters\n"
             "- `?` matches exactly **one** character\n\n"
             "Examples:\n\n"
             "- `*.txt` matches every file ending in .txt\n"
             "- `notes_?.txt` matches notes_1.txt, notes_a.txt, but not "
             "notes_10.txt (two characters)\n"
             "- `*` on its own matches everything in the current folder\n\n"
             "⚠️ Wildcards are powerful but dangerous with `rm`. A command "
             "like `rm *` deletes **everything** in the current folder. "
             "Always double check with `ls` first to see what a wildcard "
             "would match."),
            ("practice",
             "Use a wildcard with ls to list every .txt file in this folder.",
             "ls *.txt",
             "ls followed by *.txt"),
            ("quiz",
             "Before running 'rm *.log' to clean up log files, what's the safest first step?",
             ["Just run it, log files are always safe to delete", "Run 'ls *.log' first to see exactly what would be deleted", "Run it as root to be sure", "Rename the files first"],
             1,
             "Running 'ls' with the same pattern shows you exactly what "
             "'rm' would match, before anything is deleted. This is a "
             "simple habit that prevents most wildcard accidents."),
        ],
    ),
    Lesson(
        id="b11_superuser",
        title="11. sudo and the Superuser",
        summary="Understand administrator privileges and why sudo is safer than root login.",
        blocks=[
            ("text",
             "Some actions - installing software, editing system files, "
             "managing services - need administrator (or **superuser**) "
             "privileges.\n\n"
             "On older systems, admins would log in directly as a user "
             "called `root`, who can do *anything* - including breaking "
             "the system with one typo. Modern Ubuntu disables this "
             "account by default.\n\n"
             "Instead, Ubuntu uses **sudo** ('switch user and do'). You "
             "prefix a single command with `sudo`, type your own password "
             "when asked, and that one command runs with admin rights. "
             "Everything else you do stays as your normal user.\n\n"
             "`sudo apt update`\n\n"
             "**Before running any command with sudo, make sure you "
             "understand what it does.** sudo gives that command full "
             "power over your system - there's no safety net once it "
             "runs."),
            ("text",
             "🚫 **Things to avoid:**\n\n"
             "- Never run `sudo su` or try to 'become root' permanently "
             "unless you have a specific, well-understood reason. Every "
             "command afterward runs as root, with no warnings.\n"
             "- Never run `chmod -R 777 /` or similar 'fix everything' "
             "permission commands you find online. They remove security "
             "protections system-wide.\n"
             "- Be suspicious of any instructions that ask you to enable "
             "the root account or download-and-run scripts with `curl | "
             "sudo bash`."),
            ("quiz",
             "What does 'sudo' let you do?",
             ["Permanently become the root user", "Run one command with administrator privileges, after confirming your password", "Bypass your password entirely", "Install software without an internet connection"],
             1,
             "sudo elevates just the single command that follows it. You "
             "stay logged in as your normal user the rest of the time, "
             "which limits the damage a mistake can cause."),
        ],
    ),
    Lesson(
        id="b12_installing_software",
        title="12. Installing Software with APT",
        summary="Learn how Ubuntu's package manager works.",
        blocks=[
            ("text",
             "Ubuntu installs most software through **APT** (Advanced "
             "Package Tool), which downloads programs from trusted "
             "repositories - servers maintained by Ubuntu and its "
             "partners.\n\n"
             "Common commands:\n\n"
             "- `sudo apt update` - refreshes the list of available "
             "software and versions (doesn't install anything)\n"
             "- `sudo apt upgrade` - installs newer versions of software "
             "you already have\n"
             "- `sudo apt install packagename` - installs a new program\n"
             "- `sudo apt remove packagename` - uninstalls a program\n"
             "- `apt search keyword` - searches for available software\n\n"
             "A typical workflow is to run `sudo apt update` first, then "
             "`sudo apt upgrade` to apply any updates."),
            ("text",
             "**A word of caution:** instructions online sometimes ask you "
             "to install software a different way - using `curl`, `wget`, "
             "`pip`, `npm`, or a 'Personal Package Archive' (PPA). These "
             "aren't necessarily unsafe, but they come from outside Ubuntu's "
             "curated repositories, so it's worth checking that the source "
             "is the official project before proceeding."),
            ("quiz",
             "What does 'sudo apt update' actually do?",
             ["Installs all available updates immediately", "Refreshes the list of available software versions, without installing anything", "Removes old software", "Restarts your computer"],
             1,
             "'apt update' only refreshes APT's local index of what's "
             "available - think of it as updating a catalog. 'apt upgrade' "
             "is the separate step that actually installs newer versions."),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Intermediate Track
# ---------------------------------------------------------------------------

intermediate_lessons = [
    Lesson(
        id="i1_pipes",
        title="1. Pipes: Chaining Commands Together",
        summary="Connect commands so one's output becomes another's input.",
        blocks=[
            ("text",
             "Each command produces output (called **standard output**, "
             "or stdout) and can accept input (**standard input**, or "
             "stdin). The pipe character `|` connects the output of one "
             "command directly into the input of the next, without "
             "creating any temporary files.\n\n"
             "`ls | wc -l`\n\n"
             "This lists files, then pipes that list into `wc -l`, which "
             "counts the lines - giving you a quick file count.\n\n"
             "You can chain as many commands as you like:\n\n"
             "`cat file.txt | sort | uniq | wc -l`\n\n"
             "reads a file, sorts its lines, removes adjacent duplicates, "
             "and counts what's left."),
            ("practice",
             "Count how many items are in the current directory.",
             "ls | wc -l",
             "ls, then a pipe, then 'wc -l'."),
            ("text",
             "If a chain of commands feels overwhelming, break it down "
             "from left to right - run just the first command, see its "
             "output, then add the next piece one at a time."),
        ],
    ),
    Lesson(
        id="i2_grep",
        title="2. Searching Text with grep",
        summary="Find lines matching a pattern across files and command output.",
        blocks=[
            ("text",
             "`grep` searches for text and prints matching lines. It's one "
             "of the most useful tools on the command line.\n\n"
             "- `grep \"word\" file.txt` - find lines containing 'word' in "
             "file.txt\n"
             "- `grep -i \"word\" file.txt` - case-insensitive search\n"
             "- `grep -r \"word\" folder/` - search recursively through a "
             "whole folder\n"
             "- `grep -v \"word\" file.txt` - show lines that **don't** "
             "match\n\n"
             "It works great with pipes too:\n\n"
             "`systemctl --failed | grep service`\n\n"
             "or checking running processes:\n\n"
             "`ps aux | grep firefox`"),
            ("practice",
             "Search greeting.txt for the word 'Second'.",
             'grep "Second" greeting.txt',
             "grep, the word in quotes, then the filename."),
            ("quiz",
             "What does 'grep -i \"error\" log.txt' do?",
             ["Removes the word 'error' from log.txt", "Finds lines containing 'error' or 'Error' or 'ERROR', regardless of case", "Counts how many times 'error' appears", "Deletes log.txt if it contains errors"],
             1,
             "The -i flag makes the search case-insensitive, so it matches "
             "'error', 'Error', 'ERROR', and any other capitalization."),
        ],
    ),
    Lesson(
        id="i3_permissions",
        title="3. File Permissions",
        summary="Understand the rwx permission system and how to read it.",
        blocks=[
            ("text",
             "Running `ls -l` shows a permissions string like this:\n\n"
             "`-rw-r--r-- 1 user user 220 Jan  1 12:00 file.txt`\n\n"
             "The first 10 characters describe the type and permissions:\n\n"
             "- Position 1: `-` for a file, `d` for a directory\n"
             "- Positions 2-4: permissions for the **owner** (rwx = read, "
             "write, execute)\n"
             "- Positions 5-7: permissions for the **group**\n"
             "- Positions 8-10: permissions for **everyone else**\n\n"
             "So `-rw-r--r--` means: a regular file; the owner can read and "
             "write; the group can only read; everyone else can only "
             "read.\n\n"
             "Permissions are changed with `chmod` and ownership with "
             "`chown`. For example:\n\n"
             "`chmod +x script.sh` - makes a file executable\n\n"
             "`sudo chown user:user file.txt` - changes who owns a file"),
            ("practice",
             "View detailed permissions for everything in the current folder.",
             "ls -l",
             "ls with the -l (lowercase L) option."),
            ("text",
             "⚠️ Avoid 'permission fix' commands you find online that use "
             "`chmod -R 777`. The `777` means 'everyone can read, write, "
             "AND execute' - applied recursively, this removes important "
             "protections and can make a system insecure. If something has "
             "a genuine permission problem, it's almost always better to "
             "fix the *ownership* (`chown`) rather than throw open every "
             "permission."),
        ],
    ),
    Lesson(
        id="i4_processes",
        title="4. Processes: ps, top, and kill",
        summary="See what's running on your system and manage it.",
        blocks=[
            ("text",
             "Every running program is a **process**, identified by a "
             "Process ID (PID).\n\n"
             "- `ps aux` lists all running processes with details: who "
             "started them, how much CPU/memory they're using, and their "
             "PID\n"
             "- `top` shows a live, constantly updating view - press `q` to "
             "quit\n"
             "- `kill PID` asks a process to stop gracefully\n"
             "- `kill -9 PID` forces it to stop immediately - use as a "
             "last resort, since the program has no chance to save data or "
             "clean up\n\n"
             "A common pattern is finding a process with `ps aux | grep "
             "name` to get its PID, then using that PID with `kill`."),
            ("practice",
             "List all running processes (output will be long - that's normal).",
             "ps aux",
             "ps with the 'aux' options (no dash needed for this "
             "combination)."),
            ("quiz",
             "What's the difference between 'kill PID' and 'kill -9 PID'?",
             ["No difference", "kill -9 is gentler", "'kill' asks the program to shut down cleanly; 'kill -9' forces an immediate stop with no cleanup", "'kill' only works on your own programs"],
             2,
             "Plain 'kill' sends a polite request the program can respond "
             "to (saving work, closing files). 'kill -9' is an immediate, "
             "forceful termination - useful when a program is completely "
             "frozen, but it skips any cleanup."),
        ],
    ),
    Lesson(
        id="i5_systemd",
        title="5. systemd Services",
        summary="Manage background services with systemctl.",
        blocks=[
            ("text",
             "Most modern Linux distributions use **systemd** to manage "
             "background services (often called **daemons**) - programs "
             "like networking, printing, or Bluetooth that run without a "
             "window.\n\n"
             "Key commands:\n\n"
             "- `systemctl status servicename` - check if a service is "
             "running and see recent activity\n"
             "- `systemctl --failed` - list any services that failed to "
             "start\n"
             "- `sudo systemctl restart servicename` - restart a service\n"
             "- `sudo systemctl enable servicename` - make a service start "
             "automatically at boot\n"
             "- `sudo systemctl disable servicename` - stop it from "
             "starting automatically\n"
             "- `journalctl -u servicename` - view that service's logs\n\n"
             "Service names typically end in `.service`, like "
             "`NetworkManager.service` or `cups.service` (the printing "
             "system)."),
            ("practice",
             "Check the status of the (simulated) NetworkManager service.",
             "systemctl status NetworkManager",
             "systemctl status, then the service name."),
            ("text",
             "This is exactly what Grix's System Sentinel does behind the "
             "scenes when it reports a failed service - it's running "
             "`systemctl --failed`, then offering to restart whatever it "
             "finds, with your confirmation."),
        ],
    ),
    Lesson(
        id="i6_logs",
        title="6. Reading Logs with journalctl",
        summary="Investigate problems by reading the system journal.",
        blocks=[
            ("text",
             "`journalctl` shows the **systemd journal** - a unified log "
             "of messages from the kernel, services, and applications.\n\n"
             "Useful forms:\n\n"
             "- `journalctl` - view the entire journal (opens in `less` - "
             "press `q` to quit)\n"
             "- `journalctl -u servicename` - logs for one specific "
             "service\n"
             "- `journalctl -b` - logs from the current boot only\n"
             "- `journalctl -f` - 'follow' new log entries live, like "
             "`tail -f`\n"
             "- `journalctl --disk-usage` - see how much disk space logs "
             "are using\n"
             "- `journalctl -p err` - show only error-level messages and "
             "above\n\n"
             "Logs can take up significant disk space over time. Trimming "
             "old entries with `journalctl --vacuum-time=14d` is safe and "
             "is one of Grix's 'safe fix' suggestions."),
            ("practice",
             "Check how much disk space the journal is using.",
             "journalctl --disk-usage",
             "journalctl with the --disk-usage option."),
        ],
    ),
    Lesson(
        id="i7_disk_usage",
        title="7. Disk Usage: df and du",
        summary="Find out what's using your disk space.",
        blocks=[
            ("text",
             "Two commands, easy to mix up:\n\n"
             "- `df -h` ('disk free', human-readable) shows space used and "
             "available on each mounted filesystem/partition - the big "
             "picture\n"
             "- `du -sh foldername` ('disk usage', summarized, "
             "human-readable) shows the total size of a specific folder\n\n"
             "To find what's taking up space inside a folder, you can "
             "combine `du` with sorting:\n\n"
             "`du -h --max-depth=1 /home/user | sort -rh`\n\n"
             "This lists each subfolder's size, sorted largest first - a "
             "great way to hunt down what's eating your disk space."),
            ("practice",
             "Check overall disk usage for all mounted filesystems.",
             "df -h",
             "df with the -h option."),
            ("practice",
             "Check the size of the current directory.",
             "du -sh .",
             "du -sh, then a dot to mean 'this folder'."),
        ],
    ),
    Lesson(
        id="i8_environment",
        title="8. Environment Variables and PATH",
        summary="Understand how the shell finds commands and stores settings.",
        blocks=[
            ("text",
             "**Environment variables** are named values the shell and "
             "programs can read. View them with `env` or print one "
             "specific value with `echo $VARNAME`.\n\n"
             "One of the most important is **PATH** - a list of folders "
             "the shell searches through when you type a command name. "
             "When you run `ls`, the shell searches each folder in PATH "
             "until it finds a program called `ls`.\n\n"
             "`echo $PATH`\n\n"
             "might show something like:\n\n"
             "`/usr/local/bin:/usr/bin:/bin:/usr/local/games`\n\n"
             "Folders are separated by colons. If you install a program and "
             "the shell says 'command not found', it's often because the "
             "program's folder isn't in PATH."),
            ("practice",
             "Print your PATH variable.",
             "echo $PATH",
             "echo, then a dollar sign and PATH (all uppercase)."),
            ("text",
             "Other commonly-used variables: `$HOME` (your home directory), "
             "`$USER` (your username), and `$SHELL` (which shell program "
             "you're using, usually `/bin/bash`)."),
        ],
    ),
    Lesson(
        id="i9_scripts",
        title="9. Your First Shell Script",
        summary="Combine commands into a reusable script file.",
        blocks=[
            ("text",
             "A **shell script** is just a text file containing commands, "
             "run in order. Scripts let you save and re-run sequences of "
             "commands instead of retyping them.\n\n"
             "A simple script looks like:\n\n"
             "```\n"
             "#!/bin/bash\n"
             "echo \"Starting cleanup...\"\n"
             "rm -f *.tmp\n"
             "echo \"Done!\"\n"
             "```\n\n"
             "The first line, `#!/bin/bash`, is called a **shebang** - it "
             "tells the system which program should run this script.\n\n"
             "To run a script:\n\n"
             "1. Save it as a file, e.g. `cleanup.sh`\n"
             "2. Make it executable: `chmod +x cleanup.sh`\n"
             "3. Run it: `./cleanup.sh` (the `./` means 'in this folder')\n\n"
             "⚠️ Only make a script executable and run it if you've read "
             "and understood what it does. A script can run any command "
             "your account has permission for."),
            ("quiz",
             "Why does './cleanup.sh' include './' at the start?",
             ["It's required by all Linux commands", "It tells the shell to look for the script in the current folder, since the current folder usually isn't in PATH", "It runs the script as root", "It's optional and does nothing"],
             1,
             "For security, the current directory generally isn't searched "
             "automatically when you type a command. './' explicitly says "
             "'look here', confirming you mean to run this specific file."),
        ],
    ),
    Lesson(
        id="i10_kernel_drivers",
        title="10. The Kernel, Modules, and Drivers",
        summary="Understand how Linux loads hardware drivers.",
        blocks=[
            ("text",
             "Hardware drivers on Linux are usually **kernel modules** - "
             "small pieces of code the kernel can load and unload while "
             "running.\n\n"
             "- `lsmod` - lists currently loaded kernel modules\n"
             "- `lspci` - lists hardware connected via PCI (graphics cards, "
             "Wi-Fi cards, etc.)\n"
             "- `lsusb` - lists connected USB devices\n"
             "- `dmesg` - shows kernel messages, including hardware "
             "detection at boot - useful for diagnosing why a device isn't "
             "working\n\n"
             "On Ubuntu, `ubuntu-drivers devices` can suggest recommended "
             "proprietary drivers (commonly used for NVIDIA graphics "
             "cards)."),
            ("practice",
             "List PCI hardware devices.",
             "lspci",
             "Just type 'lspci'."),
            ("text",
             "If a piece of hardware 'disappears' after an update, "
             "`dmesg | grep -i error` right after plugging it in (or "
             "rebooting) is often the fastest way to see what the kernel "
             "thinks went wrong."),
        ],
    ),
    Lesson(
        id="i11_networking",
        title="11. Networking Basics",
        summary="Check connectivity, IP addresses, and DNS.",
        blocks=[
            ("text",
             "Useful networking commands:\n\n"
             "- `ip a` - shows your network interfaces and their IP "
             "addresses (the modern replacement for the older `ifconfig`)\n"
             "- `ping address` - sends test packets to check connectivity "
             "(press Ctrl+C to stop)\n"
             "- `resolvectl status` - shows DNS configuration\n"
             "- `systemctl status NetworkManager` - check if the network "
             "service is running\n\n"
             "A simple troubleshooting order:\n\n"
             "1. `ip a` - do I have an IP address at all?\n"
             "2. `ping 1.1.1.1` - can I reach the internet by number "
             "(rules out DNS)?\n"
             "3. `ping google.com` - can I reach it by name (tests DNS)?\n\n"
             "If step 2 fails but step 1 looks fine, the problem is likely "
             "with your router or connection. If step 2 works but step 3 "
             "fails, the problem is specifically DNS."),
            ("practice",
             "Show your network interfaces and IP addresses.",
             "ip a",
             "Type 'ip a' (the second word is the letter a)."),
        ],
    ),
    Lesson(
        id="i12_putting_it_together",
        title="12. Putting It Together: Troubleshooting Like Grix",
        summary="Apply everything you've learned to a real troubleshooting workflow.",
        blocks=[
            ("text",
             "You now know enough to follow most of what Grix's System "
             "Sentinel does under the hood. Here's the typical pattern for "
             "investigating any problem:\n\n"
             "1. **Reproduce and observe** - what exactly is happening? "
             "Check `journalctl -b` or a specific service's logs around "
             "the time the problem occurred.\n"
             "2. **Check the obvious things first** - disk space (`df -h`), "
             "failed services (`systemctl --failed`), recent updates "
             "(`apt list --upgradable`).\n"
             "3. **Narrow it down** - use `grep` to filter logs for "
             "keywords like 'error' or 'fail'.\n"
             "4. **Research the specific error message** - search for the "
             "exact text of an error, in quotes, often gets the best "
             "results.\n"
             "5. **Make one change at a time** - so if something improves "
             "(or breaks), you know exactly why.\n"
             "6. **Note what you changed** - so you can undo it if needed.\n\n"
             "This is exactly the loop Grix's diagnostic module follows: "
             "detect → explain → offer a fix → wait for your approval → "
             "log what happened."),
            ("quiz",
             "Why is 'make one change at a time' good troubleshooting advice?",
             ["It's slower so you learn patience", "If multiple things change at once, you can't tell which change fixed (or broke) something", "Linux only allows one change per session", "It uses less disk space"],
             1,
             "When several things change together, a fix and a new problem "
             "can mask each other. Isolating changes makes cause and effect "
             "clear - the same principle behind Grix only ever offering one "
             "fix at a time for confirmation."),
            ("text",
             "🎉 That's the end of the Intermediate track. You've covered "
             "navigation, file management, permissions, processes, "
             "services, logs, networking, and scripting basics - everything "
             "you need to understand most of what Grix's System Sentinel "
             "does, and to start exploring Linux confidently on your own.\n\n"
             "Ready to go further? The **Advanced: System Mastery & Local "
             "Control** track covers text processing, sandboxed apps, "
             "backups, secure remote access, and shaping the shell to work "
             "the way you do."),
        ],
    ),
]


# ---------------------------------------------------------------------------
# Advanced Track
# ---------------------------------------------------------------------------

advanced_lessons: list[Lesson] = [
    Lesson(
        id="a1_text_processing",
        title="1. Advanced Text Processing: find, sed, awk, xargs",
        summary="Find files, edit text in place, parse columns, and chain it all together.",
        blocks=[
            ("text",
             "You already know `grep` for finding lines that match a "
             "pattern. This lesson covers four more tools that, together, "
             "let you find things, transform text, and automate repetitive "
             "tasks - the building blocks of real shell automation.\n\n"
             "We'll cover them one at a time: `find` (locate files), `sed` "
             "(edit text), `awk` (extract columns), and `xargs` (turn "
             "output into arguments for another command)."),
            ("text",
             "**Finding files with `find`**\n\n"
             "Unlike `ls`, which lists what's in one folder, `find` "
             "searches recursively through a whole directory tree and can "
             "filter by name, type, and more:\n\n"
             "- `find . -name \"*.log\"` - find files ending in .log, "
             "starting from the current folder\n"
             "- `find /var/log -type f` - find only regular files (not "
             "folders) under /var/log\n"
             "- `find . -type d` - find only directories\n\n"
             "`find` is case-sensitive by default; there's a `-iname` "
             "variant for case-insensitive matching if you need it."),
            ("practice",
             "Find every .log file inside the 'old_logs' folder you're about to create. First make the folder and a couple of log files.",
             ["mkdir old_logs", "touch old_logs/app1.log", "touch old_logs/app2.log", "find old_logs -name \"*.log\""],
             "mkdir old_logs, then touch two .log files inside it, then find old_logs -name \"*.log\"."),
            ("text",
             "**Editing text with `sed`**\n\n"
             "`sed` (stream editor) transforms text as it flows through, "
             "most commonly to find-and-replace:\n\n"
             "`sed 's/old/new/' file.txt`\n\n"
             "reads `file.txt` and replaces the **first** occurrence of "
             "'old' with 'new' on each line, printing the result (it "
             "doesn't change the file unless you add `-i` for "
             "**in-place** editing - use that with care, since it "
             "overwrites the original).\n\n"
             "Add a `g` at the end to replace **every** occurrence on each "
             "line, not just the first:\n\n"
             "`sed 's/old/new/g' file.txt`\n\n"
             "⚠️ `sed -i` modifies files immediately with no undo. It's "
             "worth testing the command without `-i` first to preview the "
             "result before committing to it."),
            ("practice",
             "Use sed to replace 'world' with 'there' in some piped text.",
             'echo hello world | sed "s/world/there/"',
             'echo hello world, pipe it to sed "s/world/there/".'),
            ("text",
             "**Extracting columns with `awk`**\n\n"
             "`awk` is built around columns - it automatically splits each "
             "line into fields separated by whitespace, accessible as "
             "`$1`, `$2`, `$3`, and so on (`$0` means the whole line).\n\n"
             "`awk '{print $2}' file.txt`\n\n"
             "prints just the second column of every line. It's especially "
             "useful piped after a command whose output is column-shaped, "
             "like `ps aux` or `df -h`:\n\n"
             "`ps aux | awk '{print $2, $11}'`\n\n"
             "prints just the PID and command name of every running "
             "process, instead of the full wide table."),
            ("practice",
             "Use awk to print just the second word from some piped text.",
             'echo one two three | awk "{print $2}"',
             'echo one two three, pipe to awk "{print $2}".'),
            ("text",
             "**Turning output into arguments with `xargs`**\n\n"
             "Many commands (like `find`) print a *list* of things, but "
             "don't act on them directly. `xargs` bridges that gap: it "
             "reads whatever comes in on standard input and runs another "
             "command once for each item.\n\n"
             "This is the single most useful combination in this lesson:\n\n"
             "`find . -name \"*.log\" | xargs rm`\n\n"
             "finds every .log file, then removes each one. Without "
             "`xargs`, `find` would just print the filenames - it doesn't "
             "delete anything by itself.\n\n"
             "⚠️ Always run the `find` part **alone first** to see exactly "
             "what would be matched, before piping it into `xargs rm`. "
             "There's no undo once files are removed."),
            ("practice",
             "Find the .log files in old_logs and remove them in one pipeline.",
             'find old_logs -name "*.log" | xargs rm',
             'find old_logs -name "*.log", pipe to xargs rm.'),
            ("practice",
             "Confirm only the .log files were removed.",
             "ls old_logs",
             "Just 'ls old_logs'."),
            ("quiz",
             "What's the safest way to use 'find ... | xargs rm' on files you're not 100% sure about?",
             ["Just run it - xargs has a built-in undo", "Run the 'find' part alone first to see exactly what matches, before piping to xargs rm", "Always add -r to be safe", "There's no way to preview it"],
             1,
             "Running the find command by itself first shows you the exact "
             "list of files that would be affected, with no risk - nothing "
             "is deleted until you actually pipe it into 'xargs rm'."),
            ("quiz",
             "Which command would replace every occurrence of 'cat' with 'dog' on each line of pets.txt (not just the first per line)?",
             ["sed 's/cat/dog/' pets.txt", "sed 's/cat/dog/g' pets.txt", "grep 'cat' pets.txt", "awk '{print $1}' pets.txt"],
             1,
             "The trailing 'g' flag makes sed replace every match on each "
             "line ('global'), not just the first one."),
        ],
    ),
    Lesson(
        id="a2_flatpak",
        title="2. Package Management Beyond APT: Flatpak & Local Apps",
        summary="Manage sandboxed Flatpak apps and their permissions.",
        blocks=[
            ("text",
             "APT installs software system-wide, sharing libraries across "
             "every app. **Flatpak** takes a different approach: each app "
             "runs in its own sandbox with its own bundled dependencies, "
             "isolated from the rest of your system unless you explicitly "
             "grant it access to something (your camera, a specific "
             "folder, the network, and so on).\n\n"
             "This sandboxing is genuinely useful for a privacy-focused "
             "setup: an app can't quietly read files outside its sandbox "
             "or access hardware you haven't approved, even if the app "
             "itself isn't fully trustworthy."),
            ("command", "flatpak list",
             "Lists every installed Flatpak app and runtime on your "
             "system."),
            ("text",
             "Installing and removing follow a similar shape to APT, just "
             "with different verbs:\n\n"
             "- `flatpak install <remote> <app-id>` - install an app (the "
             "remote is usually `flathub`, the main Flatpak app store)\n"
             "- `flatpak uninstall <app-id>` - remove an app\n"
             "- `flatpak update` - update all installed Flatpak apps\n"
             "- `flatpak uninstall --unused` - remove runtimes nothing "
             "installed needs anymore (Grix's System Sentinel can do this "
             "for you safely too, under Disk Space)"),
            ("text",
             "**Checking and changing permissions**\n\n"
             "Every Flatpak app's sandbox permissions can be inspected and "
             "adjusted with `flatpak override`:\n\n"
             "`flatpak info --show-permissions <app-id>`\n\n"
             "shows what an app is currently allowed to access - things "
             "like `--filesystem=home` (full home directory access) or "
             "`--share=network` (internet access).\n\n"
             "To revoke a permission for a specific app, for example "
             "blocking network access:\n\n"
             "`flatpak override --user --unshare=network <app-id>`\n\n"
             "The `--user` flag means the change only applies to your "
             "account, not system-wide. This is one of the most useful "
             "privacy tools on a Flatpak-based desktop: you can run an app "
             "you don't fully trust with the network cut off entirely."),
            ("quiz",
             "An app you installed via Flatpak doesn't need internet access, and you'd rather it didn't have any. What do you run?",
             ["flatpak uninstall --unused", "flatpak override --user --unshare=network <app-id>", "flatpak update", "sudo apt remove <app-id>"],
             1,
             "'flatpak override --unshare=network' revokes an app's "
             "network access within its sandbox - the app keeps working "
             "for everything else, it just can't reach the internet."),
            ("text",
             "**A note on local-first computing:** because each Flatpak "
             "app is sandboxed with its own explicit permissions, you can "
             "audit exactly what every app on your system can touch, "
             "rather than trusting that system-wide installed software "
             "behaves itself. This is a meaningfully different security "
             "model from traditional package management, and one reason "
             "Flatpak has become popular on privacy-conscious desktops."),
            ("quiz",
             "What is the main architectural difference between a Flatpak app and an APT-installed app?",
             ["Flatpak apps are always free, APT apps are always paid", "Flatpak apps run sandboxed with explicit, per-app permissions; APT apps run with full system access by default", "There is no real difference", "Flatpak only works on servers"],
             1,
             "Flatpak's sandboxing model means each app only gets the "
             "specific permissions it's granted (filesystem access, "
             "network, devices, etc.), while a traditionally-installed "
             "package generally runs with the same access as your user "
             "account."),
        ],
    ),
    Lesson(
        id="a3_backups",
        title="3. Local Storage, Archiving, and Backups: tar & rsync",
        summary="Create compressed archives and perform reliable local backups.",
        blocks=[
            ("text",
             "A local-first workflow means *you* are responsible for your "
             "own backups - no cloud service quietly doing it for you. "
             "Two tools cover almost everything: `tar` for bundling and "
             "compressing files, and `rsync` for efficient, repeatable "
             "copies."),
            ("text",
             "**Archiving with `tar`**\n\n"
             "`tar` bundles multiple files and folders into a single "
             "archive file, optionally compressed. The flags are usually "
             "combined into one cluster:\n\n"
             "- `tar -czvf backup.tar.gz Documents/` - **c**reate an "
             "archive, **z** compress it with gzip, **v**erbose (list "
             "files as it works), **f** the filename comes next\n"
             "- `tar -xzvf backup.tar.gz` - e**x**tract a gzipped archive\n"
             "- `tar -tvf backup.tar.gz` - list (**t**) what's inside "
             "**without** extracting it - always worth doing before "
             "extracting something from an unfamiliar source\n\n"
             "A memory trick: 'czvf' to **c**reate, 'xzvf' to e**x**tract "
             "- only the second letter changes."),
            ("practice",
             "Create a folder with a file in it, then archive it.",
             ["mkdir project", "touch project/main.py", "tar -czvf project.tar.gz project"],
             "mkdir project, touch project/main.py, then tar -czvf project.tar.gz project."),
            ("practice",
             "List the archive's contents without extracting it.",
             "tar -tvf project.tar.gz",
             "tar -tvf project.tar.gz."),
            ("text",
             "**Syncing and backing up with `rsync`**\n\n"
             "`rsync` copies files like `cp`, but smarter: on repeat runs, "
             "it only transfers what's **new or changed**, instead of "
             "copying everything again. This makes it ideal for ongoing "
             "backups, not just one-off copies.\n\n"
             "`rsync -av Documents/ /media/backup-drive/Documents/`\n\n"
             "- `-a` ('archive' mode) preserves permissions, timestamps, "
             "and folder structure - almost always what you want for a "
             "real backup\n"
             "- `-v` is verbose, showing what's being copied\n\n"
             "⚠️ **The trailing slash matters.** `Documents/` (with a "
             "slash) copies the *contents* of Documents into the "
             "destination. `Documents` (no slash) creates a Documents "
             "*folder* inside the destination. Mixing these up is one of "
             "the most common rsync mistakes."),
            ("text",
             "Two more flags worth knowing:\n\n"
             "- `--delete` - also removes files from the destination if "
             "they no longer exist in the source, keeping the backup an "
             "exact mirror (powerful, but means the destination really is "
             "just a mirror - deleted-by-mistake files vanish from the "
             "backup too)\n"
             "- `-n` (or `--dry-run`) - shows exactly what rsync *would* "
             "do, without actually copying or deleting anything. Always "
             "worth running once with `-n` before using `--delete` for "
             "the first time on a new destination."),
            ("practice",
             "Sync your Documents folder to a backup location.",
             "rsync -av Documents/ /backup/",
             "rsync -av Documents/ /backup/ (note the trailing slashes)."),
            ("quiz",
             "Why might you run 'rsync -av --delete -n ...' before the real thing?",
             ["To make it run faster", "The -n flag previews exactly what would change or be deleted, with nothing actually happening yet", "It compresses the files first", "-n means 'normal mode'"],
             1,
             "-n (dry-run) shows you the plan without executing it - "
             "especially important with --delete, since that flag removes "
             "files from the destination that aren't in the source."),
            ("quiz",
             "What's the difference between 'rsync -av Documents/ dest/' and 'rsync -av Documents dest/' (no trailing slash on the source)?",
             ["No difference at all", "With the slash, Documents' contents land directly in dest/; without it, a Documents folder is created inside dest/", "The version without a slash is faster", "The version with a slash compresses the files"],
             1,
             "The trailing slash on the source tells rsync to copy the "
             "contents of the folder, not the folder itself. This is one "
             "of the most common sources of 'why did this create a nested "
             "folder' confusion with rsync."),
        ],
    ),
    Lesson(
        id="a4_ssh",
        title="4. Secure Remote Access: SSH & Keys",
        summary="Connect to remote systems and manage SSH key pairs safely.",
        blocks=[
            ("text",
             "SSH (Secure Shell) lets you log into another Linux machine "
             "over the network and get a full terminal session, encrypted "
             "end-to-end. It's the foundation almost all remote Linux "
             "administration is built on."),
            ("text",
             "**Connecting**\n\n"
             "`ssh username@hostname`\n\n"
             "for example:\n\n"
             "`ssh bobby@192.168.1.50`\n\n"
             "The first time you connect to a given machine, SSH shows you "
             "its cryptographic fingerprint and asks you to confirm it's "
             "expected - this protects against someone secretly "
             "impersonating the server. After confirming once, that "
             "fingerprint is remembered; if it ever changes unexpectedly "
             "on a later connection, SSH will loudly warn you, since that "
             "can indicate someone tampering with the connection."),
            ("practice",
             "Try connecting to a (simulated) remote machine.",
             "ssh bobby@192.168.1.50",
             "ssh, then username@host."),
            ("text",
             "**Key-based authentication**\n\n"
             "Typing a password every time is fine, but SSH **keys** are "
             "both more secure and more convenient. A key pair has two "
             "halves:\n\n"
             "- a **private key** (`id_ed25519` or `id_rsa`) - stays on "
             "your computer, never shared, ideally protected with its own "
             "passphrase\n"
             "- a **public key** (`id_ed25519.pub`) - safe to share, "
             "copied onto any server you want to log into\n\n"
             "Generate a new pair with:\n\n"
             "`ssh-keygen -t ed25519`\n\n"
             "(`ed25519` is a modern, fast, secure key type - prefer it "
             "over the older `rsa` type for new keys.) You'll be prompted "
             "for a file location (the default is usually fine) and "
             "**optionally** a passphrase - a passphrase adds another "
             "layer of protection if your private key file is ever stolen."),
            ("practice",
             "Generate a new SSH key pair.",
             "ssh-keygen -t ed25519",
             "ssh-keygen -t ed25519."),
            ("text",
             "To actually use a key to log in, your **public** key needs "
             "to be copied to the server, into "
             "`~/.ssh/authorized_keys` in the account you're logging into. "
             "The easiest way is:\n\n"
             "`ssh-copy-id username@hostname`\n\n"
             "which copies your public key over (you'll need your "
             "password one last time to authorize it). After that, "
             "logging in with `ssh username@hostname` uses your key "
             "automatically - no password needed."),
            ("text",
             "⚠️ **Never share your private key** (the file *without* "
             "`.pub` on the end). Sharing it is equivalent to handing "
             "someone your password permanently - they could log in as "
             "you anywhere that key is trusted, and you'd have to revoke "
             "it everywhere to undo it."),
            ("text",
             "**Locking down a server: disabling password login**\n\n"
             "Once key-based login works reliably, a common hardening step "
             "is to disable password authentication entirely on the "
             "server, so only people with an authorized key can ever log "
             "in - even if someone guesses or steals a password, it's "
             "useless without the matching private key.\n\n"
             "This is done by editing `/etc/ssh/sshd_config` on the "
             "**server**, setting:\n\n"
             "`PasswordAuthentication no`\n\n"
             "then restarting the SSH service "
             "(`sudo systemctl restart ssh`). ⚠️ **Do this only after "
             "confirming key-based login already works** - if you disable "
             "password auth before your key is set up correctly, you can "
             "lock yourself out entirely (especially painful on a remote "
             "server with no physical access)."),
            ("quiz",
             "Which file should you NEVER share or upload anywhere?",
             ["id_ed25519.pub", "authorized_keys", "id_ed25519 (the private key, no .pub extension)", "known_hosts"],
             2,
             "The private key (no .pub extension) must stay secret - "
             "anyone who has it can authenticate as you. The public key "
             "(.pub) is specifically designed to be shared safely."),
            ("quiz",
             "Why confirm key-based SSH login works BEFORE disabling password authentication on a server?",
             ["It doesn't matter what order you do it in", "Disabling password auth before keys work can lock you out entirely, especially on a remote machine with no physical access", "Password authentication must always stay enabled", "Keys only work after passwords are disabled"],
             1,
             "If something's misconfigured with your key and password "
             "login is already disabled, you have no way back in - "
             "verifying the key works first is the safety net."),
        ],
    ),
    Lesson(
        id="a5_shell_customization",
        title="5. Environment Customization: .bashrc & Aliases",
        summary="Make the terminal yours with config files, aliases, and exported variables.",
        blocks=[
            ("text",
             "By now you've typed plenty of commands. This lesson is about "
             "making the ones you use often shorter, and making your shell "
             "environment set itself up automatically every time you open "
             "a terminal."),
            ("text",
             "**`~/.bashrc`** is a script that runs automatically every "
             "time you open a new terminal window (technically: every new "
             "*interactive non-login* shell - the practical effect is "
             "'every terminal you open'). Anything you put in it - "
             "variables, aliases, custom prompts - takes effect "
             "automatically from then on, without you having to type it "
             "each time.\n\n"
             "It's just a regular text file. Open it with a text editor "
             "(`nano ~/.bashrc`), add your changes at the bottom, save, "
             "and either open a new terminal or run `source ~/.bashrc` to "
             "apply the changes to your current session immediately."),
            ("text",
             "**Aliases** are shorthand for longer commands. Define one "
             "with:\n\n"
             "`alias ll='ls -la'`\n\n"
             "After this, typing `ll` runs `ls -la`. Some genuinely useful "
             "examples to put in your `.bashrc`:\n\n"
             "```\n"
             "alias update='sudo apt update && sudo apt upgrade'\n"
             "alias ..='cd ..'\n"
             "alias grep='grep --color=auto'\n"
             "```\n\n"
             "Typed directly into the terminal, an alias only lasts for "
             "that session. Put it in `.bashrc` to make it permanent."),
            ("practice",
             "Create an alias for a long ls command.",
             "alias ll='ls -la'",
             "alias ll='ls -la' (single quotes around the command)."),
            ("text",
             "**Exporting environment variables** makes a value available "
             "not just to the shell itself, but to any program you launch "
             "from it:\n\n"
             "`export EDITOR=nano`\n\n"
             "Many command-line tools check `$EDITOR` to decide which "
             "text editor to open when they need you to type something - "
             "setting this once in `.bashrc` means `git commit` (and "
             "anything else that asks for editor input) consistently "
             "opens nano instead of whatever the system default happens "
             "to be.\n\n"
             "Like aliases, an `export` typed directly into the terminal "
             "only lasts for that session - put it in `.bashrc` to make it "
             "stick."),
            ("practice",
             "Export an EDITOR environment variable.",
             "export EDITOR=nano",
             "export EDITOR=nano."),
            ("text",
             "**A safety note on editing `.bashrc`:** a broken `.bashrc` "
             "can sometimes prevent new terminals from starting cleanly. "
             "Two habits keep this safe:\n\n"
             "1. Keep a backup before a big edit: `cp ~/.bashrc "
             "~/.bashrc.bak`\n"
             "2. Test changes with `source ~/.bashrc` in your **current** "
             "terminal before closing it - if something's badly broken, "
             "you'll see the error immediately and still have a working "
             "terminal open to fix it, rather than discovering the "
             "problem only when opening a brand new one."),
            ("quiz",
             "You want a custom alias to be available every time you open a new terminal, not just this session. What do you do?",
             ["Type the alias command - it's automatically permanent", "Add the alias to ~/.bashrc", "Restart the computer", "Aliases can never be made permanent"],
             1,
             "Aliases typed directly only last for the current session. "
             "Adding the line to ~/.bashrc makes it run automatically "
             "every time a new terminal starts."),
            ("quiz",
             "What's a sensible safety habit before making big edits to .bashrc?",
             ["Delete it first and start fresh", "Back it up first (cp ~/.bashrc ~/.bashrc.bak), and test with 'source ~/.bashrc' before closing the terminal", "Edit it as root", "There's no way to test changes safely"],
             1,
             "Backing up first gives you an easy way back, and sourcing "
             "the file in your current terminal (rather than only finding "
             "out when you open a new one) means you'll immediately see "
             "if something broke, while you still have a working shell "
             "open to fix it."),
            ("text",
             "🎉 That's the Advanced track. Between this and the "
             "Intermediate track, you can now search and transform text "
             "at scale, manage sandboxed applications, back up your data "
             "reliably, connect securely to remote systems, and shape your "
             "own terminal environment - the full toolkit for running a "
             "self-maintained, local-first Linux system with confidence."),
        ],
    ),
]

TRACKS: list[Track] = [
    Track(
        id="beginner",
        title="Beginner: Getting Comfortable",
        description=(
            "Start here if you're new to Linux or the terminal. You'll "
            "learn what Linux actually is, how to move around the "
            "filesystem, and how to safely create, view, and manage files."
        ),
        lessons=beginner_lessons,
    ),
    Track(
        id="intermediate",
        title="Intermediate: Thinking Like an Admin",
        description=(
            "Build on the basics with pipes, permissions, processes, "
            "services, and logs - the tools you need to understand what "
            "Grix's System Sentinel is doing, and to troubleshoot "
            "confidently on your own."
        ),
        lessons=intermediate_lessons,
    ),
    Track(
        id="advanced",
        title="Advanced: System Mastery & Local Control",
        description=(
            "Go further with text processing, sandboxed apps, backups, "
            "secure remote access, and shell customization - the toolkit "
            "for running a self-maintained, local-first Linux system with "
            "confidence."
        ),
        lessons=advanced_lessons,
    ),
]


def all_tracks() -> list[Track]:
    """Built-in tracks (TRACKS) plus any tracks registered by plugins
    (see grix/modules/plugins.py), in that order. This is what the
    Academy panel, get_track(), get_lesson(), and total_lesson_count()
    all actually use - TRACKS itself stays as just the built-in list,
    importable on its own without triggering plugin loading (useful
    for tests or tools that only care about Grix's own content)."""
    from . import plugins  # local import: avoids loading the plugin
    # system as a side effect of merely importing grix.modules.lessons
    try:
        registry = plugins.get_plugin_registry()
        plugin_tracks = [t for t in registry.lesson_tracks if isinstance(t, Track)]
    except Exception:  # pragma: no cover - plugin loading must never
        # take down Linux Academy even if something is badly broken
        plugin_tracks = []
    return TRACKS + plugin_tracks


def get_track(track_id: str) -> Track | None:
    for t in all_tracks():
        if t.id == track_id:
            return t
    return None


def get_lesson(track_id: str, lesson_id: str) -> Lesson | None:
    track = get_track(track_id)
    if not track:
        return None
    for l in track.lessons:
        if l.id == lesson_id:
            return l
    return None


def total_lesson_count() -> int:
    return sum(len(t.lessons) for t in all_tracks())
