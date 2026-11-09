"""News Ingestion Pipeline - Multi-source news aggregation and processing."""

import asyncio
import logging
import hashlib
import re
from dataclasses import dataclass, field
from datetime import datetime, date, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Optional, Callable, Tuple
from enum import Enum
from typing import TYPE_CHECKING
from collections import deque
import feedparser
import asyncio

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class NewsCategory(str, Enum):
    MARKETS = "MARKETS"
    ECONOMY = "ECONOMY"
    COMPANIES = "COMPANIES"
    SECTORS = "SECTORS"
    CRYPTO = "CRYPTO"
    FOREX = "FOREX"
    COMMODITIES = "COMMODITIES"
    FIXED_INCOME = "FIXED_INCOME"
    EARNINGS = "EARNINGS"
    MERGERS = "MERGERS"
    REGULATION = "REGULATION"
    POLITICS = "POLITICS"
    TECHNOLOGY = "TECHNOLOGY"
    ENERGY = "ENERGY"
    GENERAL = "GENERAL"


class NewsSource(str, Enum):
    REUTERS = "REUTERS"
    BLOOMBERG = "BLOOMBERG"
    WSJ = "WSJ"
    FT = "FT"
    CNBC = "CNBC"
    MARKETWATCH = "MARKETWATCH"
    INVESTING_COM = "INVESTING_COM"
    SEEKING_ALPHA = "SEEKING_ALPHA"
    YAHOO_FINANCE = "YAHOO_FINANCE"
    GOOGLE_NEWS = "GOOGLE_NEWS"
    RSS_FEED = "RSS_FEED"
    TWITTER = "TWITTER"
    REDDIT = "REDDIT"
    CUSTOM = "CUSTOM"


class NewsSentiment(str, Enum):
    VERY_NEGATIVE = "VERY_NEGATIVE"
    NEGATIVE = "NEGATIVE"
    NEUTRAL = "NEUTRAL"
    POSITIVE = "POSITIVE"
    VERY_POSITIVE = "VERY_POSITIVE"


@dataclass
class NewsArticle:
    """News article with metadata."""
    
    # Identity
    id: str = ""
    source: NewsSource = NewsSource.CUSTOM
    source_id: str = ""  # Source-specific ID
    
    # Content
    title: str = ""
    summary: str = ""
    content: str = ""
    url: str = ""
    
    # Metadata
    author: str = ""
    published_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None
    language: str = "en"
    
    # Classification
    categories: List[NewsCategory] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    
    # Entities
    entities: List[Dict] = field(default_factory=list)  # {type, name, relevance, sentiment}
    tickers: List[str] = field(default_factory=list)
    
    # Sentiment
    sentiment: NewsSentiment = NewsSentiment.NEUTRAL
    sentiment_score: Decimal = Decimal('0')  # -1 to 1
    confidence: Decimal = Decimal('0')
    
    # Relevance
    relevance_score: Decimal = Decimal('0')  # 0 to 1
    market_relevance: Dict[str, Decimal] = field(default_factory=dict)  # symbol -> relevance
    
    # Engagement
    view_count: int = 0
    share_count: int = 0
    comment_count: int = 0
    
    # Processing
    hash: str = ""  # Content hash for deduplication
    processed_at: datetime = field(default_factory=datetime.utcnow)
    raw_data: Dict = field(default_factory=dict)
    
    def compute_hash(self) -> str:
        """Compute content hash for deduplication."""
        content = f"{self.title}{self.summary}{self.url}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]
    
    @property
    def is_high_relevance(self) -> bool:
        return self.relevance_score >= Decimal('0.7')
    
    @property
    def has_tickers(self) -> bool:
        return len(self.tickers) > 0


@dataclass
class NewsFilter:
    """Filter for querying news."""
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    sources: List[NewsSource] = field(default_factory=list)
    categories: List[NewsCategory] = field(default_factory=list)
    sentiments: List[NewsSentiment] = field(default_factory=list)
    tickers: List[str] = field(default_factory=list)
    keywords: List[str] = field(default_factory=list)
    min_relevance: Decimal = Decimal('0')
    languages: List[str] = field(default_factory=list)
    min_confidence: Decimal = Decimal('0')


class NewsIngestionPipeline:
    """Pipeline for ingesting, processing, and storing news."""
    
    def __init__(self):
        self._articles: Dict[str, NewsArticle] = {}
        self._by_ticker: Dict[str, List[str]] = {}  # ticker -> article_ids
        self._by_category: Dict[NewsCategory, List[str]] = {}
        self._by_source: Dict[NewsSource, List[str]] = {}
        self._by_date: Dict[date, List[str]] = {}
        
        # Deduplication
        self._hash_index: Dict[str, str] = {}  # hash -> article_id
        
        # Processing pipeline
        self._extractors: List[Callable] = []
        self._classifiers: List[Callable] = []
        self._sentiment_analyzers: List[Callable] = []
        self._relevance_scorers: List[Callable] = []
        
        # Callbacks
        self._callbacks: List[Callable] = []
        
        # Queue
        self._queue: asyncio.Queue = asyncio.Queue()
        self._workers: List[asyncio.Task] = []
        self._running = False
    
    def register_extractor(self, extractor: Callable):
        self._extractors.append(extractor)
    
    def register_classifier(self, classifier: Callable):
        self._classifiers.append(classifier)
    
    def register_sentiment_analyzer(self, analyzer: Callable):
        self._sentiment_analyzers.append(analyzer)
    
    def register_relevance_scorer(self, scorer: Callable):
        self._relevance_scorers.append(scorer)
    
    def register_callback(self, callback: Callable):
        self._callbacks.append(callback)
    
    async def start(self, num_workers: int = 4):
        """Start processing workers."""
        self._running = True
        for i in range(num_workers):
            task = asyncio.create_task(self._worker(f"worker-{i}"))
            self._workers.append(task)
    
    async def stop(self):
        self._running = False
        for worker in self._workers:
            worker.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)
    
    async def ingest_article(self, article: NewsArticle) -> Optional[str]:
        """Ingest a single article."""
        # Compute hash
        article.hash = article.compute_hash()
        
        # Check for duplicate
        if article.hash in self._hash_index:
            existing_id = self._hash_index[article.hash]
            return existing_id
        
        # Add to queue
        await self._queue.put(article)
        return article.id
    
    async def ingest_batch(self, articles: List[NewsArticle]) -> List[str]:
        """Ingest multiple articles."""
        ids = []
        for article in articles:
            aid = await self.ingest_article(article)
            if aid:
                ids.append(aid)
        return ids
    
    async def _worker(self, name: str):
        while True:
            try:
                article = await self._queue.get()
                await self._process_article(article)
                self._queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Worker {name} error: {e}")
    
    async def _process_article(self, article: NewsArticle):
        """Process article through pipeline."""
        try:
            # Run extractors
            for extractor in self._extractors:
                try:
                    await extractor(article)
                except Exception as e:
                    logger.warning(f"Extractor error: {e}")
            
            # Run classifiers
            for classifier in self._classifiers:
                try:
                    await classifier(article)
                except Exception as e:
                    logger.warning(f"Classifier error: {e}")
            
            # Run sentiment analyzers
            for analyzer in self._sentiment_analyzers:
                try:
                    await analyzer(article)
                except Exception as e:
                    logger.warning(f"Sentiment analyzer error: {e}")
            
            # Run relevance scorers
            for scorer in self._relevance_scorers:
                try:
                    await scorer(article)
                except Exception as e:
                    logger.warning(f"Relevance scorer error: {e}")
            
            # Store article
            self._store_article(article)
            
            # Notify callbacks
            for callback in self._callbacks:
                try:
                    await callback(article)
                except Exception as e:
                    logger.warning(f"Callback error: {e}")
                    
        except Exception as e:
            logger.error(f"Article processing error: {e}")
    
    def _store_article(self, article: NewsArticle):
        """Store article in indexes."""
        self._articles[article.id] = article
        self._hash_index[article.hash] = article.id
        
        # Index by ticker
        for ticker in article.tickers:
            if ticker not in self._by_ticker:
                self._by_ticker[ticker] = []
            self._by_ticker[ticker].append(article.id)
        
        # Index by category
        for cat in article.categories:
            if cat not in self._by_category:
                self._by_category[cat] = []
            self._by_category[cat].append(article.id)
        
        # Index by source
        if article.source not in self._by_source:
            self._by_source[article.source] = []
        self._by_source[article.source].append(article.id)
        
        # Index by date
        pub_date = article.published_at.date()
        if pub_date not in self._by_date:
            self._by_date[pub_date] = []
        self._by_date[pub_date].append(article.id)
    
    def get_article(self, article_id: str) -> Optional[NewsArticle]:
        return self._articles.get(article_id)
    
    def get_articles(
        self,
        filter: NewsFilter = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[NewsArticle]:
        results = []
        for article in self._articles.values():
            if filter and not self._matches_filter(article, filter):
                continue
            results.append(article)
        
        results.sort(key=lambda a: a.published_at, reverse=True)
        return results[offset:offset + limit]
    
    def _matches_filter(self, article: NewsArticle, filter: NewsFilter) -> bool:
        if filter.start_date and article.published_at < filter.start_date:
            return False
        if filter.end_date and article.published_at > filter.end_date:
            return False
        if filter.sources and article.source not in filter.sources:
            return False
        if filter.categories and not any(c in article.categories for c in filter.categories):
            return False
        if filter.sentiments and article.sentiment not in filter.sentiments:
            return False
        if filter.tickers and not any(t in article.tickers for t in filter.tickers):
            return False
        if filter.keywords:
            text = f"{article.title} {article.summary} {article.content}".lower()
            if not any(kw.lower() in text for kw in filter.keywords):
                return False
        if article.relevance_score < filter.min_relevance:
            return False
        if filter.languages and article.language not in filter.languages:
            return False
        if article.confidence < filter.min_confidence:
            return False
        return True
    
    def get_articles_by_ticker(
        self,
        ticker: str,
        start_date: datetime = None,
        end_date: datetime = None,
        limit: int = 50
    ) -> List[NewsArticle]:
        article_ids = self._by_ticker.get(ticker.upper(), [])
        articles = []
        for aid in article_ids:
            article = self._articles.get(aid)
            if article:
                if start_date and article.published_at < start_date:
                    continue
                if end_date and article.published_at > end_date:
                    continue
                articles.append(article)
        
        articles.sort(key=lambda a: a.published_at, reverse=True)
        return articles[:limit]
    
    def get_latest_news(
        self,
        tickers: List[str] = None,
        categories: List[NewsCategory] = None,
        hours: int = 24,
        limit: int = 50
    ) -> List[NewsArticle]:
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        filter = NewsFilter(
            start_date=cutoff,
            tickers=tickers,
            categories=categories,
            min_relevance=Decimal('0.3')
        )
        
        return self.get_articles(filter, limit=limit)
    
    def get_trending_topics(self, hours: int = 24, limit: int = 10) -> List[Dict]:
        """Get trending topics/keywords."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        keyword_counts = {}
        ticker_counts = {}
        
        for article in self._articles.values():
            if article.published_at < cutoff:
                continue
            
            for kw in article.keywords:
                keyword_counts[kw] = keyword_counts.get(kw, 0) + 1
            
            for ticker in article.tickers:
                ticker_counts[ticker] = ticker_counts.get(ticker, 0) + 1
        
        trending_keywords = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        trending_tickers = sorted(ticker_counts.items(), key=lambda x: x[1], reverse=True)[:limit]
        
        return {
            'keywords': [{'keyword': k, 'count': c} for k, c in trending_keywords],
            'tickers': [{'ticker': t, 'count': c} for t, c in trending_tickers],
        }
    
    def get_sentiment_summary(self, ticker: str = None, hours: int = 24) -> Dict:
        """Get sentiment summary for ticker or overall."""
        cutoff = datetime.utcnow() - timedelta(hours=hours)
        
        articles = self.get_articles_by_ticker(ticker) if ticker else list(self._articles.values())
        articles = [a for a in articles if a.published_at >= cutoff]
        
        if not articles:
            return {}
        
        sentiments = [a.sentiment_score for a in articles]
        confidences = [a.confidence for a in articles]
        
        # Weight by confidence
        weighted_sentiment = sum(s * c for s, c in zip(sentiments, confidences)) / sum(confidences) if sum(confidences) > 0 else Decimal('0')
        
        sentiment_dist = {}
        for a in articles:
            sentiment_dist[a.sentiment.value] = sentiment_dist.get(a.sentiment.value, 0) + 1
        
        return {
            'article_count': len(articles),
            'avg_sentiment': float(sum(sentiments) / len(sentiments)),
            'weighted_sentiment': float(weighted_sentiment),
            'distribution': sentiment_dist,
            'avg_confidence': float(sum(confidences) / len(confidences)),
        }


class RSSFeedProvider:
    """RSS feed news provider."""
    
    def __init__(self, name: str, feed_urls: List[str], source: NewsSource = NewsSource.RSS_FEED):
        self.name = name
        self.feed_urls = feed_urls
        self.source = source
        self._last_checked: Dict[str, datetime] = {}
    
    async def fetch_articles(self) -> List[NewsArticle]:
        articles = []
        
        for url in self.feed_urls:
            try:
                feed = feedparser.parse(url)
                
                for entry in feed.entries:
                    # Parse date
                    published = datetime.utcnow()
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        published = datetime(*entry.published_parsed[:6])
                    
                    article = NewsArticle(
                        source=self.source,
                        source_id=entry.get('id', entry.get('link', '')),
                        title=entry.get('title', ''),
                        summary=entry.get('summary', ''),
                        content=entry.get('content', [{}])[0].get('value', '') if entry.get('content') else '',
                        url=entry.get('link', ''),
                        author=entry.get('author', ''),
                        published_at=published,
                        language=entry.get('language', 'en'),
                    )
                    article.hash = article.compute_hash()
                    articles.append(article)
                    
            except Exception as e:
                logger.error(f"Error fetching {url}: {e}")
        
        return articles
    
    async def poll(self, interval_seconds: int = 300) -> List[NewsArticle]:
        """Poll feeds for new articles."""
        while True:
            articles = await self.fetch_articles()
            yield articles
            await asyncio.sleep(interval_seconds)


class NewsAPIProvider:
    """Generic News API provider."""
    
    def __init__(self, name: str, api_key: str, base_url: str, source: NewsSource):
        self.name = name
        self.api_key = api_key
        self.base_url = base_url
        self.source = source
    
    async def fetch_latest(
        self,
        query: str = "",
        categories: List[str] = None,
        limit: int = 50
    ) -> List[NewsArticle]:
        # Would implement API call
        return []


class TwitterNewsProvider:
    """Twitter/X news provider."""
    
    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
    
    async def fetch_tweets(
        self,
        query: str,
        max_results: int = 100
    ) -> List[NewsArticle]:
        # Would use Twitter API v2
        return []


class RedditNewsProvider:
    """Reddit news provider."""
    
    def __init__(self, client_id: str, client_secret: str):
        self.client_id = client_id
        self.client_secret = client_secret
    
    async def fetch_posts(
        self,
        subreddits: List[str],
        limit: int = 50
    ) -> List[NewsArticle]:
        # Would use Reddit API
        return []


class NewsAggregator:
    """Aggregate news from multiple sources."""
    
    def __init__(self, pipeline: NewsIngestionPipeline):
        self.pipeline = pipeline
        self.providers: List[Any] = []
    
    def add_provider(self, provider: Any):
        self.providers.append(provider)
    
    async def fetch_all(self) -> List[NewsArticle]:
        all_articles = []
        for provider in self.providers:
            try:
                if hasattr(provider, 'fetch_articles'):
                    articles = await provider.fetch_articles()
                elif hasattr(provider, 'fetch_latest'):
                    articles = await provider.fetch_latest()
                elif hasattr(provider, 'fetch_tweets'):
                    articles = await provider.fetch_tweets()
                elif hasattr(provider, 'fetch_posts'):
                    articles = await provider.fetch_posts()
                else:
                    continue
                
                if articles:
                    await self.pipeline.ingest_batch(articles)
                    all_articles.extend(articles)
            except Exception as e:
                logger.error(f"Provider error: {e}")
        
        return all_articles
    
    async def run_continuous(self, interval_seconds: int = 300):
        """Continuously fetch from all providers."""
        while True:
            try:
                await self.fetch_all()
            except Exception as e:
                logger.error(f"Aggregation error: {e}")
            await asyncio.sleep(interval_seconds)


class NLPProcessor:
    """NLP processing for news articles."""
    
    def __init__(self):
        self._nlp_models: Dict[str, Any] = {}
        self._ticker_pattern = re.compile(r'\b[A-Z]{1,5}\b')
        self._currency_pattern = re.compile(r'\b(USD|EUR|GBP|JPY|CHF|CAD|AUD|CNY)\b')
        self._entity_cache: Dict[str, List[Dict]] = {}
    
    async def extract_entities(self, text: str) -> List[Dict]:
        """Extract named entities from text."""
        # Check cache
        cache_key = hashlib.md5(text.encode()).hexdigest()
        if cache_key in self._entity_cache:
            return self._entity_cache[cache_key]
        
        entities = []
        
        # Extract tickers (simple regex)
        tickers = self._ticker_pattern.findall(text.upper())
        exclude = {'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HIS', 'HOW', 'ITS', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WHO', 'BOY', 'DID', 'OIL', 'SIT', 'USE', 'CEO', 'CFO', 'CTO', 'COO', 'IPO', 'ETF', 'SEC', 'FDA', 'FED', 'GDP', 'CPI', 'PMI', 'EPS', 'ROE', 'ROA', 'YOY', 'QOQ', 'MTM', 'WTD', 'YTD', 'APPLE', 'BEATS', 'STOCK', 'SALES', 'ON', 'BEAT', 'BOTH', 'MISS', 'MISSING', 'ESTIMATES', 'ESTIMATE', 'EXPECTATIONS', 'EXPECTATION', 'REPORT', 'REPORTED', 'REPORTING', 'QUARTER', 'QUARTERLY', 'ANNUAL', 'YEAR', 'YEARS', 'MONTH', 'MONTHS', 'WEEK', 'WEEKS', 'DAY', 'DAYS', 'TODAY', 'YESTERDAY', 'TOMORROW', 'MONDAY', 'TUESDAY', 'WEDNESDAY', 'THURSDAY', 'FRIDAY', 'SATURDAY', 'SUNDAY', 'JANUARY', 'FEBRUARY', 'MARCH', 'APRIL', 'MAY', 'JUNE', 'JULY', 'AUGUST', 'SEPTEMBER', 'OCTOBER', 'NOVEMBER', 'DECEMBER', 'Q1', 'Q2', 'Q3', 'Q4', 'H1', 'H2', 'FY', 'TTM', 'LTM', 'NTM', 'FWD', 'TRAILING', 'FORWARD', 'CONSENSUS', 'ESTIMATE', 'WHISPER', 'GUIDANCE', 'OUTLOOK', 'TARGET', 'PRICE', 'RATING', 'UPGRADE', 'DOWNGRADE', 'INITIATE', 'COVERAGE', 'ANALYST', 'ANALYSTS', 'FIRM', 'BANK', 'BROKER', 'DEALER', 'MARKET', 'STREET', 'WALL', 'MAIN', 'SECTOR', 'INDUSTRY', 'GROUP', 'PEER', 'PEERS', 'COMPETITOR', 'COMPETITORS', 'LEADER', 'LEADERS', 'LAGGARD', 'LAGGARDS', 'WINNER', 'WINNERS', 'LOSER', 'LOSERS', 'GAINER', 'GAINERS', 'DECLINER', 'DECLINERS', 'ACTIVE', 'ACTIVES', 'VOLUME', 'VOLUMES', 'PRICE', 'PRICES', 'VALUE', 'VALUES', 'WORTH', 'COST', 'COSTS', 'EXPENSE', 'EXPENSES', 'REVENUE', 'REVENUES', 'PROFIT', 'PROFITS', 'EARNING', 'EARNINGS', 'INCOME', 'NET', 'GROSS', 'OPERATING', 'MARGIN', 'MARGINS', 'EBITDA', 'EBIT', 'FCF', 'CAPEX', 'DEBT', 'CASH', 'LIQUIDITY', 'SOLVENCY', 'LEVERAGE', 'RATIO', 'RATIOS', 'MULTIPLE', 'MULTIPLES', 'PE', 'PEG', 'PB', 'PS', 'EV', 'EBITDA', 'ROE', 'ROA', 'ROIC', 'WACC', 'CAPM', 'BETA', 'ALPHA', 'SHARPE', 'SORTINO', 'TREYNOR', 'JENSEN', 'INFORMATION', 'RATIO', 'TRACKING', 'ERROR', 'VOLATILITY', 'VAR', 'ES', 'CVAR', 'STRESS', 'TEST', 'SCENARIO', 'MONTE', 'CARLO', 'SIMULATION', 'OPTIMIZATION', 'PORTFOLIO', 'RISK', 'RETURN', 'RETURNS', 'ALPHA', 'BETA', 'CORRELATION', 'COVARIANCE', 'FACTOR', 'FACTORS', 'STYLE', 'MOMENTUM', 'VALUE', 'GROWTH', 'QUALITY', 'SIZE', 'MIN', 'LOW', 'HIGH', 'VOLATILITY', 'SKEW', 'KURTOSIS', 'NORMAL', 'DISTRIBUTION', 'LOG', 'NORMAL', 'STUDENT', 'T', 'GARCH', 'EGARCH', 'TGARCH', 'APARCH', 'FIGARCH', 'FIEGARCH', 'HYGARCH', 'CMGARCH', 'DCC', 'CCC', 'BEKK', 'VECH', 'RISKMETRICS', 'JP', 'MORGAN', 'GOLDMAN', 'SACHS', 'MORGAN', 'STANLEY', 'MERRILL', 'LYNCH', 'DEUTSCHE', 'BANK', 'BARCLAYS', 'CREDIT', 'SUISSE', 'UBS', 'CITI', 'CITIGROUP', 'BOFA', 'AMERICA', 'WELLS', 'FARGO', 'JPMORGAN', 'CHASE', 'MORGAN', 'STANLEY', 'CITI', 'GROUP', 'HSBC', 'STANDARD', 'CHARTERED', 'RBS', 'ROYAL', 'BANK', 'SCOTLAND', 'SANTANDER', 'BBVA', 'ING', 'RABOBANK', 'ABN', 'AMRO', 'COOPERATIEVE', 'NOMURA', 'DAIWA', 'MIZUHO', 'SMBC', 'MUFG', 'SUMITOMO', 'MITSU', 'TOYOTA', 'HONDA', 'NISSAN', 'MAZDA', 'SUBARU', 'SUZUKI', 'MITSUBISHI', 'ISUZU', 'HINO', 'DAIHATSU', 'KOMATSU', 'KUBOTA', 'YANMAR', 'ISEKI', 'SHIBAURA', 'KIOTI', 'TYM', 'LS', 'MTD', 'TORO', 'BRIGGS', 'STRATTON', 'KOHLER', 'GENERAC', 'CUMMINS', 'CATERPILLAR', 'DEERE', 'JOHN', 'CASE', 'NEWHOLLAND', 'AGCO', 'CLAAS', 'KUHN', 'KVERNELAND', 'LELY', 'GEA', 'TETRA', 'PAK', 'DELAVAL', 'BOUVMATIC', 'FULLWOOD', 'SAC', 'ALPRO', 'DAIRY', 'FARM', 'FARMS', 'MILK', 'CHEESE', 'BUTTER', 'YOGURT', 'ICE', 'CREAM', 'MEAT', 'BEEF', 'PORK', 'CHICKEN', 'TURKEY', 'EGG', 'EGGS', 'GRAIN', 'WHEAT', 'CORN', 'SOY', 'SOYBEAN', 'RICE', 'COTTON', 'SUGAR', 'COFFEE', 'COCOA', 'ORANGE', 'JUICE', 'FCOJ', 'LIVE', 'CATTLE', 'FEEDER', 'LEAN', 'HOGS', 'PORK', 'BELLY', 'LUMBER', 'PANEL', 'OSB', 'PLYWOOD', 'PARTICLE', 'BOARD', 'MDF', 'HDF', 'PAPER', 'PULP', 'WOOD', 'TIMBER', 'LOG', 'LOGS'}
        for ticker in tickers:
            if len(ticker) >= 2 and ticker not in exclude:
                entities.append({
                    'type': 'TICKER',
                    'name': ticker,
                    'relevance': 0.5,
                    'sentiment': 0.0
                })
        
        # Extract currencies
        currencies = self._currency_pattern.findall(text.upper())
        for curr in currencies:
            entities.append({
                'type': 'CURRENCY',
                'name': curr,
                'relevance': 0.3,
                'sentiment': 0.0
            })
        
        # In production, would use spaCy, transformers, etc.
        # entities = self._spacy_nlp(text).ents
        
        self._entity_cache[cache_key] = entities
        return entities
    
    async def classify_category(self, title: str, summary: str) -> List[NewsCategory]:
        """Classify article category."""
        text = f"{title} {summary}".lower()
        
        categories = []
        
        keyword_map = {
            NewsCategory.MARKETS: ['market', 'stock', 'trading', 'index', 'nasdaq', 'dow', 's&p', 'etf'],
            NewsCategory.ECONOMY: ['gdp', 'inflation', 'unemployment', 'fed', 'central bank', 'interest rate', 'cpi', 'pmi'],
            NewsCategory.COMPANIES: ['earnings', 'revenue', 'profit', 'ceo', 'quarterly', 'guidance'],
            NewsCategory.EARNINGS: ['earnings', 'eps', 'revenue', 'beat', 'miss', 'guidance', 'quarter'],
            NewsCategory.CRYPTO: ['bitcoin', 'ethereum', 'crypto', 'blockchain', 'btc', 'eth'],
            NewsCategory.FOREX: ['forex', 'currency', 'dollar', 'euro', 'yen', 'fx', 'exchange rate'],
            NewsCategory.COMMODITIES: ['oil', 'gold', 'silver', 'copper', 'commodity', 'crude', 'brent'],
            NewsCategory.FIXED_INCOME: ['bond', 'yield', 'treasury', 'coupon', 'duration', 'spread'],
            NewsCategory.MERGERS: ['merger', 'acquisition', 'takeover', 'buyout', 'm&a'],
            NewsCategory.REGULATION: ['sec', 'regulation', 'compliance', 'investigation', 'fine'],
            NewsCategory.TECHNOLOGY: ['ai', 'artificial intelligence', 'cloud', 'software', 'chip', 'semiconductor'],
            NewsCategory.ENERGY: ['energy', 'solar', 'wind', 'renewable', 'battery', 'hydrogen'],
        }
        
        for category, keywords in keyword_map.items():
            if any(kw in text for kw in keywords):
                categories.append(category)
        
        if not categories:
            categories.append(NewsCategory.GENERAL)
        
        return categories
    
    async def extract_keywords(self, text: str, max_keywords: int = 10) -> List[str]:
        """Extract key phrases/keywords."""
        # Simple TF-IDF style extraction
        # In production, would use RAKE, YAKE, or KeyBERT
        
        # Remove common stop words
        stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'as', 'is', 'was', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'this', 'that', 'these', 'those', 'it', 'its', 'their', 'them', 'they', 'we', 'you', 'i', 'he', 'she', 'his', 'her', 'our', 'your', 'my', 'me'}
        
        # Extract words
        words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())
        words = [w for w in words if w not in stop_words]
        
        # Count frequency
        freq = {}
        for w in words:
            freq[w] = freq.get(w, 0) + 1
        
        # Return top keywords
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [w for w, _ in sorted_words[:max_keywords]]
    
    async def analyze_sentiment(self, text: str) -> Tuple[NewsSentiment, Decimal, Decimal]:
        """Analyze sentiment of text.
        
        Returns: (sentiment_label, sentiment_score, confidence)
        """
        # Simple rule-based sentiment
        # In production, would use VADER, TextBlob, or transformer models
        
        positive_words = {'gain', 'rise', 'up', 'surge', 'rally', 'bull', 'bullish', 'profit', 'growth', 'beat', 'exceed', 'strong', 'record', 'high', 'best', 'optimistic', 'positive', 'upgrade', 'buy', 'outperform'}
        negative_words = {'fall', 'drop', 'decline', 'crash', 'bear', 'bearish', 'loss', 'weak', 'miss', 'cut', 'low', 'worst', 'pessimistic', 'negative', 'downgrade', 'sell', 'underperform', 'risk', 'concern', 'warn'}
        
        text_lower = text.lower()
        words = set(re.findall(r'\b\w+\b', text_lower))
        
        pos_count = len(words & positive_words)
        neg_count = len(words & negative_words)
        
        total = pos_count + neg_count
        if total == 0:
            return NewsSentiment.NEUTRAL, Decimal('0'), Decimal('0.3')
        
        score = (pos_count - neg_count) / total
        
        if score > 0.3:
            sentiment = NewsSentiment.VERY_POSITIVE if score > 0.6 else NewsSentiment.POSITIVE
        elif score < -0.3:
            sentiment = NewsSentiment.VERY_NEGATIVE if score < -0.6 else NewsSentiment.NEGATIVE
        else:
            sentiment = NewsSentiment.NEUTRAL
        
        confidence = Decimal(str(min(abs(score) + 0.2, 0.9)))
        
        return sentiment, Decimal(str(score)), confidence
    
    async def extract_tickers(self, text: str) -> List[str]:
        """Extract stock tickers from text."""
        # Common false positives to exclude
        exclude = {'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM', 'HIS', 'HOW', 'ITS', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WHO', 'BOY', 'DID', 'OIL', 'SIT', 'USE', 'CEO', 'CFO', 'CTO', 'COO', 'IPO', 'ETF', 'SEC', 'FDA', 'FED', 'GDP', 'CPI', 'PMI', 'EPS', 'ROE', 'ROA', 'YOY', 'QOQ', 'MTM', 'WTD', 'YTD'}
        
        tickers = self._ticker_pattern.findall(text.upper())
        valid_tickers = [t for t in tickers if t not in exclude and len(t) >= 2]
        
        # Deduplicate
        return list(dict.fromkeys(valid_tickers))
    
    async def score_relevance(self, article: 'NewsArticle', watchlist: List[str] = None) -> Decimal:
        """Score article relevance."""
        score = Decimal('0')
        
        # Ticker match
        if article.tickers:
            if watchlist:
                matches = set(article.tickers) & set(watchlist)
                score += Decimal(str(len(matches) * 0.2))
            else:
                score += Decimal(str(min(len(article.tickers) * 0.1, 0.5)))
        
        # Category relevance
        high_relevance_cats = {NewsCategory.EARNINGS, NewsCategory.MERGERS, NewsCategory.MARKETS, NewsCategory.ECONOMY}
        for cat in article.categories:
            if cat in high_relevance_cats:
                score += Decimal('0.15')
        
        # Sentiment strength
        score += Decimal(str(abs(float(article.sentiment_score)) * 0.2))
        
        # Recency
        hours_old = (datetime.utcnow() - article.published_at).total_seconds() / 3600
        if hours_old < 1:
            score += Decimal('0.3')
        elif hours_old < 6:
            score += Decimal('0.2')
        elif hours_old < 24:
            score += Decimal('0.1')
        
        return min(score, Decimal('1'))


class AlertManager:
    """Manage news alerts."""
    
    def __init__(self, pipeline: NewsIngestionPipeline):
        self.pipeline = pipeline
        self.rules: List[Dict] = []
    
    def add_rule(
        self,
        name: str,
        condition: Callable[['NewsArticle'], bool],
        callback: Callable[['NewsArticle'], Any],
        cooldown_seconds: int = 300
    ):
        """Add alert rule."""
        self.rules.append({
            'name': name,
            'condition': condition,
            'callback': callback,
            'cooldown': cooldown_seconds,
            'last_triggered': None,
        })
    
    async def check_alerts(self, article: 'NewsArticle'):
        """Check article against alert rules."""
        for rule in self.rules:
            # Check cooldown
            if rule['last_triggered']:
                elapsed = (datetime.utcnow() - rule['last_triggered']).total_seconds()
                if elapsed < rule['cooldown']:
                    continue
            
            try:
                if await rule['condition'](article):
                    rule['last_triggered'] = datetime.utcnow()
                    await rule['callback'](article)
            except Exception as e:
                logger.error(f"Alert rule {rule['name']} error: {e}")
    
    def add_ticker_alert(self, ticker: str, threshold: float, callback: Callable):
        """Add alert for ticker sentiment threshold."""
        async def condition(article):
            return ticker in article.tickers and float(article.sentiment_score) >= threshold
        
        self.add_rule(f"ticker_{ticker}_sentiment", condition, callback)


def create_news_pipeline() -> NewsIngestionPipeline:
    return NewsIngestionPipeline()


def create_nlp_processor() -> NLPProcessor:
    return NLPProcessor()


def create_alert_manager(pipeline: NewsIngestionPipeline) -> AlertManager:
    return AlertManager(pipeline)


def create_rss_provider(name: str, feed_urls: List[str], source: NewsSource = NewsSource.RSS_FEED) -> RSSFeedProvider:
    return RSSFeedProvider(name, feed_urls, source)


def create_news_aggregator(pipeline: NewsIngestionPipeline) -> NewsAggregator:
    return NewsAggregator(pipeline)