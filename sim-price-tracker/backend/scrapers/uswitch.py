import re
import json
import logging
from typing import List
from .base import BaseScraper, ScrapedPlan
from .playwright_helper import fetch_page_content

logger = logging.getLogger(__name__)

NETWORKS = ["EE", "Three", "O2", "Vodafone", "giffgaff", "VOXI", "iD Mobile", "Tesco Mobile", "Lyca Mobile", "Smarty"]

class USwitchScraper(BaseScraper):
    provider_name = "uSwitch"
    provider_slug = "uswitch"
    provider_type = "affiliate"
    base_url = "https://www.uswitch.com/mobiles/compare/sim_only_deals/"

    async def scrape(self) -> List[ScrapedPlan]:
        plans = []
        try:
            # Try httpx first
            resp = await self.session.get(self.base_url)
            html = resp.text
            if len(html) > 5000:
                plans = self._parse(html)
            
            # Fallback to Playwright
            if len(plans) < 5:
                html = await fetch_page_content(self.base_url, wait_ms=15000)
                if html:
                    plans.extend(self._parse(html))
            
            logger.info(f"uSwitch: Found {len(plans)} plans")
        except Exception as e:
            logger.error(f"uSwitch error: {e}")
        return self._dedupe(plans)

    def _parse(self, html: str) -> List[ScrapedPlan]:
        plans = []
        # Try JSON first
        for pat in [r'<script[^>]*id="__NEXT_DATA__"[^]*>(.*?)</script>', r'window\.__ssrState__\s*=\s*(\{.*?\});']:
            m = re.search(pat, html, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(1))
                    plans.extend(self._walk_json(data))
                except: pass
        
        # Regex fallback
        for m in re.finditer(r'££](\d+(?:\.\d+)?)\s*(?:/)?(?:mo|pm|month).{0,500}?(\d+)\s*GB', html, re.I|re.DOTALL):
            try:
                price = float(m.group(1))
                gb = int(m.group(2))
                if 5 < price < 100 and 1 <= gb <= 500:
                    ctx = html[max(o,m.start()-500):m.end()+200]
                    net = self._find_net(ctx)
                    name = f"{net} {gb}GB" if net else f"{gb}GB SIM"
                    plans.append(ScrapedPlan(name=name, price=price, data_gb=gb, url=self.base_url, is_5g='5g' in ctx.lower(), external_id=f"usw_{price}_{gb}"))
            except: pass
        return plans

    def _walk_json(self, data, depth=0) -> List[ScrapedPlan]:
        if depth > 10: return []
        plans = []
        if isinstance(data, dict):
            price = None
            for k in ('monthlyCost', 'price', 'monthlyPrice'):
                if k in data:
                    try:
                        price = float(str(data[k]).replace('£', '').replace('£', ''))
                        if 0 < price < 200: break
                    except: pass
            if price and 0 < price < 200:
                gb = None
                unlim = False
                for k in ('data', 'dataAllowance', 'allowance'):
                    if k in data:
                        val = str(data[k]).lower()
                        if 'unlimited' in val: unlim = True
                        else:
                            mt = re.search(r'(\d+)', val)
                            if mt: gb = int(mt.group(1))
                        break
                net = data.get('network', data.get('provider', ''))
                name = f"{net} {gb}GB" if net and gb else f"{n} Unlimited" if net and unlim else f"{n}GB SIM" if gb else "SIM Only"
                plans.append(ScrapedPlan(name=name, price=price, data_gb=gb, data_unlimited=unlim, url=self.base_url, is_5g=any('5g' in str(v).lower() for v in data.values() if isinstance(v, str)), external_id=f"usw_{price}_{gb or 0}"))
            for v in data.values():
                plans.extend(self._walk_json(v, depth+1))
        elif isinstance(data, list):
            for item in data:
                plans.extend(self._walk_json(item, depth+1))
        return plans

    def _find_net(self, txt: str) -> str:
        txtl = txt.lower()
        for n in NETWORKS:
            if n.lower() in txtl: return n
        return ''

    def _dedupe(self, plans: List[ScrapedPlan]) -> List[ScrapedPlan]:
        seen = set()
        out = []
        for p in plans:
            k = (p.price, p.data_gb)
            if k not in seen:
                seen.add(k)
                out.append(p)
        return out
