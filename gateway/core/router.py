"""Request routing logic for the API Gateway."""
import yaml
from typing import Dict, List, Optional
from pathlib import Path

from shared.models import RouteConfig, ServiceConfig
from shared.exceptions import RouteNotFound, ConfigurationError
from shared.utils import match_route


class Router:
    """Handles request routing to upstream services."""

    def __init__(self, config_path: str = "gateway/config/routes.yaml"):
        """Initialize router with configuration."""
        self.config_path = Path(config_path)
        self.routes: List[RouteConfig] = []
        self.services: Dict[str, ServiceConfig] = {}
        self.load_configuration()

    def load_configuration(self) -> None:
        """Load routing configuration from YAML file."""
        if not self.config_path.exists():
            raise ConfigurationError(f"Routes config not found: {self.config_path}")

        with open(self.config_path, 'r') as f:
            config = yaml.safe_load(f)

        # Load routes
        for route_data in config.get('routes', []):
            route = RouteConfig(**route_data)
            self.routes.append(route)

        # Load services
        for service_name, service_data in config.get('services', {}).items():
            service = ServiceConfig(**service_data)
            self.services[service_name] = service

    def reload_configuration(self) -> None:
        """Reload configuration from file."""
        self.routes = []
        self.services = {}
        self.load_configuration()

    def find_route(self, path: str, method: str) -> Optional[tuple[RouteConfig, Dict[str, str]]]:
        """
        Find a matching route for the given path and method.

        Returns:
            Tuple of (RouteConfig, path_params) if found, None otherwise
        """
        for route in self.routes:
            # Check if method is allowed
            if method.upper() not in [m.upper() for m in route.methods]:
                continue

            # Try to match the path
            path_params = match_route(path, route.path)
            if path_params is not None:
                return route, path_params

        return None

    def get_upstream_url(self, route: RouteConfig, path: str, path_params: Dict[str, str]) -> str:
        """
        Build the upstream URL for the matched route.

        Args:
            route: Matched route configuration
            path: Original request path
            path_params: Extracted path parameters

        Returns:
            Full upstream URL
        """
        # Handle internal routes
        if route.upstream == "internal":
            return "internal"

        # Get service configuration if available
        service = self.services.get(route.service)
        if service:
            upstream_base = service.url
        else:
            upstream_base = route.upstream

        # Build the upstream path
        if route.strip_path:
            # Remove the route prefix from the path
            upstream_path = path.replace(route.path.split('{')[0].rstrip('/'), '', 1)
            if not upstream_path:
                upstream_path = '/'
        else:
            upstream_path = path

        # Combine base URL and path
        return f"{upstream_base.rstrip('/')}{upstream_path}"

    def get_service(self, service_name: str) -> Optional[ServiceConfig]:
        """Get service configuration by name."""
        return self.services.get(service_name)

    def get_all_routes(self) -> List[RouteConfig]:
        """Get all configured routes."""
        return self.routes

    def get_all_services(self) -> Dict[str, ServiceConfig]:
        """Get all configured services."""
        return self.services


# Global router instance
router = Router()
