"""Security utilities for tools.

This module provides security validation functions to prevent:
- SSRF (Server-Side Request Forgery)
- Path traversal attacks
- Other injection vulnerabilities
"""

import ipaddress
import logging
import os
import socket
from typing import Any
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

# Private/internal IP ranges that should be blocked
BLOCKED_IP_NETWORKS = [
    # Loopback
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
    # Private networks
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    # Link-local
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("fe80::/10"),
    # Unique local addresses (IPv6 private)
    ipaddress.ip_network("fc00::/7"),
    # Documentation/test
    ipaddress.ip_network("192.0.2.0/24"),
    ipaddress.ip_network("198.51.100.0/24"),
    ipaddress.ip_network("203.0.113.0/24"),
    ipaddress.ip_network("2001:db8::/32"),
    # AWS/Cloud metadata endpoints
    ipaddress.ip_network("169.254.169.254/32"),
]

# Blocked hostnames (cloud metadata, internal services)
BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata.goog",
    "169.254.169.254",
}

# Default allowed schemes
ALLOWED_SCHEMES = {"http", "https"}

# Domain whitelist (if set, only these domains are allowed)
# Set via environment variable: URL_WHITELIST=example.com,another.com
DOMAIN_WHITELIST: set[str] | None = None
_whitelist_env = os.getenv("URL_WHITELIST", "").strip()
if _whitelist_env:
    DOMAIN_WHITELIST = {d.strip().lower() for d in _whitelist_env.split(",") if d.strip()}

# Domain blacklist (always blocked regardless of whitelist)
# Set via environment variable: URL_BLACKLIST=evil.com,malware.net
DOMAIN_BLACKLIST: set[str] = set()
_blacklist_env = os.getenv("URL_BLACKLIST", "").strip()
if _blacklist_env:
    DOMAIN_BLACKLIST = {d.strip().lower() for d in _blacklist_env.split(",") if d.strip()}


class SSRFError(Exception):
    """Exception raised when SSRF attempt is detected."""

    pass


def is_ip_blocked(ip_str: str) -> bool:
    """Check if an IP address is in a blocked range.

    Args:
        ip_str: IP address string

    Returns:
        True if IP is blocked, False otherwise
    """
    try:
        ip = ipaddress.ip_address(ip_str)
        for network in BLOCKED_IP_NETWORKS:
            if ip in network:
                return True
        return False
    except ValueError:
        # Invalid IP format
        return False


def is_hostname_blocked(hostname: str) -> bool:
    """Check if a hostname is blocked.

    Args:
        hostname: Hostname to check

    Returns:
        True if hostname is blocked
    """
    hostname_lower = hostname.lower()

    # Check explicit blocklist
    if hostname_lower in BLOCKED_HOSTNAMES:
        return True

    # Check domain blacklist
    if hostname_lower in DOMAIN_BLACKLIST:
        return True

    # Check if it's a subdomain of a blocked domain
    for blocked in DOMAIN_BLACKLIST:
        if hostname_lower.endswith(f".{blocked}"):
            return True

    return False


def resolve_hostname(hostname: str) -> list[str]:
    """Resolve hostname to IP addresses.

    Args:
        hostname: Hostname to resolve

    Returns:
        List of IP address strings

    Raises:
        SSRFError: If hostname cannot be resolved
    """
    try:
        # Use socket to resolve (handles both IPv4 and IPv6)
        results = socket.getaddrinfo(hostname, None, socket.AF_UNSPEC, socket.SOCK_STREAM)
        ips = list({result[4][0] for result in results})
        return ips
    except socket.gaierror as e:
        logger.warning(f"Failed to resolve hostname {hostname}: {e}")
        raise SSRFError(f"Cannot resolve hostname: {hostname}") from e


def validate_url_for_ssrf(url: str, allow_internal: bool = False) -> dict[str, Any]:
    """Validate a URL to prevent SSRF attacks.

    Security checks:
    1. Scheme must be http or https
    2. Hostname must not be in blocklist
    3. Resolved IP must not be in private/internal ranges
    4. If whitelist is set, hostname must be in whitelist
    5. Hostname must not be in blacklist

    Args:
        url: URL to validate
        allow_internal: If True, skip internal IP checks (for internal tools only)

    Returns:
        Dict with validation results:
        - valid: bool
        - url: str (normalized URL)
        - hostname: str
        - resolved_ips: list[str]
        - error: str | None

    Raises:
        SSRFError: If URL is potentially malicious
    """
    result: dict[str, Any] = {
        "valid": False,
        "url": url,
        "hostname": None,
        "resolved_ips": [],
        "error": None,
    }

    # Parse URL
    try:
        parsed = urlparse(url)
    except Exception as e:
        result["error"] = f"Invalid URL format: {e}"
        raise SSRFError(result["error"]) from e

    # Check scheme
    if parsed.scheme not in ALLOWED_SCHEMES:
        result["error"] = f"Blocked scheme: {parsed.scheme}"
        raise SSRFError(result["error"])

    # Get hostname
    hostname = parsed.hostname
    if not hostname:
        result["error"] = "No hostname in URL"
        raise SSRFError(result["error"])

    result["hostname"] = hostname

    # Check hostname blocklist
    if is_hostname_blocked(hostname):
        result["error"] = f"Blocked hostname: {hostname}"
        logger.warning(f"SSRF attempt blocked: {url} (blocked hostname)")
        raise SSRFError(result["error"])

    # Check domain whitelist (if configured)
    if DOMAIN_WHITELIST is not None:
        hostname_lower = hostname.lower()
        allowed = hostname_lower in DOMAIN_WHITELIST
        if not allowed:
            # Check subdomains
            for allowed_domain in DOMAIN_WHITELIST:
                if hostname_lower.endswith(f".{allowed_domain}"):
                    allowed = True
                    break
        if not allowed:
            result["error"] = f"Domain not in whitelist: {hostname}"
            logger.warning(f"SSRF attempt blocked: {url} (not in whitelist)")
            raise SSRFError(result["error"])

    # Skip IP resolution checks if explicitly allowed
    if allow_internal:
        result["valid"] = True
        return result

    # Check if hostname is already an IP
    try:
        ip = ipaddress.ip_address(hostname)
        if is_ip_blocked(str(ip)):
            result["error"] = f"Blocked IP address: {hostname}"
            logger.warning(f"SSRF attempt blocked: {url} (blocked IP)")
            raise SSRFError(result["error"])
        result["resolved_ips"] = [str(ip)]
        result["valid"] = True
        return result
    except ValueError:
        # Not an IP, continue with DNS resolution
        pass

    # Resolve hostname and check all IPs
    try:
        ips = resolve_hostname(hostname)
        result["resolved_ips"] = ips

        for ip_str in ips:
            if is_ip_blocked(ip_str):
                result["error"] = f"Hostname resolves to blocked IP: {ip_str}"
                logger.warning(
                    f"SSRF attempt blocked: {url} (resolves to {ip_str})"
                )
                raise SSRFError(result["error"])

        result["valid"] = True
        return result

    except SSRFError:
        raise
    except Exception as e:
        result["error"] = f"DNS resolution failed: {e}"
        raise SSRFError(result["error"]) from e


def validate_file_path(path: str, allowed_base: str | None = None) -> str:
    """Validate a file path to prevent path traversal attacks.

    Args:
        path: Path to validate
        allowed_base: If set, path must be under this directory

    Returns:
        Normalized absolute path

    Raises:
        ValueError: If path is invalid or attempts traversal
    """
    import os.path

    # Normalize path
    normalized = os.path.normpath(path)

    # Check for traversal patterns
    if ".." in normalized:
        raise ValueError(f"Path traversal attempt detected: {path}")

    # If allowed_base is set, ensure path is under it
    if allowed_base:
        base = os.path.normpath(os.path.abspath(allowed_base))
        full_path = os.path.normpath(os.path.abspath(path))

        # Use commonpath to check if path is under base
        try:
            common = os.path.commonpath([base, full_path])
            if common != base:
                raise ValueError(f"Path escapes allowed directory: {path}")
        except ValueError as e:
            # commonpath raises ValueError if paths are on different drives (Windows)
            raise ValueError(f"Invalid path: {path}") from e

    return normalized
