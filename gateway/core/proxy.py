"""HTTP proxy for forwarding requests to upstream services."""
import httpx
from typing import Dict, Optional, Any
from fastapi import Request, Response
from fastapi.responses import StreamingResponse

from gateway.config.settings import settings
from shared.exceptions import UpstreamError, TimeoutError as GatewayTimeoutError


class HTTPProxy:
    """Handles proxying HTTP requests to upstream services."""

    def __init__(self):
        """Initialize HTTP proxy with default settings."""
        self.timeout = httpx.Timeout(
            timeout=settings.proxy_timeout_seconds,
            connect=10.0,
            read=settings.proxy_timeout_seconds,
        )
        self.limits = httpx.Limits(max_keepalive_connections=100, max_connections=200)
        self.client: Optional[httpx.AsyncClient] = None

    async def get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self.client is None or self.client.is_closed:
            self.client = httpx.AsyncClient(
                timeout=self.timeout,
                limits=self.limits,
                follow_redirects=True,
                http2=True,
            )
        return self.client

    async def close(self):
        """Close the HTTP client."""
        if self.client and not self.client.is_closed:
            await self.client.aclose()

    async def forward_request(
        self,
        upstream_url: str,
        method: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None,
        query_params: Optional[Dict[str, Any]] = None,
    ) -> Response:
        """
        Forward a request to an upstream service.

        Args:
            upstream_url: Full URL to the upstream service
            method: HTTP method
            headers: Request headers
            body: Request body
            query_params: Query parameters

        Returns:
            FastAPI Response object

        Raises:
            UpstreamError: If upstream service returns an error
            GatewayTimeoutError: If request times out
        """
        client = await self.get_client()

        # Prepare headers (remove hop-by-hop headers)
        forwarded_headers = self._prepare_headers(headers or {})

        try:
            # Make the request to upstream
            response = await client.request(
                method=method,
                url=upstream_url,
                headers=forwarded_headers,
                content=body,
                params=query_params,
            )

            # Prepare response headers
            response_headers = self._prepare_response_headers(dict(response.headers))

            # Return the response
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
                media_type=response.headers.get("content-type"),
            )

        except httpx.TimeoutException as e:
            raise GatewayTimeoutError(f"Upstream request timed out: {str(e)}")
        except httpx.RequestError as e:
            raise UpstreamError(f"Failed to connect to upstream service: {str(e)}")
        except Exception as e:
            raise UpstreamError(f"Unexpected error during proxy: {str(e)}")

    async def stream_request(
        self,
        upstream_url: str,
        method: str,
        headers: Optional[Dict[str, str]] = None,
        body: Optional[bytes] = None,
        query_params: Optional[Dict[str, Any]] = None,
    ) -> StreamingResponse:
        """
        Stream a request to an upstream service (for large responses).

        Args:
            upstream_url: Full URL to the upstream service
            method: HTTP method
            headers: Request headers
            body: Request body
            query_params: Query parameters

        Returns:
            StreamingResponse for streaming content
        """
        client = await self.get_client()
        forwarded_headers = self._prepare_headers(headers or {})

        try:
            async with client.stream(
                method=method,
                url=upstream_url,
                headers=forwarded_headers,
                content=body,
                params=query_params,
            ) as response:
                response_headers = self._prepare_response_headers(dict(response.headers))

                async def generate():
                    async for chunk in response.aiter_bytes():
                        yield chunk

                return StreamingResponse(
                    content=generate(),
                    status_code=response.status_code,
                    headers=response_headers,
                    media_type=response.headers.get("content-type"),
                )

        except httpx.TimeoutException as e:
            raise GatewayTimeoutError(f"Upstream request timed out: {str(e)}")
        except httpx.RequestError as e:
            raise UpstreamError(f"Failed to connect to upstream service: {str(e)}")
        except Exception as e:
            raise UpstreamError(f"Unexpected error during streaming: {str(e)}")

    def _prepare_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """
        Prepare headers for forwarding.
        Remove hop-by-hop headers and add necessary headers.
        """
        # Hop-by-hop headers that should not be forwarded
        hop_by_hop = {
            'connection', 'keep-alive', 'proxy-authenticate',
            'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade'
        }

        forwarded = {
            k: v for k, v in headers.items()
            if k.lower() not in hop_by_hop
        }

        # Add X-Forwarded headers
        if 'x-forwarded-for' not in forwarded:
            forwarded['x-forwarded-for'] = headers.get('x-real-ip', 'unknown')

        forwarded['x-forwarded-proto'] = 'http'  # Could be https in production
        forwarded['x-gateway'] = settings.app_name

        return forwarded

    def _prepare_response_headers(self, headers: Dict[str, str]) -> Dict[str, str]:
        """Prepare response headers."""
        # Remove headers that should not be forwarded back
        hop_by_hop = {
            'connection', 'keep-alive', 'proxy-authenticate',
            'proxy-authorization', 'te', 'trailers', 'transfer-encoding', 'upgrade'
        }

        return {
            k: v for k, v in headers.items()
            if k.lower() not in hop_by_hop
        }


# Global proxy instance
http_proxy = HTTPProxy()
