from pydantic import SecretStr

from chicory.config import BackendConfig, BrokerConfig, ChicoryConfig
from chicory.types import ValidationMode


class TestBrokerConfig:
    def test_broker_config_defaults(self) -> None:
        broker_config = BrokerConfig()
        assert broker_config.redis_host is None
        assert broker_config.redis_port == 6379
        assert broker_config.redis_db == 0
        assert broker_config.redis_user is None
        assert broker_config.redis_password is None
        assert broker_config.redis_url is None
        assert broker_config.redis_dsn is None

    def test_redis_dsn_with_redis_url(self) -> None:
        url = "redis://user:password@localhost:6379/0"
        broker_config = BrokerConfig()
        broker_config.redis_url = url
        assert broker_config.redis_dsn == url

    def test_redis_dsn_with_host_and_port(self) -> None:
        broker_config = BrokerConfig()
        broker_config.redis_host = "localhost"
        broker_config.redis_port = 6379
        broker_config.redis_user = "user"
        broker_config.redis_password = SecretStr("password")
        expected_dsn = "redis://user:password@localhost:6379/0"
        assert broker_config.redis_dsn == expected_dsn


class TestBackendConfig:
    def test_backend_config_defaults(self) -> None:
        backend_config = BackendConfig()
        assert backend_config.redis_host is None
        assert backend_config.redis_port == 6379
        assert backend_config.redis_db == 1
        assert backend_config.redis_user is None
        assert backend_config.redis_password is None
        assert backend_config.redis_url is None
        assert backend_config.redis_dsn is None

    def test_redis_dsn_with_redis_url(self) -> None:
        url = "redis://user:password@localhost:6379/1"
        backend_config = BackendConfig()
        backend_config.redis_url = url
        assert backend_config.redis_dsn == url

    def test_redis_dsn_with_host_and_port(self) -> None:
        backend_config = BackendConfig()
        backend_config.redis_host = "localhost"
        backend_config.redis_port = 6379
        backend_config.redis_user = "user"
        backend_config.redis_password = SecretStr("password")
        expected_dsn = "redis://user:password@localhost:6379/1"
        assert backend_config.redis_dsn == expected_dsn


class TestChicoryConfig:
    def test_chicory_config_defaults(self) -> None:
        chicory_config = ChicoryConfig()
        assert isinstance(chicory_config.broker, BrokerConfig)
        assert isinstance(chicory_config.backend, BackendConfig)
        assert chicory_config.validation_mode == ValidationMode.INPUTS
