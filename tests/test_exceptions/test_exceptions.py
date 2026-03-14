"""Tests for the PolicyFoundry exception hierarchy."""

from policyfoundry.exceptions import (
    AdapterError,
    ConfigError,
    ConfigFileNotFound,
    ConfigValidationError,
    IngestionError,
    OutputError,
    PipelineError,
    PolicyFoundryError,
    StorageError,
)


def test_all_exceptions_importable() -> None:
    """All 9 exception classes are importable from policyfoundry.exceptions."""
    classes = [
        PolicyFoundryError,
        ConfigError,
        ConfigFileNotFound,
        ConfigValidationError,
        IngestionError,
        StorageError,
        AdapterError,
        PipelineError,
        OutputError,
    ]
    assert len(classes) == 9
    for cls in classes:
        assert issubclass(cls, Exception)


def test_base_exception_hierarchy() -> None:
    """PolicyFoundryError is a subclass of Exception."""
    assert issubclass(PolicyFoundryError, Exception)
    err = PolicyFoundryError("base error")
    assert isinstance(err, Exception)


def test_config_error_hierarchy() -> None:
    """ConfigError hierarchy checks inheritance chain."""
    assert issubclass(ConfigError, PolicyFoundryError)
    assert issubclass(ConfigFileNotFound, ConfigError)
    assert issubclass(ConfigValidationError, ConfigError)


def test_domain_error_hierarchy() -> None:
    """All domain errors inherit from PolicyFoundryError."""
    domain_errors = [IngestionError, StorageError, AdapterError, PipelineError, OutputError]
    for cls in domain_errors:
        msg = cls.__name__ + " not subclass of PolicyFoundryError"
        assert issubclass(cls, PolicyFoundryError), msg


def test_error_code_and_details() -> None:
    """PolicyFoundryError carries error_code and details when provided."""
    err = PolicyFoundryError(
        "something went wrong",
        error_code="TEST_001",
        details={"key": "value"},
    )
    assert err.error_code == "TEST_001"
    assert err.details == {"key": "value"}


def test_error_code_defaults_none() -> None:
    """PolicyFoundryError error_code defaults to None."""
    err = PolicyFoundryError("msg")
    assert err.error_code is None


def test_details_defaults_empty() -> None:
    """PolicyFoundryError details defaults to empty dict."""
    err = PolicyFoundryError("msg")
    assert err.details == {}


def test_str_returns_message() -> None:
    """str(exception) returns the message."""
    err = PolicyFoundryError("test message")
    assert str(err) == "test message"


def test_catch_by_parent() -> None:
    """Exceptions can be caught by parent class."""
    try:
        raise ConfigFileNotFound("not found")
    except ConfigError as e:
        assert str(e) == "not found"

    try:
        raise ConfigFileNotFound("not found again")
    except PolicyFoundryError as e:
        assert str(e) == "not found again"


def test_structured_config_error() -> None:
    """ConfigFileNotFound inherits structured error attributes."""
    err = ConfigFileNotFound(
        "Not found",
        error_code="CONF_001",
        details={"path": "/etc/config.yaml"},
    )
    assert str(err) == "Not found"
    assert err.error_code == "CONF_001"
    assert err.details == {"path": "/etc/config.yaml"}
    assert isinstance(err, ConfigError)
    assert isinstance(err, PolicyFoundryError)
