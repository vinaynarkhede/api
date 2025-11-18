"""Consul service discovery integration."""
import consul
import consul.aio
from typing import List, Dict, Optional
from gateway.config.settings import settings


class ConsulServiceDiscovery:
    """Service discovery using HashiCorp Consul."""

    def __init__(self):
        """Initialize Consul client."""
        self.consul_client: Optional[consul.aio.Consul] = None
        self.enabled = settings.consul_enabled

        if self.enabled:
            self._init_consul()

    def _init_consul(self):
        """Initialize Consul connection."""
        try:
            self.consul_client = consul.aio.Consul(
                host=settings.consul_host,
                port=settings.consul_port,
            )
        except Exception as e:
            print(f"Warning: Could not connect to Consul: {e}")
            self.enabled = False

    async def register_service(
        self,
        service_name: str,
        service_id: str,
        address: str,
        port: int,
        health_check_url: str,
        tags: List[str] = None,
        meta: Dict[str, str] = None,
    ) -> bool:
        """
        Register a service with Consul.

        Args:
            service_name: Service name
            service_id: Unique service ID
            address: Service address
            port: Service port
            health_check_url: HTTP health check URL
            tags: Service tags
            meta: Service metadata

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        try:
            await self.consul_client.agent.service.register(
                name=service_name,
                service_id=service_id,
                address=address,
                port=port,
                tags=tags or [],
                meta=meta or {},
                check={
                    "http": health_check_url,
                    "interval": "10s",
                    "timeout": "5s",
                    "deregister_critical_service_after": "30s",
                },
            )
            return True

        except Exception as e:
            print(f"Failed to register service: {e}")
            return False

    async def deregister_service(self, service_id: str) -> bool:
        """
        Deregister a service from Consul.

        Args:
            service_id: Service ID to deregister

        Returns:
            True if successful
        """
        if not self.enabled:
            return False

        try:
            await self.consul_client.agent.service.deregister(service_id)
            return True

        except Exception as e:
            print(f"Failed to deregister service: {e}")
            return False

    async def discover_service(self, service_name: str) -> List[Dict]:
        """
        Discover healthy instances of a service.

        Args:
            service_name: Service name to discover

        Returns:
            List of service instances
        """
        if not self.enabled:
            return []

        try:
            index, services = await self.consul_client.health.service(
                service_name, passing=True
            )

            instances = []
            for service in services:
                instances.append({
                    "service_id": service["Service"]["ID"],
                    "address": service["Service"]["Address"],
                    "port": service["Service"]["Port"],
                    "tags": service["Service"]["Tags"],
                    "meta": service["Service"]["Meta"],
                })

            return instances

        except Exception as e:
            print(f"Failed to discover service: {e}")
            return []

    async def get_all_services(self) -> Dict[str, List]:
        """
        Get all registered services.

        Returns:
            Dictionary of service name to instances
        """
        if not self.enabled:
            return {}

        try:
            index, services = await self.consul_client.catalog.services()

            all_services = {}
            for service_name in services.keys():
                instances = await self.discover_service(service_name)
                if instances:
                    all_services[service_name] = instances

            return all_services

        except Exception as e:
            print(f"Failed to get all services: {e}")
            return {}


# Global Consul client
consul_discovery = ConsulServiceDiscovery()
