"""Economic Calendar - Event scheduling and tracking."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, date, time, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Optional
from enum import Enum
from typing import TYPE_CHECKING
import json

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


class EventImportance(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class EventCategory(str, Enum):
    EMPLOYMENT = "EMPLOYMENT"
    INFLATION = "INFLATION"
    GROWTH = "GROWTH"
    MONETARY_POLICY = "MONETARY_POLICY"
    FISCAL_POLICY = "FISCAL_POLICY"
    TRADE = "TRADE"
    HOUSING = "HOUSING"
    CONSUMER = "CONSUMER"
    BUSINESS = "BUSINESS"
    CENTRAL_BANK = "CENTRAL_BANK"
    ENERGY = "ENERGY"
    AGRICULTURE = "AGRICULTURE"


class EventStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    RELEASED = "RELEASED"
    REVISED = "REVISED"
    CANCELLED = "CANCELLED"


@dataclass
class EconomicEvent:
    """Economic calendar event."""
    
    # Identity
    id: str = ""
    source: str = ""  # FRED, ECB, BOE, BOJ, etc.
    source_event_id: str = ""
    
    # Event details
    title: str = ""
    description: str = ""
    category: EventCategory = EventCategory.GROWTH
    importance: EventImportance = EventImportance.MEDIUM
    
    # Timing
    scheduled_time: datetime = field(default_factory=datetime.utcnow)
    actual_time: Optional[datetime] = None
    timezone: str = "UTC"
    country: str = "US"
    region: str = ""
    
    # Values
    previous_value: Optional[Decimal] = None
    consensus_forecast: Optional[Decimal] = None
    actual_value: Optional[Decimal] = None
    revised_value: Optional[Decimal] = None
    unit: str = ""
    
    # Status
    status: EventStatus = EventStatus.SCHEDULED
    
    # Market impact
    market_impact: Optional[str] = None
    affected_assets: List[str] = field(default_factory=list)
    historical_volatility: Optional[Decimal] = None
    
    # Metadata
    url: str = ""
    tags: List[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    
    @property
    def surprise(self) -> Optional[Decimal]:
        """Calculate surprise vs consensus."""
        if self.consensus_forecast is not None and self.actual_value is not None:
            return self.actual_value - self.consensus_forecast
        return None
    
    @property
    def surprise_pct(self) -> Optional[Decimal]:
        """Surprise as percentage of consensus."""
        if self.consensus_forecast and self.consensus_forecast != 0 and self.surprise is not None:
            return (self.surprise / self.consensus_forecast) * Decimal('100')
        return None
    
    @property
    def is_high_impact(self) -> bool:
        return self.importance in [EventImportance.HIGH, EventImportance.CRITICAL]
    
    @property
    def is_released(self) -> bool:
        return self.status == EventStatus.RELEASED


@dataclass
class CalendarFilter:
    """Filter for querying economic calendar."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    countries: List[str] = field(default_factory=list)
    categories: List[EventCategory] = field(default_factory=list)
    importance: List[EventImportance] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    statuses: List[EventStatus] = field(default_factory=list)
    min_importance: Optional[EventImportance] = None
    keywords: List[str] = field(default_factory=list)


class EconomicCalendar:
    """Economic calendar management."""
    
    def __init__(self):
        self._events: Dict[str, EconomicEvent] = {}
        self._by_date: Dict[date, List[str]] = {}  # date -> event_ids
        self._by_country: Dict[str, List[str]] = {}
        self._by_category: Dict[EventCategory, List[str]] = {}
        self._importance_order = {
            EventImportance.LOW: 0,
            EventImportance.MEDIUM: 1,
            EventImportance.HIGH: 2,
            EventImportance.CRITICAL: 3,
        }
    
    def add_event(self, event: EconomicEvent) -> str:
        """Add event to calendar."""
        if not event.id:
            import uuid
            event.id = str(uuid.uuid4())
        
        self._events[event.id] = event
        
        # Index by date
        event_date = event.scheduled_time.date()
        if event_date not in self._by_date:
            self._by_date[event_date] = []
        self._by_date[event_date].append(event.id)
        
        # Index by country
        if event.country not in self._by_country:
            self._by_country[event.country] = []
        self._by_country[event.country].append(event.id)
        
        # Index by category
        if event.category not in self._by_category:
            self._by_category[event.category] = []
        self._by_category[event.category].append(event.id)
        
        return event.id
    
    def get_event(self, event_id: str) -> Optional[EconomicEvent]:
        return self._events.get(event_id)
    
    def get_events(
        self,
        filter: CalendarFilter = None,
        limit: int = 100,
        offset: int = 0
    ) -> List[EconomicEvent]:
        """Query events with filter."""
        results = []
        
        for event in self._events.values():
            if filter and not self._matches_filter(event, filter):
                continue
            results.append(event)
        
        # Sort by scheduled time, then importance
        results.sort(key=lambda e: (e.scheduled_time, -self._importance_order.get(e.importance, 0)))
        
        return results[offset:offset + limit]
    
    def _matches_filter(self, event: EconomicEvent, filter: CalendarFilter) -> bool:
        if filter.start_date and event.scheduled_time.date() < filter.start_date:
            return False
        if filter.end_date and event.scheduled_time.date() > filter.end_date:
            return False
        if filter.countries and event.country not in filter.countries:
            return False
        if filter.categories and event.category not in filter.categories:
            return False
        if filter.importance and event.importance not in filter.importance:
            return False
        if filter.sources and event.source not in filter.sources:
            return False
        if filter.statuses and event.status not in filter.statuses:
            return False
        if filter.min_importance:
            if self._importance_order.get(event.importance, 0) < self._importance_order.get(filter.min_importance, 0):
                return False
        if filter.keywords:
            text = f"{event.title} {event.description}".lower()
            if not any(kw.lower() in text for kw in filter.keywords):
                return False
        return True
    
    def get_events_for_date(self, target_date: date) -> List[EconomicEvent]:
        """Get all events for a specific date."""
        event_ids = self._by_date.get(target_date, [])
        events = [self._events[eid] for eid in event_ids if eid in self._events]
        events.sort(key=lambda e: (e.scheduled_time, -self._importance_order.get(e.importance, 0)))
        return events
    
    def get_events_for_range(self, start: date, end: date) -> List[EconomicEvent]:
        """Get all events in date range."""
        results = []
        for event in self._events.values():
            if start <= event.scheduled_time.date() <= end:
                results.append(event)
        results.sort(key=lambda e: (e.scheduled_time, -self._importance_order.get(e.importance, 0)))
        return results
    
    def get_upcoming_events(
        self,
        hours: int = 24,
        min_importance: EventImportance = EventImportance.MEDIUM
    ) -> List[EconomicEvent]:
        """Get upcoming events within hours."""
        now = datetime.utcnow()
        cutoff = now + timedelta(hours=hours)
        
        results = []
        for event in self._events.values():
            if event.status != EventStatus.SCHEDULED:
                continue
            if now <= event.scheduled_time <= cutoff:
                if self._importance_order.get(event.importance, 0) >= self._importance_order.get(min_importance, 0):
                    results.append(event)
        
        results.sort(key=lambda e: e.scheduled_time)
        return results
    
    def get_high_impact_upcoming(self, hours: int = 24) -> List[EconomicEvent]:
        """Get high impact upcoming events."""
        return self.get_upcoming_events(hours, EventImportance.HIGH)
    
    def update_event(self, event_id: str, updates: Dict[str, Any]) -> bool:
        """Update event fields."""
        event = self._events.get(event_id)
        if not event:
            return False
        
        for key, value in updates.items():
            if hasattr(event, key):
                setattr(event, key, value)
        
        event.updated_at = datetime.utcnow()
        return True
    
    def mark_released(self, event_id: str, actual_value: Decimal, actual_time: datetime = None) -> bool:
        """Mark event as released with actual value."""
        event = self._events.get(event_id)
        if not event:
            return False
        
        event.status = EventStatus.RELEASED
        event.actual_value = actual_value
        event.actual_time = actual_time or datetime.utcnow()
        event.updated_at = datetime.utcnow()
        return True
    
    def revise_event(self, event_id: str, revised_value: Decimal) -> bool:
        """Update event with revised value."""
        event = self._events.get(event_id)
        if not event:
            return False
        
        event.status = EventStatus.REVISED
        event.revised_value = revised_value
        event.updated_at = datetime.utcnow()
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get calendar statistics."""
        total = len(self._events)
        by_status = {}
        by_importance = {}
        by_country = {}
        by_category = {}
        
        for event in self._events.values():
            by_status[event.status.value] = by_status.get(event.status.value, 0) + 1
            by_importance[event.importance.value] = by_importance.get(event.importance.value, 0) + 1
            by_country[event.country] = by_country.get(event.country, 0) + 1
            by_category[event.category.value] = by_category.get(event.category.value, 0) + 1
        
        return {
            'total_events': total,
            'by_status': by_status,
            'by_importance': by_importance,
            'by_country': by_country,
            'by_category': by_category,
        }


class CalendarProvider:
    """Base class for calendar data providers."""
    
    def __init__(self, name: str):
        self.name = name
        self.calendar = EconomicCalendar()
    
    async def fetch_events(
        self,
        start_date: date,
        end_date: date,
        countries: List[str] = None
    ) -> List[EconomicEvent]:
        """Fetch events from source."""
        raise NotImplementedError
    
    async def sync_calendar(
        self,
        start_date: date,
        end_date: date,
        countries: List[str] = None
    ) -> int:
        """Sync calendar with source."""
        events = await self.fetch_events(start_date, end_date, countries)
        count = 0
        for event in events:
            self.calendar.add_event(event)
            count += 1
        return count


class FREDEconomicCalendarProvider(CalendarProvider):
    """FRED economic calendar provider."""
    
    def __init__(self, api_key: str = None):
        super().__init__("FRED")
        self.api_key = api_key
        self._base_url = "https://api.stlouisfed.org/fred"
    
    async def fetch_events(
        self,
        start_date: date,
        end_date: date,
        countries: List[str] = None
    ) -> List[EconomicEvent]:
        # In production, would call FRED API
        # For now, return sample events
        events = []
        
        # Sample high-impact US events
        sample_events = [
            {
                'title': 'Nonfarm Payrolls',
                'category': EventCategory.EMPLOYMENT,
                'importance': EventImportance.CRITICAL,
                'country': 'US',
                'unit': 'Thousands',
                'previous': Decimal('200'),
                'consensus': Decimal('180'),
            },
            {
                'title': 'CPI YoY',
                'category': EventCategory.INFLATION,
                'importance': EventImportance.CRITICAL,
                'country': 'US',
                'unit': '%',
                'previous': Decimal('3.2'),
                'consensus': Decimal('3.1'),
            },
            {
                'title': 'FOMC Rate Decision',
                'category': EventCategory.MONETARY_POLICY,
                'importance': EventImportance.CRITICAL,
                'country': 'US',
                'unit': '%',
                'previous': Decimal('5.50'),
                'consensus': Decimal('5.50'),
            },
            {
                'title': 'GDP QoQ',
                'category': EventCategory.GROWTH,
                'importance': EventImportance.HIGH,
                'country': 'US',
                'unit': '%',
                'previous': Decimal('2.1'),
                'consensus': Decimal('2.0'),
            },
            {
                'title': 'Retail Sales MoM',
                'category': EventCategory.CONSUMER,
                'importance': EventImportance.HIGH,
                'country': 'US',
                'unit': '%',
                'previous': Decimal('0.3'),
                'consensus': Decimal('0.2'),
            },
        ]
        
        import random
        base_date = datetime.combine(start_date, time(12, 30))  # 8:30 AM ET
        
        for i, evt in enumerate(sample_events):
            event_date = base_date + timedelta(days=i * 7)
            if event_date.date() > end_date:
                break
            
            event = EconomicEvent(
                source=self.name,
                source_event_id=f"fred_{evt['title'].lower().replace(' ', '_')}",
                title=evt['title'],
                category=evt['category'],
                importance=evt['importance'],
                country=evt['country'],
                unit=evt['unit'],
                previous_value=evt.get('previous'),
                consensus_forecast=evt.get('consensus'),
                scheduled_time=event_date,
                timezone='America/New_York',
                status=EventStatus.SCHEDULED if event_date > datetime.utcnow() else EventStatus.RELEASED,
                tags=['macro', 'us', evt['category'].value.lower()],
            )
            events.append(event)
        
        return events


class InvestingComCalendarProvider(CalendarProvider):
    """Investing.com economic calendar provider."""
    
    def __init__(self):
        super().__init__("Investing.com")
    
    async def fetch_events(
        self,
        start_date: date,
        end_date: date,
        countries: List[str] = None
    ) -> List[EconomicEvent]:
        # Would scrape or use API
        return []


class ForexFactoryCalendarProvider(CalendarProvider):
    """Forex Factory calendar provider."""
    
    def __init__(self):
        super().__init__("ForexFactory")
    
    async def fetch_events(
        self,
        start_date: date,
        end_date: date,
        countries: List[str] = None
    ) -> List[EconomicEvent]:
        # Would scrape Forex Factory
        return []


class CalendarAggregator:
    """Aggregate multiple calendar providers."""
    
    def __init__(self):
        self.providers: List[CalendarProvider] = []
        self.calendar = EconomicCalendar()
    
    def add_provider(self, provider: CalendarProvider):
        self.providers.append(provider)
    
    async def sync_all(
        self,
        start_date: date,
        end_date: date,
        countries: List[str] = None
    ) -> Dict[str, int]:
        """Sync all providers."""
        results = {}
        for provider in self.providers:
            try:
                count = await provider.sync_calendar(start_date, end_date, countries)
                results[provider.name] = count
            except Exception as e:
                results[provider.name] = f"Error: {e}"
        
        # Merge into main calendar
        for provider in self.providers:
            for event in provider.calendar._events.values():
                # Check for duplicates
                existing = self._find_duplicate(event)
                if not existing:
                    self.calendar.add_event(event)
                else:
                    # Merge: keep the one with more data
                    if event.actual_value and not existing.actual_value:
                        existing.actual_value = event.actual_value
        
        return results
    
    def _find_duplicate(self, event: EconomicEvent) -> Optional[EconomicEvent]:
        """Find duplicate event in calendar."""
        for existing in self.calendar._events.values():
            if (existing.title == event.title and 
                existing.country == event.country and
                abs((existing.scheduled_time - event.scheduled_time).total_seconds()) < 3600):
                return existing
        return None


def create_economic_calendar() -> EconomicCalendar:
    return EconomicCalendar()


def create_calendar_aggregator() -> CalendarAggregator:
    return CalendarAggregator()


def create_fred_calendar_provider(api_key: str = None) -> FREDEconomicCalendarProvider:
    return FREDEconomicCalendarProvider(api_key)