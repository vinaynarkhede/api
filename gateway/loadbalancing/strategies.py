"""Load balancing strategies for distributing requests."""
import hashlib
import random
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from collections import defaultdict


class LoadBalancingStrategy(ABC):
    """Base class for load balancing strategies."""

    @abstractmethod
    async def select_instance(self, instances: List[Dict], context: Dict = None) -> Optional[Dict]:
        """
        Select an instance from the available instances.

        Args:
            instances: List of available service instances
            context: Request context (for sticky sessions, etc.)

        Returns:
            Selected instance or None
        """
        pass


class RoundRobinStrategy(LoadBalancingStrategy):
    """Round-robin load balancing strategy."""

    def __init__(self):
        """Initialize round-robin strategy."""
        self.counters: Dict[str, int] = defaultdict(int)

    async def select_instance(self, instances: List[Dict], context: Dict = None) -> Optional[Dict]:
        """Select next instance in round-robin fashion."""
        if not instances:
            return None

        # Generate key for this service
        key = instances[0].get("service_name", "default")

        # Get and increment counter
        index = self.counters[key] % len(instances)
        self.counters[key] += 1

        return instances[index]


class LeastConnectionsStrategy(LoadBalancingStrategy):
    """Least connections load balancing strategy."""

    def __init__(self):
        """Initialize least connections strategy."""
        self.connections: Dict[str, int] = defaultdict(int)

    async def select_instance(self, instances: List[Dict], context: Dict = None) -> Optional[Dict]:
        """Select instance with fewest active connections."""
        if not instances:
            return None

        # Find instance with minimum connections
        min_connections = float('inf')
        selected_instance = instances[0]

        for instance in instances:
            instance_id = instance.get("service_id", str(instance))
            connections = self.connections[instance_id]

            if connections < min_connections:
                min_connections = connections
                selected_instance = instance

        # Increment connection count
        instance_id = selected_instance.get("service_id", str(selected_instance))
        self.connections[instance_id] += 1

        return selected_instance

    def release_connection(self, instance: Dict):
        """Release connection for an instance."""
        instance_id = instance.get("service_id", str(instance))
        if self.connections[instance_id] > 0:
            self.connections[instance_id] -= 1


class WeightedRoundRobinStrategy(LoadBalancingStrategy):
    """Weighted round-robin load balancing strategy."""

    def __init__(self):
        """Initialize weighted round-robin strategy."""
        self.current_weights: Dict[str, List[int]] = {}
        self.counters: Dict[str, int] = defaultdict(int)

    async def select_instance(self, instances: List[Dict], context: Dict = None) -> Optional[Dict]:
        """Select instance based on weights."""
        if not instances:
            return None

        # Get weights from instances (default weight = 1)
        weights = [instance.get("weight", 1) for instance in instances]

        # Generate key
        key = instances[0].get("service_name", "default")

        # Initialize weights if needed
        if key not in self.current_weights:
            self.current_weights[key] = weights.copy()

        # Find instance with highest current weight
        max_weight_idx = self.current_weights[key].index(max(self.current_weights[key]))

        # Decrease selected instance weight and reset others
        self.current_weights[key][max_weight_idx] -= 1

        # Reset weights if all are 0
        if all(w <= 0 for w in self.current_weights[key]):
            self.current_weights[key] = weights.copy()

        return instances[max_weight_idx]


class ConsistentHashingStrategy(LoadBalancingStrategy):
    """Consistent hashing for sticky sessions."""

    def __init__(self, virtual_nodes: int = 150):
        """
        Initialize consistent hashing strategy.

        Args:
            virtual_nodes: Number of virtual nodes per instance
        """
        self.virtual_nodes = virtual_nodes
        self.hash_ring: Dict[str, List[int]] = {}

    def _hash(self, key: str) -> int:
        """Hash a key to integer."""
        return int(hashlib.md5(key.encode()).hexdigest(), 16)

    def _build_hash_ring(self, instances: List[Dict]) -> Dict[int, Dict]:
        """Build hash ring from instances."""
        ring = {}

        for instance in instances:
            instance_id = instance.get("service_id", str(instance))

            # Add virtual nodes
            for i in range(self.virtual_nodes):
                virtual_key = f"{instance_id}:{i}"
                hash_value = self._hash(virtual_key)
                ring[hash_value] = instance

        return ring

    async def select_instance(self, instances: List[Dict], context: Dict = None) -> Optional[Dict]:
        """Select instance using consistent hashing."""
        if not instances:
            return None

        # Get session ID or user ID from context
        session_id = None
        if context:
            session_id = context.get("session_id") or context.get("user_id") or context.get("ip_address")

        if not session_id:
            # Fallback to random if no session info
            return random.choice(instances)

        # Build hash ring
        ring = self._build_hash_ring(instances)

        # Hash the session ID
        hash_value = self._hash(str(session_id))

        # Find the first node clockwise from hash_value
        sorted_keys = sorted(ring.keys())

        for key in sorted_keys:
            if key >= hash_value:
                return ring[key]

        # Wrap around to first node
        return ring[sorted_keys[0]]


class RandomStrategy(LoadBalancingStrategy):
    """Random load balancing strategy."""

    async def select_instance(self, instances: List[Dict], context: Dict = None) -> Optional[Dict]:
        """Select random instance."""
        if not instances:
            return None

        return random.choice(instances)


class LoadBalancer:
    """Main load balancer that uses different strategies."""

    def __init__(self):
        """Initialize load balancer with available strategies."""
        self.strategies = {
            "round_robin": RoundRobinStrategy(),
            "least_connections": LeastConnectionsStrategy(),
            "weighted_round_robin": WeightedRoundRobinStrategy(),
            "consistent_hashing": ConsistentHashingStrategy(),
            "random": RandomStrategy(),
        }

        self.default_strategy = "round_robin"

    async def select_instance(
        self,
        instances: List[Dict],
        strategy: str = None,
        context: Dict = None,
    ) -> Optional[Dict]:
        """
        Select an instance using specified strategy.

        Args:
            instances: Available instances
            strategy: Strategy name (default: round_robin)
            context: Request context

        Returns:
            Selected instance
        """
        strategy_name = strategy or self.default_strategy
        strategy_obj = self.strategies.get(strategy_name)

        if not strategy_obj:
            strategy_obj = self.strategies[self.default_strategy]

        return await strategy_obj.select_instance(instances, context)

    def release_connection(self, instance: Dict, strategy: str = None):
        """
        Release connection (for least_connections strategy).

        Args:
            instance: Instance to release
            strategy: Strategy name
        """
        strategy_name = strategy or self.default_strategy
        strategy_obj = self.strategies.get(strategy_name)

        if isinstance(strategy_obj, LeastConnectionsStrategy):
            strategy_obj.release_connection(instance)


# Global load balancer
load_balancer = LoadBalancer()
