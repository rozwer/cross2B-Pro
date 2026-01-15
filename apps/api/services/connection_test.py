"""Connection test service for external APIs.

Provides lightweight connection tests for:
- LLM providers (Gemini, OpenAI, Anthropic)
- SERP API
- Google Ads API
- GitHub

Tests are designed to minimize API costs while verifying connectivity.
"""

import logging
import os
import time
from dataclasses import dataclass
from typing import Any

import httpx

logger = logging.getLogger(__name__)


@dataclass
class ConnectionTestResult:
    """Result of a connection test."""

    success: bool
    service: str
    latency_ms: int | None = None
    error_message: str | None = None
    details: dict[str, Any] | None = None


class ConnectionTestService:
    """Service for testing connections to external APIs."""

    # Supported services
    LLM_SERVICES = {"gemini", "openai", "anthropic"}
    EXTERNAL_SERVICES = {"serp", "google_ads", "github"}
    ALL_SERVICES = LLM_SERVICES | EXTERNAL_SERVICES

    async def test_connection(
        self,
        service: str,
        api_key: str | None = None,
        model: str | None = None,
    ) -> ConnectionTestResult:
        """Test connection to a service.

        Args:
            service: Service name (gemini, openai, anthropic, serp, google_ads, github)
            api_key: API key to test (uses env var if not provided)
            model: Model name for LLM services (optional)

        Returns:
            ConnectionTestResult with success status and details
        """
        service = service.lower()

        if service not in self.ALL_SERVICES:
            return ConnectionTestResult(
                success=False,
                service=service,
                error_message=f"Unknown service: {service}. Supported: {', '.join(sorted(self.ALL_SERVICES))}",
            )

        start_time = time.time()

        try:
            if service in self.LLM_SERVICES:
                result = await self._test_llm(service, api_key, model)
            elif service == "serp":
                result = await self._test_serp(api_key)
            elif service == "google_ads":
                result = await self._test_google_ads(api_key)
            elif service == "github":
                result = await self._test_github(api_key)
            else:
                result = ConnectionTestResult(
                    success=False,
                    service=service,
                    error_message="Test not implemented",
                )

            # Add latency
            latency_ms = int((time.time() - start_time) * 1000)
            result.latency_ms = latency_ms
            return result

        except Exception as e:
            latency_ms = int((time.time() - start_time) * 1000)
            logger.exception(f"Connection test failed for {service}")
            return ConnectionTestResult(
                success=False,
                service=service,
                latency_ms=latency_ms,
                error_message=str(e),
            )

    async def _test_llm(
        self,
        provider: str,
        api_key: str | None = None,
        model: str | None = None,
    ) -> ConnectionTestResult:
        """Test LLM provider connection using health_check().

        Uses minimal tokens to verify API connectivity.
        """
        from apps.api.llm.base import get_llm_client
        from apps.api.llm.exceptions import LLMAuthenticationError, LLMError

        # Temporarily set API key in environment if provided
        env_var_map = {
            "gemini": "GEMINI_API_KEY",
            "openai": "OPENAI_API_KEY",
            "anthropic": "ANTHROPIC_API_KEY",
        }

        env_var = env_var_map.get(provider)
        original_key = None

        if api_key and env_var:
            original_key = os.environ.get(env_var)
            os.environ[env_var] = api_key

        try:
            # Create client with optional model override
            kwargs = {}
            if model:
                kwargs["model"] = model

            client = get_llm_client(provider, **kwargs)

            # Use health_check method
            is_healthy = await client.health_check()

            if is_healthy:
                return ConnectionTestResult(
                    success=True,
                    service=provider,
                    details={
                        "provider": provider,
                        "model": model or client.default_model,
                        "available_models": client.available_models,
                    },
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    service=provider,
                    error_message="Health check returned False",
                )

        except LLMAuthenticationError as e:
            return ConnectionTestResult(
                success=False,
                service=provider,
                error_message=f"Authentication failed: {e}",
            )
        except LLMError as e:
            return ConnectionTestResult(
                success=False,
                service=provider,
                error_message=f"LLM error: {e}",
            )
        finally:
            # Restore original environment
            if env_var:
                if original_key is not None:
                    os.environ[env_var] = original_key
                elif api_key:
                    os.environ.pop(env_var, None)

    async def _test_serp(self, api_key: str | None = None) -> ConnectionTestResult:
        """Test SERP API connection with minimal query.

        Uses SerpApi's account info endpoint which doesn't consume credits.
        """
        key = api_key or os.getenv("SERP_API_KEY")

        if not key:
            return ConnectionTestResult(
                success=False,
                service="serp",
                error_message="SERP_API_KEY not provided",
            )

        try:
            # Use account info endpoint (free, no credits used)
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://serpapi.com/account",
                    params={"api_key": key},
                )

            if response.status_code == 200:
                data = response.json()
                return ConnectionTestResult(
                    success=True,
                    service="serp",
                    details={
                        "account_email": data.get("account_email"),
                        "plan": data.get("plan_name"),
                        "searches_remaining": data.get("searches_per_month", 0) - data.get("this_month_usage", 0),
                    },
                )
            elif response.status_code == 401:
                return ConnectionTestResult(
                    success=False,
                    service="serp",
                    error_message="Invalid API key",
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    service="serp",
                    error_message=f"API returned status {response.status_code}",
                )

        except httpx.TimeoutException:
            return ConnectionTestResult(
                success=False,
                service="serp",
                error_message="Request timed out",
            )
        except httpx.RequestError as e:
            return ConnectionTestResult(
                success=False,
                service="serp",
                error_message=f"Network error: {e}",
            )

    async def _test_google_ads(self, api_key: str | None = None) -> ConnectionTestResult:
        """Test Google Ads API connection.

        Note: Currently in mock mode. Real implementation requires OAuth.
        """
        # Check if using mock mode
        use_mock = os.getenv("USE_MOCK_GOOGLE_ADS", "true").lower() == "true"

        if use_mock:
            return ConnectionTestResult(
                success=True,
                service="google_ads",
                details={
                    "mode": "mock",
                    "note": "Google Ads API is in mock mode. Set USE_MOCK_GOOGLE_ADS=false when API is available.",
                },
            )

        # Real API test would go here
        # For now, return that it's not implemented
        return ConnectionTestResult(
            success=False,
            service="google_ads",
            error_message="Google Ads API real mode not implemented. Use mock mode or implement OAuth.",
        )

    async def _test_github(self, token: str | None = None) -> ConnectionTestResult:
        """Test GitHub API connection.

        Uses /user endpoint to verify token validity.
        SECURITY: Response does NOT include the token.
        """
        key = token or os.getenv("GITHUB_TOKEN")

        if not key:
            return ConnectionTestResult(
                success=False,
                service="github",
                error_message="GITHUB_TOKEN not provided",
            )

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    "https://api.github.com/user",
                    headers={
                        "Accept": "application/vnd.github+json",
                        "Authorization": f"Bearer {key}",
                        "X-GitHub-Api-Version": "2022-11-28",
                    },
                )

            if response.status_code == 200:
                data = response.json()
                return ConnectionTestResult(
                    success=True,
                    service="github",
                    details={
                        "username": data.get("login"),
                        "name": data.get("name"),
                        "type": data.get("type"),  # User or Bot
                        # Do NOT include token in response
                    },
                )
            elif response.status_code == 401:
                return ConnectionTestResult(
                    success=False,
                    service="github",
                    error_message="Invalid or expired token",
                )
            elif response.status_code == 403:
                # Check rate limit
                remaining = response.headers.get("X-RateLimit-Remaining")
                if remaining == "0":
                    return ConnectionTestResult(
                        success=False,
                        service="github",
                        error_message="Rate limit exceeded",
                    )
                return ConnectionTestResult(
                    success=False,
                    service="github",
                    error_message="Permission denied",
                )
            else:
                return ConnectionTestResult(
                    success=False,
                    service="github",
                    error_message=f"API returned status {response.status_code}",
                )

        except httpx.TimeoutException:
            return ConnectionTestResult(
                success=False,
                service="github",
                error_message="Request timed out",
            )
        except httpx.RequestError as e:
            return ConnectionTestResult(
                success=False,
                service="github",
                error_message=f"Network error: {e}",
            )

    async def test_all(
        self,
        settings: dict[str, dict[str, Any]] | None = None,
    ) -> dict[str, ConnectionTestResult]:
        """Test all configured services.

        Args:
            settings: Optional dict of {service: {api_key, model, ...}}

        Returns:
            Dict of {service: ConnectionTestResult}
        """
        settings = settings or {}
        results = {}

        for service in self.ALL_SERVICES:
            service_settings = settings.get(service, {})
            results[service] = await self.test_connection(
                service=service,
                api_key=service_settings.get("api_key"),
                model=service_settings.get("model"),
            )

        return results
