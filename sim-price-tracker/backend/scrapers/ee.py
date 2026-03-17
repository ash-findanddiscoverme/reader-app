import re
import json
import logging
from typing import Optional, List
from bs4 import BeautifulSoup
from .base import BaseScraper, ScrapedPlan
from .playwright_helper import fetch_page_content

logger = logging.getLogger(__name__)


class EEScraper(BaseScraper):
    provider_name = "EE"
    provider_slug = "ee"
    provider_type = "network"
    base_url = "https://shop.ee.co.uk/sim-only"

    async def scrape(self) -> List[ScrapedPlan]:
        plans = []
        urls = [self.base_url, "https://ee.co.uk/mobile/sim-only"]
        for url in urls:
            try:
                html = await fetch_page_content(url, wait_ms=15000)
                if html and len(html) > 5000:
                    found = self._parse_all(html, url)
                    plans.extend(found)
                    logger.info(f"EE: Found {len(found)} from {url}")
            except Exception as e:
                logger.error(f"EE error: {e}")
        return self._dedupe(plans)

    def _parse_all(self, html: str, url: str) -> List[ScrapedPlan]:
        plans = []
        m = re.search(r'<script[^>]*id="__NEXT_DATA__"[^>]>(.*?)</script>', html, re.DOTALL)
        if m:
            try:
                data = json.loads(m.group(1))
                plans.extend(self._walk_json(data, url))
            except: pass
        for m in re.finditer(r'<script[^>]*type="application/ld.json"[^>]>(.*?)</script>', html, re.DOTALL):
            try:
                data = json.loads(m.group(1))
                plans.extend(self._walk_json(data, url))
            except: pass
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ")
        prices = re.findall(r'££](\d+(?:\.\d+)?)\s*(?:/)?(?:mo|pm|month)', text, re.I)
        data_vals = re.findall(r'\d+)\s*GB', text, re.I)
        has_5g = bool(re.search(r'5G', text))
        seen = set()
        data_list = list(data_vals)
        for ps in prices:
            price = float(ps)
            if price < 5 or price > 100 or price in seen: continue
            seen.add(price)
            gb = None
            for d in data_list:
                v = int(d)
                if 1 <= v <= 500:
                    gb = v
                    data_list.remove(d)
                    break
            name = f"EE {gb}GB" if gb else "EE Plan"
            plans.append(ScrapedPlan(name=name, price=price, data_gb=gb, data_unlimited=(gb is None), contract_months=24, url=url, is_5g=has_5g, external_id=f"ee_{price}_{gb or 0}"))
        return plans

    def _walk_json(self, data, url: str, depth=0) -> List[ScrapedPlan]:
        if depth > 10: return []
        plans = []
        if isinstance(data, dict):
            price = None
            for k in ('price', 'monthlyPrice', 'monthlyCost', 'cost'):
                if k in data:
                    try:
                        price = float(str(data[k]).replace('£', '').replace('£', ''))
                        if 0 < price < 200: break
                    except: pass
            if price and 0 < price < 200:
                gb = None
                unlimited = False
                for k in ('data', 'dataAllowance', 'dataGb'):
                    if k in data:
                        val = str(data[k]).lower()
                        if 'unlimited' in val: unlimited = True
                        else:
                            m = re.search(r'(\d+)', val)
                            if m: gb = int(m.group(1))
                        break
                is5g = any('5g' in str(v).lower() for v in data.values() if isinstance(v, str))
                name = data.get('name', f"EE {gb}GB" if gb else "EE Unlimited" if unlimited else "EE Plan")
                plans.append(ScrapedPlan(name=name, price=price, data_gb=gb if not unlimited else None, data_unlimited=unlimited, contract_months=24, url=url, is_5g=is5g, external_id=f"ee_json_{price}_{gb or 0}"))
            for v in data.values():
                plans.extend(self._walk_json(v, url, depth+1))
        elif isinstance(data, list):
            for item in data:
                plans.extend(self._walk_json(item, url, depth+1))
        return plans

    def _dedupe(self, plans: List[ScrapedPlan]) -> List[ScrapedPlan]:
        seen = set()
        out = []
        for p in plans:
            k = (p.price, p.data_gb)
            if k not in seen:
                seen.add(k)
                out.append(p)
        return out
