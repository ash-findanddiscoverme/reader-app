import asyncio
import logging
from datetime import datetime
from typing import List, Optional
import hashlib

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from ..db.database import init_db, async_session
from ..db.models import Provider, Plan, PriceSnapshot
from ..scrapers.base import ScrapedPlan
from ..scrapers import SCRAPERS
from sqlalchemy import select
from sqlalchemy.orm import selectinload

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="SIM Price Tracker API")

import os
from fastapi.staticfiles import StaticFiles
_static_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "static")
if os.path.isdir(_static_dir):
    from fastapi.responses import FileResponse

    @app.get("/")
    async def serve_index():
        return FileResponse(os.path.join(_static_dir, "index.html"))

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ScrapeLogManager:
    def __init__(self):
        self.connections: List[WebSocket] = []
        self.is_scraping = False

    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.connections.append(ws)

    def disconnect(self, ws: WebSocket):
        if ws in self.connections:
            self.connections.remove(ws)

    async def broadcast(self, msg: dict):
        for c in self.connections[:]:
            try:
                await c.send_json(msg)
            except:
                self.disconnect(c)


log_manager = ScrapeLogManager()


@app.on_event("startup")
async def startup():
    await init_db()
    logger.info("Database initialized")


def _extract_source(url):
    if not url:
        return "Unknown"
    import re
    m = re.search(r'https?://(?:www\.)?([^/]+)', url)
    if m:
        domain = m.group(1)
        names = {
            "ee.co.uk": "EE", "three.co.uk": "Three",
            "vodafone.co.uk": "Vodafone", "o2.co.uk": "O2",
            "giffgaff.com": "giffgaff", "voxi.co.uk": "VOXI",
            "tescomobile.com": "Tesco Mobile", "mobile.asda.com": "Asda Mobile",
            "idmobile.co.uk": "iD Mobile", "lycamobile.co.uk": "Lyca Mobile",
            "talkmobile.co.uk": "Talkmobile",
            "uswitch.com": "uSwitch", "moneysupermarket.com": "MoneySupermarket",
            "moneysavingexpert.com": "MoneySavingExpert",
            "mobilephonesdirect.co.uk": "Mobile Phones Direct",
            "carphonewarehouse.com": "Carphone Warehouse",
            "currys.co.uk": "Currys",
        }
        for k, v in names.items():
            if k in domain:
                return v
        return domain
    return "Unknown"


@app.get("/api/plans")
async def get_plans(scrape_date: Optional[str] = None):
    async with async_session() as session:
        query = select(Plan).options(selectinload(Plan.provider), selectinload(Plan.price_snapshots))
        result = await session.execute(query)
        plans = result.scalars().all()
        return [{
            "id": p.id,
            "name": p.name,
            "provider_name": p.provider.name if p.provider else "Unknown",
            "provider_type": p.provider.provider_type if p.provider else "unknown",
            "source_site": _extract_source(p.url),
            "data_gb": -1 if p.data_unlimited else (p.data_gb or 0),
            "price": p.current_price if p.current_price is not None else 0.0,
            "contract_length": p.contract_months or 1,
            "is_5g": p.is_5g,
            "extras": p.extras or "",
            "url": p.url,
            "last_updated": p.last_seen.isoformat() if p.last_seen else None
        } for p in plans]


@app.get("/api/scrape-runs")
async def get_scrape_runs():
    return []


@app.get("/api/price-history")
async def get_price_history(plan_id: Optional[int] = None, provider: Optional[str] = None):
    return []


@app.post("/api/scrape/trigger")
async def trigger_scrape():
    if log_manager.is_scraping:
        return {"status": "already_running"}
    asyncio.create_task(run_scrape())
    return {"status": "started"}


def _generate_external_id(sp: ScrapedPlan, provider_slug: str) -> str:
    """Generate a unique external_id if not provided."""
    if sp.external_id:
        return sp.external_id
    # Create a hash-based ID from the plan attributes
    data_str = "unl" if sp.data_unlimited else str(sp.data_gb or 0)
    unique_str = f"{provider_slug}_{sp.price}_{data_str}_{sp.contract_months}m_{sp.name}"
    return hashlib.md5(unique_str.encode()).hexdigest()[:16]


async def save_plans(session, provider: Provider, plans: List[ScrapedPlan]):
    """Save scraped plans to the database."""
    saved_count = 0
    for sp in plans:
        try:
            # Generate external_id if not provided
            ext_id = _generate_external_id(sp, provider.slug)
            
            # Look up existing plan
            query = select(Plan).where(Plan.external_id == ext_id)
            result = await session.execute(query)
            plan = result.scalar()

            if not plan:
                plan = Plan(
                    provider_id=provider.id,
                    name=sp.name,
                    url=sp.url,
                    data_gb=sp.data_gb,
                    data_unlimited=sp.data_unlimited,
                    contract_months=sp.contract_months,
                    is_5g=sp.is_5g,
                    minutes=sp.minutes,
                    texts=sp.texts,
                    external_id=ext_id,
                    extras=getattr(sp, 'extras', None),
                )
                session.add(plan)
                await session.flush()
            else:
                # Update existing plan
                plan.last_seen = datetime.utcnow()
                plan.name = sp.name
                plan.url = sp.url
                plan.is_5g = sp.is_5g
                if hasattr(sp, 'extras') and sp.extras:
                    plan.extras = sp.extras

            # Add price snapshot
            snapshot = PriceSnapshot(plan_id=plan.id, price=sp.price)
            session.add(snapshot)
            saved_count += 1
        except Exception as e:
            logger.error(f"Error saving plan {sp.name}: {e}")
            continue

    await session.commit()
    return saved_count


async def get_or_create_provider(session, name: str, slug: str, ptype: str) -> Provider:
    query = select(Provider).where(Provider.slug == slug)
    result = await session.execute(query)
    provider = result.scalar()
    if not provider:
        provider = Provider(name=name, slug=slug, provider_type=ptype)
        session.add(provider)
        await session.flush()
    return provider


async def scrape_single_provider(ScraperClass):
    """Scrape a single provider and return results."""
    scraper = ScraperClass()
    try:
        async with scraper:
            plans = await scraper.scrape()
        return {
            "scraper": scraper,
            "plans": plans,
            "error": None
        }
    except Exception as e:
        logger.error(f"Error scraping {scraper.provider_name}: {e}")
        return {
            "scraper": scraper,
            "plans": [],
            "error": str(e)
        }


async def run_scrape():
    """Run all scrapers in parallel batches."""
    log_manager.is_scraping = True
    provider_names = [scl.provider_name for scl in SCRAPESS]

    await log_manager.broadcast({
        "type": "progress",
        "status": "started",
        "total": len(SCRAPERS),
        "completed": 0,
        "plans_found": 0,
        "provider_list": provider_names
    })

    total_plans = 0
    completed = 0

    # Run scrapers in parallel batches of 4
    batch_size = 4
    for i in range(0, len(SCRAPERS), batch_size):
        batch = SCRAPERS[i:i + batch_size]
        
        # Notify start of batch
        for ScraperClass in batch:
            await log_manager.broadcast({"type": "provider_start", "provider": ScraperClass.provider_name})
            await log_manager.broadcast({"type": "log", "message": f"Scraping {ScraperClass.provider_name}...", "level": "info"})
        
        # Run batch in parallel
        results = await asyncio.gather(*[scrape_single_provider(sc) for sc in batch])
        
        # Process results
        for result in results:
            scraper = result["scraper"]
            plans = result["plans"]
            error = result["error"]
            
            if error:
                await log_manager.broadcast({"type": "provider_complete", "provider": scraper.provider_name, "error": error})
                await log_manager.broadcast({"type": "log", "message": f"{scraper.provider_name}: Error - {error}", "level": "error"})
            else:
                # Save to database
                try:
                    async with async_session() as session:
                        provider = await get_or_create_provider(
                            session,
                            scraper.provider_name,
                            scraper.provider_slug,
                            scraper.provider_type
                        )
                        saved = await save_plans(session, provider, plans)
                    logger.info(f"{\craper.provider_name}: Saved {saved} plans")
                except Exception as e:
                    logger.error(f"Error saving plans for {scraper.provider_name}: {e}")
                
                plans_found = len(plans)
                total_plans += plans_found
                await log_manager.broadcast({"type": "provider_complete", "provider": scraper.provider_name, "plans_found": plans_found})
                await log_manager.broadcast({"type": "log", "message": f"{scraper.provider_name}: Found {plans_found} plans", "level": "success"})
            
            completed += 1
            await log_manager.broadcast({
                "type": "progress",
                "status": "running",
                "total": len(SCRAPERS),
                "completed": completed,
                "plans_found": total_plans
            })

    await log_manager.broadcast({
        "type": "progress",
        "status": "completed",
        "total": len(SCRAPERS),
        "completed": len(SCRAPERS),
        "plans_found": total_plans
    })

    log_manager.is_scraping = False


@app.websocket("/api/scrape/logs")
async def websocket_logs(ws: WebSocket):
    await log_manager.connect(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        log_manager.disconnect(ws)


if os.path.isdir(_static_dir):
    from fastapi.responses import FileResponse as _FR

    @app.get("/crawl-log.html")
    async def serve_crawl():
        return _FR(os.path.join(_static_dir, "crawl-log.html"))

    @app.get("/index.html")
    async def serve_idx():
        return _FR(os.path.join(_static_dir, "index.html"))
