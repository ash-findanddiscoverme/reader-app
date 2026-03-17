from dataclasses import dataclass, field
from typing import List, Optional
import httpx
import logging

logger = logging.getLogger(__name__)

@dataclass
class ScrapedPlan:
    name: str
    price: float
    data_gb: Optional[int] = None
    data_unlimited: bool = False
    contract_months: int = 1
    url: str = ""
    is_5g: bool = False
    minutes: str = "unlimited"
    texts: str = "unlimited"
    external_id: Optional[str] = None
    extras: Optional[str] = None
    network: Optional[str] = None  # The actual network provider (EE, Three, etc.)


class BaseScraper:
    provider_name: str = "Unknown"
    provider_slug: str = "unknown"
    provider_type: str = "network"
    base_url: str = ""

    def __init__(self):
        self.session: Optional[httpx.AsyncClient] = None

    async def __aenter__(self):
        self.session = httpx.AsyncClient(
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,*/*;q=0.8",
                "Accept-Language": "en-GB,en-US;q=0.9,en;q=0.8",
                "Accept-Encoding": "gzip, deflate, br",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1",
                "Cache-Control": "max-age=0",
            },
            timeout=45.0,
            follow_redirects=True,
            verify=False,
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            await self.session.aclose()

    async def scrape(self) -> List[ScrapedPlan]:
        raise NotImplementedError("Subclasses must implement scrape()")

    def generate_external_id(self, price: float, data_gb: Optional[int], contract: int = 1, suffix: str = "") -> str:
        """Generate a unique external_id for a plan."""
        data_str = "unl" if data_gb is None else str(data_gb)
        base_id = f"{self.provider_slug}_{price}_{data_str}_{contract}m"
        if suffix:
            base_id += f"_{suffix}"
        return base_id
