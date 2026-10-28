# md-seeder

## Preview

```
╭─salem@archdex in ~/Desktop/tmp
╰$ ./md-seeder.sh -b main -r "git@github.com:SalemSaberhagen13/md-seeder.git"
               _                         _
 _ __ ___   __| |      ___  ___  ___  __| | ___ _ __
| '_ ` _ \ / _` |_____/ __|/ _ \/ _ \/ _` |/ _ \ '__|
| | | | | | (_| |_____\__ \  __/  __/ (_| |  __/ |
|_| |_| |_|\__,_|     |___/\___|\___|\__,_|\___|_|
Downloading branch/version main from git@github.com:SalemSaberhagen13/md-seeder.git
Please wait...
Hope you've set up your ssh agent
cp -f /tmp/tmp.RRpVWo3Vct/md_files/CLAUDE.md /home/salem/Desktop/tmp/.claude/md_files/CLAUDE.md
1 file(s) copied
```

## Usage

```
Use: md-seeder -r <git@github.com:user/repo.git> [-b <branch>] [-k <path_ssh_key>] [-f] [-d] [-h]

Options:
  -r <repo_url>      Git repository URL to clone (required)
  -b <branch>        Branch or tag to clone (default: master)
  -k <path_ssh_key>  Path to SSH private key (optional; uses ssh-agent by default)
  -f                 Flatten: copy all .md files directly into .claude/ without subfolders
  -d                 Delete existing .md files in .claude/ before copying new ones
  -h                 Show this help message and exit
```
