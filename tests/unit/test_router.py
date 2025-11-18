"""Unit tests for the router module."""
import pytest
from gateway.core.router import Router
from shared.exceptions import ConfigurationError


def test_router_initialization():
    """Test router initialization."""
    router = Router()
    assert router is not None
    assert len(router.routes) > 0
    assert len(router.services) > 0


def test_find_route_exact_match():
    """Test finding routes with exact path match."""
    router = Router()

    # Test exact match
    route_match = router.find_route("/api/users", "GET")
    assert route_match is not None

    route, path_params = route_match
    assert route.path == "/api/users"
    assert "GET" in route.methods


def test_find_route_with_params():
    """Test finding routes with path parameters."""
    router = Router()

    # Test parameterized route
    route_match = router.find_route("/api/users/123", "GET")
    assert route_match is not None

    route, path_params = route_match
    assert route.path == "/api/users/{user_id}"
    assert path_params == {"user_id": "123"}


def test_find_route_method_not_allowed():
    """Test that routes with wrong methods are not matched."""
    router = Router()

    # Test wrong method
    route_match = router.find_route("/api/users", "DELETE")
    assert route_match is None


def test_find_route_not_found():
    """Test route not found scenario."""
    router = Router()

    # Test non-existent route
    route_match = router.find_route("/api/nonexistent", "GET")
    assert route_match is None


def test_get_upstream_url():
    """Test building upstream URL."""
    router = Router()

    route_match = router.find_route("/api/users/123", "GET")
    assert route_match is not None

    route, path_params = route_match
    upstream_url = router.get_upstream_url(route, "/api/users/123", path_params)

    assert "user-service" in upstream_url
    assert "/api/users/123" in upstream_url


def test_get_service():
    """Test getting service configuration."""
    router = Router()

    service = router.get_service("user-service")
    assert service is not None
    assert service.url == "http://user-service:8001"
    assert service.health_check == "/health"


def test_reload_configuration():
    """Test reloading configuration."""
    router = Router()
    initial_routes_count = len(router.routes)

    router.reload_configuration()

    assert len(router.routes) == initial_routes_count
