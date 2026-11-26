"""CLI (bootstrap, report-varieties) contra la BD de pruebas `*_test` (nunca la de desarrollo)."""
import pytest
from sqlalchemy import event, func, select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from apps.backend.src import cli
from apps.backend.src.features.auth.application import passwords_handler
from apps.backend.src.features.auth.dependencies import get_auth_service
from apps.backend.src.features.auth.domain import schemas
from apps.backend.src.features.auth.infrastructure.postgres.models import Role, User
from apps.backend.src.features.inventory.infrastructure.postgres.models import Plot
from apps.backend.tests.pg_support import load_test_database_url

pytestmark = pytest.mark.pg

PASSWORD = "Sup3r-secreta-xyz"
CONFIRM = "--yes-i-know-this-targets-the-configured-database"


@pytest.fixture
def url(pg_engine):
    return load_test_database_url()


def bootstrap_args(url, *extra, username="root", confirm=True):
    args = ["--database-url", url, "bootstrap", "--username", username, "--full-name", "Root Admin",
            "--email", f"{username}@finca.com", *extra]
    return [*args, CONFIRM] if confirm else args


def count(pg_engine, model):
    with Session(pg_engine) as s:
        return s.scalar(select(func.count()).select_from(model))


def assert_no_secret(capsys, *secrets):
    captured = capsys.readouterr()
    for secret in secrets:
        assert secret and secret not in captured.out + captured.err


# ---------- bootstrap ----------
def test_bootstrap_creates_admin_role_and_user_and_admin_can_log_in(pg_engine, url, capsys):
    code = cli.main(bootstrap_args(url), env={"BOOTSTRAP_PASSWORD": PASSWORD})
    assert code == 0
    with Session(pg_engine) as s:
        role = s.scalar(select(Role))
        assert role.name == "Administrador"
        user = s.scalar(select(User))
        assert user.username == "root" and user.role_id == role.id
        assert user.password_hash != PASSWORD and passwords_handler.verify_password(PASSWORD, user.password_hash)
        service = get_auth_service(s)
        login = service.login(schemas.LoginRequest(username="root", password=PASSWORD))
        assert login["role"] == "Administrador"
        assert service.is_admin(service.get_user_from_token(login["access_token"]))
    out = capsys.readouterr()
    assert PASSWORD not in out.out + out.err
    assert "root" in out.out


def test_bootstrap_reads_password_from_prompt_when_env_is_missing(pg_engine, url, capsys):
    answers = iter([PASSWORD, PASSWORD])
    code = cli.main(bootstrap_args(url), env={}, getpass_fn=lambda prompt="": next(answers))
    assert code == 0 and count(pg_engine, User) == 1
    assert_no_secret(capsys, PASSWORD)


def test_prompt_mismatch_aborts_without_writing(pg_engine, url, capsys):
    answers = iter([PASSWORD, PASSWORD + "x"])
    code = cli.main(bootstrap_args(url), env={}, getpass_fn=lambda prompt="": next(answers))
    assert code != 0 and count(pg_engine, User) == 0 and count(pg_engine, Role) == 0
    assert_no_secret(capsys, PASSWORD)


def test_bootstrap_refuses_when_any_user_exists(pg_engine, url, capsys):
    assert cli.main(bootstrap_args(url), env={"BOOTSTRAP_PASSWORD": PASSWORD}) == 0
    code = cli.main(bootstrap_args(url, username="otro"), env={"BOOTSTRAP_PASSWORD": PASSWORD})
    assert code != 0 and count(pg_engine, User) == 1
    assert "--force-additional" in capsys.readouterr().err


def test_force_additional_creates_another_admin_reusing_the_role(pg_engine, url):
    cli.main(bootstrap_args(url), env={"BOOTSTRAP_PASSWORD": PASSWORD})
    code = cli.main(bootstrap_args(url, "--force-additional", username="otro"), env={"BOOTSTRAP_PASSWORD": PASSWORD})
    assert code == 0 and count(pg_engine, User) == 2 and count(pg_engine, Role) == 1


def test_rerun_for_an_existing_username_is_a_noop_success(pg_engine, url, capsys):
    cli.main(bootstrap_args(url), env={"BOOTSTRAP_PASSWORD": PASSWORD})
    code = cli.main(bootstrap_args(url), env={"BOOTSTRAP_PASSWORD": "otra-clave-123"})
    assert code == 0 and count(pg_engine, User) == 1
    assert "ya existe" in capsys.readouterr().out


def test_bootstrap_reuses_an_existing_admin_role_when_there_are_no_users(pg_engine, url):
    with Session(pg_engine) as s:
        s.add(Role(name="Administrador"))
        s.commit()
    assert cli.main(bootstrap_args(url), env={"BOOTSTRAP_PASSWORD": PASSWORD}) == 0
    assert count(pg_engine, Role) == 1 and count(pg_engine, User) == 1


def test_role_name_that_is_not_an_admin_role_is_rejected(pg_engine, url):
    code = cli.main(bootstrap_args(url, "--role-name", "Operario"), env={"BOOTSTRAP_PASSWORD": PASSWORD})
    assert code != 0 and count(pg_engine, User) == 0 and count(pg_engine, Role) == 0


def test_weak_password_is_rejected_without_echoing_it(pg_engine, url, capsys):
    code = cli.main(bootstrap_args(url), env={"BOOTSTRAP_PASSWORD": "corta"})
    assert code != 0 and count(pg_engine, User) == 0
    assert_no_secret(capsys, "corta")


def test_password_can_never_be_given_as_an_argument(pg_engine, url, capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(bootstrap_args(url, "--password", PASSWORD), env={})
    assert exc.value.code != 0 and count(pg_engine, User) == 0
    assert_no_secret(capsys, PASSWORD)
    with pytest.raises(SystemExit):
        cli.main(bootstrap_args(url, f"--password={PASSWORD}"), env={})
    assert_no_secret(capsys, PASSWORD)


def test_without_confirmation_it_aborts_and_shows_target_without_password(pg_engine, url, capsys):
    code = cli.main(bootstrap_args(url, confirm=False), env={"BOOTSTRAP_PASSWORD": PASSWORD},
                    input_fn=lambda prompt="": "no")
    assert code != 0 and count(pg_engine, User) == 0
    out = capsys.readouterr()
    target = make_url(url)
    text = out.out + out.err
    assert cli.describe_target(url) in text and target.database in text
    text = text.replace(cli.describe_target(url), "")  # el destino sí se muestra; nada más puede contener secretos
    for secret in (PASSWORD, target.password):
        if secret:
            assert secret not in text


def test_typed_yes_confirms_the_write(pg_engine, url):
    code = cli.main(bootstrap_args(url, confirm=False), env={"BOOTSTRAP_PASSWORD": PASSWORD},
                    input_fn=lambda prompt="": "yes")
    assert code == 0 and count(pg_engine, User) == 1


def test_bootstrap_without_stdin_available_aborts(pg_engine, url):
    def no_stdin(prompt=""):
        raise EOFError

    code = cli.main(bootstrap_args(url, confirm=False), env={"BOOTSTRAP_PASSWORD": PASSWORD}, input_fn=no_stdin)
    assert code != 0 and count(pg_engine, User) == 0


# ---------- report-varieties ----------
def seed_plots(pg_engine, varieties):
    with Session(pg_engine) as s:
        role = Role(name="operario")
        s.add(role)
        s.flush()
        user = User(role_id=role.id, username="ana", email="ana@x.com", password_hash="h", full_name="Ana")
        s.add(user)
        s.flush()
        for i, variety in enumerate(varieties):
            s.add(Plot(owner_id=user.id, name=f"L{i}", variety=variety, area_ha=1))
        s.commit()


def test_report_varieties_lists_counts_merged_spellings_and_near_duplicates(pg_engine, url, capsys):
    seed_plots(pg_engine, ["Biloxi", " biloxi ", "BILOXI", "Biloxy", "Légacy", "Legacy", "Duke"])
    assert cli.main(["--database-url", url, "report-varieties"], env={}) == 0
    out = capsys.readouterr().out
    assert "biloxi: 3" in out and "legacy: 2" in out and "duke: 1" in out
    merged_section = out.split("unificadas")[1].split("duplicados")[0]
    assert "biloxi" in merged_section and "legacy" in merged_section and "duke" not in merged_section
    assert "biloxi ~ biloxy" in out.split("duplicados")[1]


def test_report_varieties_issues_only_selects_and_the_transaction_is_read_only(pg_engine):
    seed_plots(pg_engine, ["Biloxi"])
    statements = []

    def listener(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(pg_engine, "before_cursor_execute", listener)
    try:
        cli.run_report_varieties(pg_engine, out=lambda line: None)
    finally:
        event.remove(pg_engine, "before_cursor_execute", listener)
    assert statements and all(s.lstrip().upper().startswith("SELECT") for s in statements)
    with cli.read_only_connection(pg_engine) as conn:
        with pytest.raises(DBAPIError) as exc:
            conn.exec_driver_sql("DELETE FROM plots")
        assert exc.value.orig.pgcode == "25006"  # read_only_sql_transaction (independiente del idioma del servidor)
    assert count(pg_engine, Plot) == 1


def test_report_varieties_on_empty_table_succeeds(pg_engine, url, capsys):
    assert cli.main(["--database-url", url, "report-varieties"], env={}) == 0
    assert "0" in capsys.readouterr().out


def test_unimplemented_t1x_commands_are_not_exposed():
    with pytest.raises(SystemExit):
        cli.main(["grant-superuser"], env={})
