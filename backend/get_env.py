import secrets
import shutil
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import ClassVar


class ConsoleANSI(StrEnum):
    RESET = "\033[0m"
    BOLD = "\033[1m"
    DIM = "\033[2m"
    UNDERLINE = "\033[4m"

    RED = "\033[31m"
    GREEN = "\033[32m"
    YELLOW = "\033[33m"
    BLUE = "\033[34m"
    MAGENTA = "\033[35m"
    CYAN = "\033[36m"


class ConsoleIcons(StrEnum):
    INFO = "[?] "
    WARN = "[!] "
    ERROR = "[X] "


class Console:
    colored: StrEnum
    icons: StrEnum

    def __init__(
        self,
        colored: ConsoleANSI = ConsoleANSI,
        icons: ConsoleIcons = ConsoleIcons,
    ):
        self.colored = colored
        self.icons = icons

    def print_colored(
        self,
        text: str,
        color: str | None = None,
        reset: str | None = None,
        endl: str = "\n",
    ):
        color = color or self.colored.RESET
        reset = reset or self.colored.RESET

        print(f"{color}{text}{reset}", end=endl)

    def info(self, text: str):
        self.print_colored(text=f"{self.icons.INFO}{text}")

    def warn(self, text: str):
        self.print_colored(text=f"{self.icons.WARN}{text}", color=self.colored.YELLOW)

    def error(self, text: str):
        self.print_colored(text=f"{self.icons.ERROR}{text}", color=self.colored.RED)

    def prompt(self, text: str, color: str | None = None, reset: str | None = None):
        color = color or self.colored.RESET
        reset = reset or self.colored.RESET

        return input(f"{color}{text}: {reset}")

    def prompt_def(
        self,
        text: str,
        default: str | None = None,
        color: str | None = None,
        reset: str | None = None,
        print_def: bool = True,
    ) -> str:
        _ = self.prompt(
            text=f"{text} {f'(def. {default})' if print_def else ''}",
            color=color,
            reset=reset,
        )
        return default if _ == "" else _

    def get_yn(self, default: str = "N") -> str:
        if default.lower() not in ("y", "n"):
            raise ValueError('Only "y" or "n" can be used here!')
        return "Y/n" if default.lower() == "y" else "y/N"

    def prompt_yn(
        self,
        text: str,
        default: str = "N",
        color: str | None = None,
        reset: str | None = None,
    ) -> bool:
        return self.prompt_def(
            text=f"{text} [{self.get_yn(default=default)}]",
            default=default,
            color=color,
            reset=reset,
            print_def=False,
        ).lower() in ("y", "yes")


@dataclass()
class BaseDataclass:
    def to_dict(self, exclude: set | None = None):
        exclude = exclude or set()

        return {
            key: value
            for key, value in asdict(self).items()
            if key not in exclude and not callable(value)
        }


@dataclass()
class Configuration(BaseDataclass):
    THIS_DIR: ClassVar[Path] = Path(__file__).parent
    BACKUP_DIR: ClassVar[Path] = THIS_DIR / "backups"

    FILENAME: str = field(default=".env")
    FILE_EXIST: bool = field(default=False)
    MIGRATE: bool = field(default=False)

    fields_autogenerate: dict[str, Callable[[], str]] = field(
        default_factory=lambda: {"PEPPER": secrets.token_hex}
    )
    env_fields: dict[str, str] = field(
        default_factory=lambda: {"DB_URL": "", "PEPPER": "", "REDIS_URL": ""}
    )
    existing_conf: dict[str, str] = field(default_factory=dict)


def conf_from_exist_file(file: Path):
    _conf = {}
    for line in file.read_text().split("\n"):
        if line.strip().startswith("#") or "=" not in line:
            continue

        field, value = map(str.strip, line.strip().split("=", 1))
        _conf[field] = value
    return _conf


def copy_file(
    filename: Path | str,
    original_dir: Path | str,
    backup_dir: Path | str,
    writer: Console | None = None,
    naming_pattern: str | None = None,
):
    naming_pattern = naming_pattern or datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

    original = Path(original_dir) / filename
    backup = Path(backup_dir) / (str(filename) + "." + naming_pattern)

    shutil.copy2(original, backup)

    if writer is None:
        print("[!] env has been copied!")
    else:
        writer.warn("env has been copied!")


def write_env(env_payload: dict[str, str], path: Path):
    lines = [
        f"# FILE GENERATED: {datetime.now().strftime('%H:%M:%S %d-%m-%Y')}",
        *(f"{fld}={val}" for fld, val in env_payload.items()),
    ]

    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


cons = Console()
conf = Configuration()


def main(args: list):
    if "--migrate" in args or "-m" in args:
        conf.MIGRATE = True
        cons.info("Env migrating")

    conf.FILENAME = cons.prompt_def(text="Filename", default=conf.FILENAME)

    conf.FILE_EXIST = (conf.THIS_DIR / conf.FILENAME).exists()

    if conf.FILE_EXIST:
        cons.warn("File already exist!")

        conf.existing_conf = conf_from_exist_file(file=(conf.THIS_DIR / conf.FILENAME))

        if not conf.BACKUP_DIR.exists() and cons.prompt_yn(
            "Create backup dir? (backups)"
        ):
            conf.BACKUP_DIR.mkdir()

        if conf.BACKUP_DIR.exists():
            copy_file(
                filename=conf.FILENAME,
                original_dir=conf.THIS_DIR,
                backup_dir=conf.BACKUP_DIR,
                writer=cons,
            )
        else:
            cons.warn("! ENV HAS NOT BACKUPING !")

    new_env: dict = {}
    i: int = 1

    for fld in conf.env_fields:
        if fld in conf.existing_conf and conf.MIGRATE:
            new_env[fld] = conf.existing_conf[fld]
            continue

        if fld in conf.fields_autogenerate:
            new_env[fld] = conf.fields_autogenerate[fld](16)
            continue

        new_env[fld] = cons.prompt(f"({i}) {fld}")
        i += 1

    if conf.MIGRATE:
        new_env = conf.existing_conf | new_env

    write_env(env_payload=new_env, path=(conf.THIS_DIR / conf.FILENAME))
    cons.info("Env has been saved!")


if __name__ == "__main__":
    try:
        main(args=sys.argv[1:])
    except KeyboardInterrupt:
        print("\n^C exit...")
