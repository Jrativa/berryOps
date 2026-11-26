# src/cli.py
"""CLI de administración. Se ejecuta desde la raíz del repo:

    python -m apps.backend.src.cli <comando> ...

Comandos:
  bootstrap         (interino) crea el rol de administrador y el primer usuario admin con el esquema actual.
                    La contraseña NUNCA es un argumento: se lee de la variable de entorno BOOTSTRAP_PASSWORD
                    o de un prompt interactivo (getpass), y jamás se muestra ni se registra.
  report-varieties  (solo lectura) variedades distintas de `plots.variety`, grafías unificadas y casi-duplicados.

Por defecto actúa sobre la BD configurada en apps/backend/.env (DB_*); `--database-url` la sustituye
(lo usan las pruebas). `bootstrap` escribe, así que exige confirmación: la bandera
`--yes-i-know-this-targets-the-configured-database` o escribir `yes` tras ver host/puerto/BD de destino.

T1.x ampliará `bootstrap` con la creación de organización, finca y membresía, y añadirá `grant-superuser`.
Esos comandos NO existen todavía (no existen las tablas ni la columna `users.is_platform_superuser`).
"""
import argparse
import getpass
import os
import sys
from collections.abc import Callable, Iterator, Mapping
from contextlib import contextmanager

from pydantic import ValidationError
from sqlalchemy import create_engine, select
from sqlalchemy.engine import Connection, Engine, make_url
from sqlalchemy.orm import sessionmaker

from apps.backend.src.core.config import settings
from apps.backend.src.core.uow import open_unit_of_work
from apps.backend.src.core.variety_analysis import analyze_varieties
from apps.backend.src.features.auth.dependencies import get_auth_service
from apps.backend.src.features.auth.domain import schemas
from apps.backend.src.features.inventory.infrastructure.postgres.models import Plot

PASSWORD_ENV_VAR = "BOOTSTRAP_PASSWORD"
DEFAULT_ADMIN_ROLE = "Administrador"
CONFIRM_FLAG = "--yes-i-know-this-targets-the-configured-database"
FORCE_FLAG = "--force-additional"


class CliError(Exception):
    """Fallo esperado: se muestra el mensaje (nunca secretos) y el proceso termina con código 1."""


class _Parser(argparse.ArgumentParser):
    """Rechaza argumentos desconocidos SIN repetirlos (p. ej. `--password algo` no debe volcarse a stderr)."""

    def parse_args(self, args=None, namespace=None):
        parsed, extras = self.parse_known_args(args, namespace)
        if extras:
            self.error(f"{len(extras)} argumento(s) no reconocido(s). La contraseña nunca se pasa como "
                       f"argumento: use {PASSWORD_ENV_VAR} o el prompt interactivo")
        return parsed


def build_parser() -> argparse.ArgumentParser:
    parser = _Parser(prog="python -m apps.backend.src.cli", description="Administración de Arándanos",
                     epilog="grant-superuser y la creación de organización/finca llegan con T1.x.",
                     allow_abbrev=False)
    parser.add_argument("--database-url", help="URL de la BD (por defecto la de apps/backend/.env)")
    commands = parser.add_subparsers(dest="command", required=True, parser_class=_Parser)

    boot = commands.add_parser("bootstrap", help="crea el rol admin y el primer usuario admin", allow_abbrev=False)
    boot.add_argument("--username", required=True)
    boot.add_argument("--full-name", required=True)
    boot.add_argument("--email", required=True)
    boot.add_argument("--role-name", default=DEFAULT_ADMIN_ROLE)
    boot.add_argument(FORCE_FLAG, action="store_true", help="permite crear otro admin aunque ya existan usuarios")
    boot.add_argument(CONFIRM_FLAG, dest="assume_yes", action="store_true",
                      help="confirma que se escribirá en la BD indicada, sin pregunta interactiva")

    commands.add_parser("report-varieties", help="informe de solo lectura de plots.variety", allow_abbrev=False)
    return parser


# ---------- infraestructura ----------
def describe_target(url: str) -> str:
    """Host, puerto y nombre de la BD. Nunca la contraseña."""
    target = make_url(url)
    return f"host={target.host} puerto={target.port} bd={target.database}"


def confirm_write(url: str, assume_yes: bool, input_fn: Callable[[str], str]) -> bool:
    print(f"Destino: {describe_target(url)}")
    if assume_yes:
        return True
    try:
        return input_fn("Se escribirá en esa base de datos. Escriba 'yes' para continuar: ").strip() == "yes"
    except EOFError:
        return False


@contextmanager
def read_only_connection(engine: Engine) -> Iterator[Connection]:
    """Conexión cuya transacción PostgreSQL es READ ONLY: la BD rechaza cualquier escritura."""
    with engine.connect() as connection:
        yield connection.execution_options(postgresql_readonly=True)


# ---------- bootstrap ----------
def read_password(env: Mapping[str, str], getpass_fn: Callable[[str], str]) -> str:
    password = env.get(PASSWORD_ENV_VAR)
    if password:
        return password
    password = getpass_fn("Contraseña del administrador: ")
    if password != getpass_fn("Repita la contraseña: "):
        raise CliError("Las contraseñas no coinciden")
    return password


def run_bootstrap(engine: Engine, args: argparse.Namespace, get_password: Callable[[], str]) -> int:
    if args.role_name.strip().lower() not in settings.admin_roles:
        raise CliError(f"'{args.role_name}' no es un rol de administrador (ADMIN_ROLE_NAMES)")
    # Misma unidad de trabajo que la API: commit si todo sale bien, rollback ante cualquier error.
    with contextmanager(open_unit_of_work)(sessionmaker(bind=engine, autoflush=False)) as session:
        service = get_auth_service(session)
        if service.user_repo.get_by_username(args.username):
            print(f"El usuario '{args.username}' ya existe; no se hace nada.")
            return 0
        if service.user_repo.exists_any() and not args.force_additional:
            raise CliError(f"Ya existen usuarios; bootstrap no crea más. Use {FORCE_FLAG} para forzarlo")
        password = get_password()
        try:
            role = service.role_repo.get_by_name(args.role_name) or service.create_role(
                schemas.RoleCreate(name=args.role_name))
            service.register_user(schemas.UserCreate(
                username=args.username, email=args.email, full_name=args.full_name,
                role_id=role.id, password=password, created_by="cli:bootstrap"))
        except ValidationError as exc:  # solo `msg`: el error completo incluiría el valor (la contraseña)
            raise CliError("; ".join(e["msg"] for e in exc.errors())) from None
        except ValueError as exc:
            raise CliError(str(exc)) from None
    print(f"Administrador '{args.username}' creado con el rol '{args.role_name}'.")
    return 0


# ---------- report-varieties ----------
def run_report_varieties(engine: Engine, out: Callable[[str], None] = print) -> int:
    with read_only_connection(engine) as connection:
        names = list(connection.execute(select(Plot.variety)).scalars())
    report = analyze_varieties(names)
    out(f"Variedades distintas (normalizadas): {len(report.counts)}")
    for key, total in report.counts.items():
        out(f"  {key}: {total} lote(s)")
    out("Grafías unificadas (misma variedad escrita distinto):")
    for key in report.merged:
        out(f"  {key} <- " + ", ".join(f"{s!r} ({n})" for s, n in report.spellings[key].items()))
    out("Posibles duplicados (distancia de edición <= 2):")
    for first, second in report.near_duplicates:
        out(f"  {first} ~ {second}")
    return 0


# ---------- entrada ----------
def main(argv: list[str] | None = None, *, env: Mapping[str, str] | None = None,
         getpass_fn: Callable[[str], str] = getpass.getpass, input_fn: Callable[[str], str] = input) -> int:
    args = build_parser().parse_args(argv)
    env = os.environ if env is None else env
    url = args.database_url or settings.DATABASE_URL
    try:
        if args.command == "bootstrap" and not confirm_write(url, args.assume_yes, input_fn):
            raise CliError("Operación cancelada: no se confirmó la escritura")
        engine = create_engine(url)
        try:
            if args.command == "bootstrap":
                return run_bootstrap(engine, args, lambda: read_password(env, getpass_fn))
            return run_report_varieties(engine)
        finally:
            engine.dispose()
    except CliError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
