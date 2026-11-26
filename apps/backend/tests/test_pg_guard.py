"""El guard decide, sin conectar a nada, si una URL puede usarse como BD de pruebas."""
import pytest

from apps.backend.tests.pg_guard import DbTarget, UnsafeDatabaseError, assert_safe_test_database

DEV = DbTarget(host="dbhost", port=5432, name="arandanos")


def url(name: str, host: str = "dbhost", port: int = 5432) -> str:
    return f"postgresql://user:secret@{host}:{port}/{name}"


def test_accepts_a_test_database():
    assert_safe_test_database(url("arandanos_test"), DEV)


def test_refuses_a_dev_like_name():
    with pytest.raises(UnsafeDatabaseError, match="_test"):
        assert_safe_test_database(url("arandanos"), DEV)


@pytest.mark.parametrize("name", ["test", "arandanos_testing", "Arandanos_TEST", "prod", ""])
def test_refuses_names_not_ending_in_lowercase_test_suffix(name):
    with pytest.raises(UnsafeDatabaseError):
        assert_safe_test_database(url(name), DEV)


def test_refuses_the_dev_database_even_if_it_ends_in_test():
    dev = DbTarget(host="dbhost", port=5432, name="arandanos_test")
    with pytest.raises(UnsafeDatabaseError, match="desarrollo"):
        assert_safe_test_database(url("arandanos_test"), dev)


def test_refuses_same_name_on_other_host():
    dev = DbTarget(host="otro", port=5433, name="arandanos_test")
    with pytest.raises(UnsafeDatabaseError):
        assert_safe_test_database(url("arandanos_test"), dev)


def test_without_dev_reference_only_the_suffix_rule_applies():
    assert_safe_test_database(url("x_test"), None)
    with pytest.raises(UnsafeDatabaseError):
        assert_safe_test_database(url("x"), None)


def test_refuses_non_postgres_or_unparsable_urls():
    with pytest.raises(UnsafeDatabaseError):
        assert_safe_test_database("sqlite:///arandanos_test", DEV)
    with pytest.raises(UnsafeDatabaseError):
        assert_safe_test_database("no es una url", DEV)


def test_error_message_never_leaks_the_password():
    with pytest.raises(UnsafeDatabaseError) as exc:
        assert_safe_test_database(url("arandanos"), DEV)
    assert "secret" not in str(exc.value)


def test_dev_target_is_read_from_env_file(tmp_path):
    from apps.backend.tests.pg_guard import read_dev_target
    env = tmp_path / ".env"
    env.write_text("DB_HOST=h\nDB_PORT=6543\nDB_NAME=prod_db\n")
    assert read_dev_target(env) == DbTarget(host="h", port=6543, name="prod_db")
    assert read_dev_target(tmp_path / "missing.env") is None
