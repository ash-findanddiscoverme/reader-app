from .base import BaseScraper, ScrapedPlan

# MNOs
from .ee import EEScraper
from .three import ThreeScraper
from .vodafone import VodafoneScraper
from .o2 import O2Scraper

# MVNOs
from .giffgaff import GiffgaffScraper
from .voxi import VOXIScraper
from .tesco_mobile import TescoMobileScraper
from .asda_mobile import AsdaMobileScraper
from .id_mobile import IDMobileScraper
from .lyca_mobile import LycaMobileScraper
from .talkmobile import TalkmobileScraper

# Affiliates
from .uswitch import USwitchScraper
from .moneysupermarket import MoneySupermarketScraper
from .moneysavingexpert import MoneySavingExpertScraper
from .mobilephonesdirect import MobilePhonesDirectScraper
from .carphonewarehouse import CarphoneWarehouseScraper

SCRAPERS = [
    # MNOs
    EEScraper,
    ThreeScraper,
    VodafoneScraper,
    O2Scraper,
    # MVNOs
    GiffgaffScraper,
    VOXIScraper,
    TescoMobileScraper,
    AsdaMobileScraper,
    IDMobileScraper,
    LycaMobileScraper,
    TalkmobileScraper,
    # Affiliates
    USwitchScraper,
    MoneySupermarketScraper,
    MoneySavingExpertScraper,
    MobilePhonesDirectScraper,
    CarphoneWarehouseScraper,
]
