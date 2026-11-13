"""IOC extraction, syntax validation, and classification engine for FinGuard AI."""

from __future__ import annotations

import ipaddress
import re
from typing import Dict, List, Optional
from urllib.parse import urlparse

from threat_intel.models import IOCType

# Standard regex patterns
MD5_REGEX = re.compile(r"^[a-fA-F0-9]{32}$")
SHA1_REGEX = re.compile(r"^[a-fA-F0-9]{40}$")
SHA256_REGEX = re.compile(r"^[a-fA-F0-9]{64}$")
IPV4_REGEX = re.compile(r"^(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$")
DOMAIN_REGEX = re.compile(r"^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$")

# Extraction regexes from unstructured text
TEXT_SHA256 = re.compile(r"\b[a-fA-F0-9]{64}\b")
TEXT_SHA1 = re.compile(r"\b[a-fA-F0-9]{40}\b")
TEXT_MD5 = re.compile(r"\b[a-fA-F0-9]{32}\b")
TEXT_IPV4 = re.compile(r"\b(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\b")
TEXT_URL = re.compile(r"\bhttps?://[^\s/$.?#].[^\s]*\b", re.IGNORECASE)
TEXT_DOMAIN = re.compile(r"\b(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}\b")


class IOCExtractor:
    """Extracts, classifies, and validates atomic indicators of compromise."""

    @classmethod
    def classify_and_validate(cls, value: str) -> Optional[IOCType]:
        """Identifies the IOC type of a given string, or returns None if invalid."""
        raw = value.strip()
        if not raw:
            return None

        # 1. Hashes (check by length and hex regex)
        if len(raw) == 64 and SHA256_REGEX.match(raw):
            return IOCType.SHA256
        if len(raw) == 40 and SHA1_REGEX.match(raw):
            return IOCType.SHA1
        if len(raw) == 32 and MD5_REGEX.match(raw):
            return IOCType.MD5

        # 2. URLs (starts with http:// or https://)
        if raw.lower().startswith(("http://", "https://")):
            try:
                parsed = urlparse(raw)
                if parsed.scheme in ("http", "https") and parsed.netloc:
                    return IOCType.URL
            except Exception:
                pass

        # 3. IPv4 address
        if IPV4_REGEX.match(raw):
            try:
                ip = ipaddress.IPv4Address(raw)
                return IOCType.IPV4
            except ValueError:
                pass

        # 4. Domain
        if DOMAIN_REGEX.match(raw):
            return IOCType.DOMAIN

        return None

    @classmethod
    def normalize_ioc(cls, ioc_type: IOCType, value: str) -> str:
        """Normalizes indicator representation (lowercase, strip trailing slashes)."""
        val = value.strip()
        if ioc_type in (IOCType.MD5, IOCType.SHA1, IOCType.SHA256, IOCType.DOMAIN):
            return val.lower()
        if ioc_type == IOCType.URL:
            # Strip trailing slash for consistency
            return val.rstrip("/")
        if ioc_type == IOCType.IPV4:
            return val
        return val

    @classmethod
    def extract_from_text(cls, text: str) -> Dict[IOCType, List[str]]:
        """Extracts unique indicators from arbitrary raw text (logs, tickets, emails)."""
        results: Dict[IOCType, List[str]] = {
            IOCType.SHA256: [],
            IOCType.SHA1: [],
            IOCType.MD5: [],
            IOCType.URL: [],
            IOCType.IPV4: [],
            IOCType.DOMAIN: [],
        }

        # Hashes
        for match in TEXT_SHA256.findall(text):
            val = match.lower()
            if val not in results[IOCType.SHA256]:
                results[IOCType.SHA256].append(val)

        for match in TEXT_SHA1.findall(text):
            val = match.lower()
            if val not in results[IOCType.SHA1] and val not in results[IOCType.SHA256]:
                results[IOCType.SHA1].append(val)

        for match in TEXT_MD5.findall(text):
            val = match.lower()
            if val not in results[IOCType.MD5] and val not in results[IOCType.SHA256] and val not in results[IOCType.SHA1]:
                results[IOCType.MD5].append(val)

        # URLs
        for match in TEXT_URL.findall(text):
            val = match.rstrip("/")
            if val not in results[IOCType.URL]:
                results[IOCType.URL].append(val)

        # IPv4
        for match in TEXT_IPV4.findall(text):
            try:
                ipaddress.IPv4Address(match)
                if match not in results[IOCType.IPV4]:
                    results[IOCType.IPV4].append(match)
            except ValueError:
                continue

        # Domains (excluding those that are part of extracted URLs or IPs)
        for match in TEXT_DOMAIN.findall(text):
            val = match.lower()
            if val not in results[IOCType.DOMAIN] and not IPV4_REGEX.match(val):
                results[IOCType.DOMAIN].append(val)

        return results
