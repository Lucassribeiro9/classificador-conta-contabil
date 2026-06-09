from core.database import build_engine_kwargs


def test_sqlite_engine_kwargs_include_check_same_thread_false():
    kwargs = build_engine_kwargs("sqlite:///./data/classificador.db")

    assert kwargs == {"connect_args": {"check_same_thread": False}}


def test_postgresql_engine_kwargs_do_not_include_sqlite_connect_args():
    kwargs = build_engine_kwargs(
        "postgresql+psycopg://user:password@postgres:5432/classificador"
    )

    assert kwargs == {}
