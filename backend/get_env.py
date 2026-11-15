import secrets
import shutil
import sys
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import ClassVar
from urllib.parse import urlparse

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519


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


def generate_login(*args, prefix: str = "shopper", length: int = 6) -> str:
    suffix = "".join(
        secrets.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(length)
    )
    return f"{prefix}_{suffix}"


def generate_password(length: int = 16, *args) -> str:
    return secrets.token_urlsafe(length)


def generate_eddsa_private_key(*args) -> str:
    seed = secrets.token_bytes(32)
    return seed.hex()


def derive_eddsa_public_key(private_key_hex: str) -> str:
    priv = ed25519.Ed25519PrivateKey.from_private_bytes(
        bytes.fromhex(private_key_hex.strip())
    )
    pub = priv.public_key()
    return pub.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    ).hex()


@dataclass()
class Configuration(BaseDataclass):
    THIS_DIR: ClassVar[Path] = Path(__file__).parent
    BACKUP_DIR: ClassVar[Path] = THIS_DIR / "backups"

    FILENAME: str = field(default=".env")
    FILE_EXIST: bool = field(default=False)
    MIGRATE: bool = field(default=False)
    AUTO: bool = field(default=False)

    fields_autogenerate: dict[str, Callable[..., str]] = field(
        default_factory=lambda: {
            "POSTGRES_USER": generate_login,
            "POSTGRES_PASSWORD": generate_password,
            "GRAFANA_ADMIN_PASSWORD": generate_password,
            "PEPPER": secrets.token_hex,
            "JWT_PRIVATE_KEY": generate_eddsa_private_key,
        }
    )
    env_fields: dict[str, str] = field(
        default_factory=lambda: {
            "POSTGRES_DB": "shopperflox",
            "POSTGRES_USER": "",
            "POSTGRES_PASSWORD": "",
            "DB_URL": "",
            "PEPPER": "",
            "REDIS_URL": "redis://localhost:6379/0",
            "JWT_ALGORITHM": "EdDSA",
            "JWT_PRIVATE_KEY": "",
            "JWT_PUBLIC_KEY": "",
            "GRAFANA_ADMIN_USER": "admin",
            "GRAFANA_ADMIN_PASSWORD": "",
        }
    )
    existing_conf: dict[str, str] = field(default_factory=dict)


def conf_from_exist_file(file: Path):
    _conf = {}
    for line in file.read_text(encoding="utf-8").split("\n"):
        if line.strip().startswith("#") or "=" not in line:
            continue

        field_name, value = map(str.strip, line.strip().split("=", 1))
        _conf[field_name] = value

    # Extract user/password from DB_URL if not explicitly present
    if "DB_URL" in _conf and "@" in _conf["DB_URL"]:
        try:
            parsed = urlparse(_conf["DB_URL"])
            if parsed.username and "POSTGRES_USER" not in _conf:
                _conf["POSTGRES_USER"] = parsed.username
            if parsed.password and "POSTGRES_PASSWORD" not in _conf:
                _conf["POSTGRES_PASSWORD"] = parsed.password
            if parsed.path.lstrip("/") and "POSTGRES_DB" not in _conf:
                _conf["POSTGRES_DB"] = parsed.path.lstrip("/")
        except Exception:
            pass

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
    content = "\n".join(lines) + "\n"

    path.write_text(content, encoding="utf-8")

    # Mirror to root .env if writing backend/.env for docker compose
    resolved = path.resolve()
    if resolved.parent.name == "backend":
        root_env = resolved.parent.parent / resolved.name
        if root_env.parent.exists():
            root_env.write_text(content, encoding="utf-8")


cons = Console()
conf = Configuration()


def main(args: list):
    if "--migrate" in args or "-m" in args:
        conf.MIGRATE = True
        cons.info("Env migrating")

    if "--auto" in args or "-a" in args or "-y" in args:
        conf.AUTO = True
        cons.info("Auto mode enabled")

    if not conf.AUTO:
        conf.FILENAME = cons.prompt_def(text="Filename", default=conf.FILENAME)

    conf.FILE_EXIST = (conf.THIS_DIR / conf.FILENAME).exists()

    if conf.FILE_EXIST:
        cons.warn("File already exist!")

        conf.existing_conf = conf_from_exist_file(file=(conf.THIS_DIR / conf.FILENAME))

        if not conf.BACKUP_DIR.exists():
            if conf.AUTO or cons.prompt_yn("Create backup dir? (backups)"):
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

    for fld, def_val in conf.env_fields.items():
        if fld in conf.existing_conf and conf.MIGRATE and conf.existing_conf[fld]:
            new_env[fld] = conf.existing_conf[fld]
            continue

        if fld == "JWT_PUBLIC_KEY":
            priv_key = new_env.get("JWT_PRIVATE_KEY") or conf.existing_conf.get(
                "JWT_PRIVATE_KEY"
            )
            if priv_key:
                new_env[fld] = derive_eddsa_public_key(priv_key)
                continue

        if fld == "DB_URL":
            pg_user = (
                new_env.get("POSTGRES_USER")
                or conf.existing_conf.get("POSTGRES_USER")
                or "shopperflox"
            )
            pg_pass = (
                new_env.get("POSTGRES_PASSWORD")
                or conf.existing_conf.get("POSTGRES_PASSWORD")
                or "shopperflox"
            )
            pg_db = (
                new_env.get("POSTGRES_DB")
                or conf.existing_conf.get("POSTGRES_DB")
                or "shopperflox"
            )
            generated_db_url = (
                f"postgresql+asyncpg://{pg_user}:{pg_pass}@localhost:5432/{pg_db}"
            )
            if conf.AUTO:
                new_env[fld] = generated_db_url
            else:
                new_env[fld] = cons.prompt_def(f"({i}) {fld}", default=generated_db_url)
                i += 1
            continue

        if fld in conf.fields_autogenerate:
            gen_val = conf.fields_autogenerate[fld](16)
            if conf.AUTO:
                new_env[fld] = gen_val
            else:
                new_env[fld] = cons.prompt_def(f"({i}) {fld}", default=gen_val)
                i += 1
            continue

        if conf.AUTO:
            new_env[fld] = def_val
        elif def_val:
            new_env[fld] = cons.prompt_def(f"({i}) {fld}", default=def_val)
            i += 1
        else:
            new_env[fld] = cons.prompt(f"({i}) {fld}")
            i += 1

    if conf.MIGRATE:
        new_env = conf.existing_conf | new_env

    # Ensure JWT_PUBLIC_KEY is derived if JWT_PRIVATE_KEY exists
    if "JWT_PRIVATE_KEY" in new_env and new_env["JWT_PRIVATE_KEY"]:
        if "JWT_PUBLIC_KEY" not in new_env or not new_env["JWT_PUBLIC_KEY"]:
            new_env["JWT_PUBLIC_KEY"] = derive_eddsa_public_key(
                new_env["JWT_PRIVATE_KEY"]
            )

    write_env(env_payload=new_env, path=(conf.THIS_DIR / conf.FILENAME))
    cons.info("Env has been saved!")


if __name__ == "__main__":
    try:
        main(args=sys.argv[1:])
    except KeyboardInterrupt:
        print("\n^C exit...")
