import re
import json
import logging
from typing import List
from bs4 import BeautifulSoup
from .base import BaseScraper, ScrapedPlan
from .playwright_helper import fetch_page_content

logger = logging.getLogger(__name__)

class IDMobileScraper(BaseScraper):
    provider_name = "iD Mobile"
    provider_slug = "id_mobile"
    provider_type = "mvno"
    base_url = "https://www.idmobile.co.uk/sim-only"
    urls = ["https://www.idmobile.co.uk/sim-only", "https://www.idmobile.co.uk/"]

    async def scrape(self) -> List[ScrapedPlan]:
        plans = []
        for url in self.urls:
            try:
                try:
                    resp = await self.session.get(url)
                    html = resp.text
                    if len(html) > 5000:
                        found = self._parse(html, url)
                        if found:
                            plans.extend(found)
                            logger.info(f"iD Mobile: Found {len(found)} via httpx")
                except Exception: pass
                if len(plans) < 3:
                    html = await fetch_page_content(url, wait_ms=15000)
                    if html and len(html) > 5000:
                        found = self._parse(html, url)
                        plans.extend(found)
                        logger.info(f"iD Mobile: Found {len(found)} via Playwright")
            except Exception as e:
                logger.error(f"iD Mobile error: {e}")
        return self._dedupe(plans)

    def _parse(self, html: str, url: str) -> List[ScrapedPlan]:
        plans = []
        patterns = [r'<script[^>]*id="__NEXT_DATA__"[^>]*>(.*?)</script>', r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>']
        for pat in patterns:
            for m in re.finditer(pat, html, re.DOTALL):
                try:
                    data = json.loads(m.group(1))
                    plans.extend(self._walk_json(data, url))
                except: pass
        soup = BeautifulSoup(html, "html.parser")
        text = soup.get_text(" ")
        prices = re.findall(r'[££](\d+(?:\.\d+)?)\s*(?:/)?(?:mo|pm|month)?', text, re.I)
        data_vals = re.findall(r'(\d+)\s*GB', text, re.I)
        has_5g = bool(re.search(r'5G', text))
        seen = set()
        data_list = list(data_vals)
        for ps in prices:
            try: price = float(ps)
            except: continue
            if price < 5 or price > 100 or price in seen: continue
            seen.add(price)
            gb = None
            for d in data_list:
                v = int(d)
                if 1 <= v <= 500: gb = v; data_list.remove(d); break
            name = f"iD Mobile {gb}GB" if gb else "iD Mobile Plan"
            ext_id = f"id_mobile_{price}_{gb or 0}"
            plans.append(ScrapedPlan(name=name, price=price, data_gb=gb, data_unlimited=(gb is None), contract_months=1, url=url, is_5g=has_5g, external_id=ext_id))
        return plans

    def _walk_json(self, data, url: str, depth=0) -> List[ScrapedPlan]:
        if depth > 10: return []
        plans = []
        if isinstance(data, dict):
            price = None
            for k in ('price', 'monthlyPrice', 'monthlyCost', 'cost'):
                if k in data:
                    try:
                        val = str(data[k]).replace('£', '').replace('£', '').replace('£', '')
                        price = float(val)
                        if 0 < price < 200: break
                    except: pass
            if price and 0 < price < 200:
                gb = None
                unlim = False
                for k in ('data', 'dataAllowance', 'dataGb'):
                    if k in data:
                        val = str(data[k]).lower()
                        if 'unlimited' in val: unlim = True
                        else:
                            mt = re.search(r'(\d+)', val)
                            if mt: gb = int(mt.group(1))
                        break
                is5g = any('5g' in str(v).lower() for v in data.values() if isinstance(v, str))
                pname = data.get('name', f"iD Mobile {gb}GB" if gb else "iD Mobile Unlimited" if unlim else "iD Mobile Plan")
                ext_id = f"id_mobile_json_{price}_{gb or 0}"
                plans.append(ScrapedPlan(name=pname, price=price, data_gb=gb if not unlim else None, data_unlimited=unlim, contract_months=1, url=url, is_5g=is5g, external_id=ext_id))
            for v in data.values(): plans.extend(self._walk_json(v, url, depth+1))
        elif isinstance(data, list):
            for item in data: plans.extend(self._walk_json(item, url, depth+1))
        return plans

    def _dedupe(self, plans: List[ScrapedPlan]) -> List[ScrapedPlan]:
        seen = set()
        out = []
        for p in plans:
            k = (p.price, p.data_gb)
            if k not in seen: seen.add(k); out.append(p)
        return out
