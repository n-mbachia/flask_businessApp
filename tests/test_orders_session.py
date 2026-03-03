import pytest
from sqlalchemy.exc import InternalError, SQLAlchemyError

from types import SimpleNamespace
from app.routes import orders as orders_module


def _dummy_app():
    logger = SimpleNamespace(
        warning=lambda *args, **kwargs: None,
        error=lambda *args, **kwargs: None
    )
    return SimpleNamespace(logger=logger)


def test_fetch_active_products_retries_after_internal_error(monkeypatch):
    reset_calls = []

    def fake_reset():
        reset_calls.append(True)

    monkeypatch.setattr(orders_module, 'reset_db_session', fake_reset)
    monkeypatch.setattr(orders_module, 'current_app', _dummy_app())

    class QueryStub:
        def __init__(self):
            self._first_attempt = True

        def filter_by(self, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            if self._first_attempt:
                self._first_attempt = False
                raise InternalError('SELECT', {}, Exception('simulated aborted transaction'))
            return ['product-a']

    class FakeProductModel:
        name = 'product_name'
        query = QueryStub()

    monkeypatch.setattr(orders_module, 'Product', FakeProductModel)

    products = orders_module._fetch_active_products(user_id=1)

    assert products == ['product-a']
    assert reset_calls == [True]


def test_fetch_active_products_resets_once_on_sqlalchemy_error(monkeypatch):
    reset_calls = []

    def fake_reset():
        reset_calls.append(True)

    monkeypatch.setattr(orders_module, 'reset_db_session', fake_reset)
    monkeypatch.setattr(orders_module, 'current_app', _dummy_app())

    class QueryStub:
        def filter_by(self, **kwargs):
            return self

        def order_by(self, *args, **kwargs):
            return self

        def all(self):
            raise SQLAlchemyError('terminal failure')

    class FakeProductModel:
        name = 'product_name'
        query = QueryStub()

    monkeypatch.setattr(orders_module, 'Product', FakeProductModel)

    with pytest.raises(SQLAlchemyError):
        orders_module._fetch_active_products(user_id=1)

    assert reset_calls == [True]
