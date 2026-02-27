"""Tests for _registry.py service registry."""

import inspect

import pytest

import insight_blueprint._registry as registry


@pytest.fixture(autouse=True)
def _reset_registry():
    """Reset all registry references after each test."""
    yield
    registry.design_service = None
    registry.catalog_service = None
    registry.review_service = None
    registry.rules_service = None


# -- Uninitialized getters raise RuntimeError --


def test_get_design_service_raises_when_uninitialized() -> None:
    registry.design_service = None
    with pytest.raises(RuntimeError, match="design_service"):
        registry.get_design_service()


def test_get_catalog_service_raises_when_uninitialized() -> None:
    registry.catalog_service = None
    with pytest.raises(RuntimeError, match="catalog_service"):
        registry.get_catalog_service()


def test_get_review_service_raises_when_uninitialized() -> None:
    registry.review_service = None
    with pytest.raises(RuntimeError, match="review_service"):
        registry.get_review_service()


def test_get_rules_service_raises_when_uninitialized() -> None:
    registry.rules_service = None
    with pytest.raises(RuntimeError, match="rules_service"):
        registry.get_rules_service()


# -- After wiring, getters return the same instance --


def test_get_design_service_returns_wired_instance() -> None:
    sentinel = object()
    registry.design_service = sentinel  # type: ignore[assignment]
    assert registry.get_design_service() is sentinel


def test_get_catalog_service_returns_wired_instance() -> None:
    sentinel = object()
    registry.catalog_service = sentinel  # type: ignore[assignment]
    assert registry.get_catalog_service() is sentinel


def test_get_review_service_returns_wired_instance() -> None:
    sentinel = object()
    registry.review_service = sentinel  # type: ignore[assignment]
    assert registry.get_review_service() is sentinel


def test_get_rules_service_returns_wired_instance() -> None:
    sentinel = object()
    registry.rules_service = sentinel  # type: ignore[assignment]
    assert registry.get_rules_service() is sentinel


# -- Module purity: only references + getters --


def test_registry_has_no_classes_or_extra_functions() -> None:
    classes = [
        name
        for name, obj in inspect.getmembers(registry, inspect.isclass)
        if not name.startswith("_")
    ]
    assert classes == [], f"Unexpected classes: {classes}"

    functions = {
        name
        for name, obj in inspect.getmembers(registry, inspect.isfunction)
        if not name.startswith("_")
    }
    expected_funcs = {
        "get_design_service",
        "get_catalog_service",
        "get_review_service",
        "get_rules_service",
    }
    assert functions == expected_funcs, (
        f"Unexpected functions: {functions - expected_funcs}"
    )
