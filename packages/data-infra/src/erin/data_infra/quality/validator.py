"""Data Quality Validation Framework - Completeness, timeliness, validity, consistency checks."""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, List, Dict, Any, Callable, Set
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from erin.market_intel.domain.interfaces import Quote, Bar

logger = logging.getLogger(__name__)


class QualitySeverity(str, Enum):
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class QualityCheckType(str, Enum):
    COMPLETENESS = "COMPLETENESS"
    TIMELINESS = "TIMELINESS"
    VALIDITY = "VALIDITY"
    CONSISTENCY = "CONSISTENCY"
    ACCURACY = "ACCURACY"


@dataclass
class QualityIssue:
    """Individual data quality issue."""
    check_type: QualityCheckType
    severity: QualitySeverity
    rule: str
    description: str
    affected_records: int
    sample_values: List[Any]
    field: Optional[str] = None
    instrument_id: Optional[str] = None
    timestamp: datetime = field(default_factory=datetime.utcnow)


@dataclass
class QualityReport:
    """Data quality report for a dataset."""
    dataset: str
    provider: str
    timestamp: datetime
    total_records: int
    issues: List[QualityIssue] = field(default_factory=list)
    completeness_score: float = 1.0
    timeliness_score: float = 1.0
    validity_score: float = 1.0
    consistency_score: float = 1.0
    overall_score: float = 1.0
    
    def add_issue(self, issue: QualityIssue):
        self.issues.append(issue)
        self._recalculate_scores()
    
    def _recalculate_scores(self):
        """Recalculate quality scores based on issues."""
        if not self.issues:
            self.completeness_score = 1.0
            self.timeliness_score = 1.0
            self.validity_score = 1.0
            self.consistency_score = 1.0
            self.overall_score = 1.0
            return
        
        # Simple scoring based on issue counts and severity
        severity_weights = {
            "INFO": 0.1,
            "WARNING": 0.3,
            "ERROR": 0.7,
            "CRITICAL": 1.0
        }
        
        type_weights = {
            "COMPLETENESS": self.completeness_score,
            "TIMELINESS": self.timeliness_score,
            "VALIDITY": self.validity_score,
            "CONSISTENCY": self.consistency_score,
            "ACCURACY": 1.0
        }
        
        # Calculate weighted penalty
        total_penalty = 0
        total_weight = 0
        
        for issue in self.issues:
            weight = severity_weights.get(issue.severity, 0.5)
            total_penalty += weight
            total_weight += 1
        
        if total_weight > 0:
            penalty = min(total_penalty / total_weight, 1.0)
            self.overall_score = max(0.0, 1.0 - penalty)
        else:
            self.overall_score = 1.0
        
        # Per-category scores (simplified)
        self.completeness_score = self.overall_score
        self.timeliness_score = self.overall_score
        self.validity_score = self.overall_score
        self.consistency_score = self.overall_score


class QualityValidator:
    """Main data quality validator with configurable rules."""
    
    def __init__(self):
        self.rules: Dict[str, Callable] = {}
        self.global_rules: List[Callable] = []
    
    def add_rule(
        self,
        name: str,
        check_fn: Callable,
        check_type: QualityCheckType = QualityCheckType.VALIDITY,
        severity: QualitySeverity = QualitySeverity.ERROR,
        description: str = ""
    ):
        """Add a validation rule."""
        self.rules[name] = {
            "fn": check_fn,
            "type": check_type,
            "severity": severity,
            "description": description
        }
    
    def add_global_rule(self, check_fn: Callable):
        """Add a global rule that applies to all records."""
        self.global_rules.append(check_fn)
    
    def validate_quotes(self, quotes: List['Quote']) -> QualityReport:
        """Validate a list of quotes."""
        from erin.market_intel.domain.interfaces import Quote
        
        report = QualityReport(
            dataset="quotes",
            provider="multiple",
            timestamp=datetime.utcnow(),
            total_records=len(quotes)
        )
        
        if not quotes:
            report.add_issue(QualityIssue(
                check_type=QualityCheckType.COMPLETENESS,
                severity=QualitySeverity.WARNING,
                rule="empty_dataset",
                description="No quotes provided",
                affected_records=0,
                sample_values=[]
            ))
            return report
        
        # Run global rules
        for rule in self.global_rules:
            try:
                issues = rule(quotes)
                for issue in issues:
                    report.add_issue(issue)
            except Exception as e:
                logger.error(f"Global rule failed: {e}")
        
        # Run per-record rules
        for quote in quotes:
            for name, rule in self.rules.items():
                try:
                    issues = rule["fn"](quote)
                    for issue in issues:
                        issue.instrument_id = quote.instrument_id.composite_ticker if quote.instrument_id else None
                        report.add_issue(issue)
                except Exception as e:
                    logger.error(f"Rule {name} failed for quote: {e}")
        
        return report
    
    def validate_bars(self, bars: List['Bar']) -> QualityReport:
        """Validate a list of price bars."""
        from erin.market_intel.domain.interfaces import Bar
        
        report = QualityReport(
            dataset="bars",
            provider="multiple",
            timestamp=datetime.utcnow(),
            total_records=len(bars)
        )
        
        if not bars:
            report.add_issue(QualityIssue(
                check_type=QualityCheckType.COMPLETENESS,
                severity=QualitySeverity.WARNING,
                rule="empty_dataset",
                description="No bars provided",
                affected_records=0,
                sample_values=[]
            ))
            return report
        
        # Check for gaps in time series
        self._check_time_gaps(bars, report)
        
        # Check OHLC consistency
        self._check_ohlc_consistency(bars, report)
        
        # Check for outliers
        self._check_outliers(bars, report)
        
        return report
    
    def _check_time_gaps(self, bars: List, report: QualityReport):
        """Check for unexpected gaps in time series."""
        if len(bars) < 2:
            return
        
        # Sort by timestamp
        sorted_bars = sorted(bars, key=lambda b: b.timestamp)
        
        for i in range(1, len(sorted_bars)):
            prev = sorted_bars[i - 1]
            curr = sorted_bars[i]
            
            # Expected interval (assuming daily data)
            expected_delta = timedelta(days=1)
            actual_delta = curr.timestamp - prev.timestamp
            
            if actual_delta > expected_delta * 3:  # More than 3 days gap
                report.add_issue(QualityIssue(
                    check_type=QualityCheckType.COMPLETENESS,
                    severity=QualitySeverity.WARNING,
                    rule="time_gap",
                    description=f"Gap of {actual_delta.days} days between {prev.timestamp.date()} and {curr.timestamp.date()}",
                    affected_records=1,
                    sample_values=[str(prev.timestamp), str(curr.timestamp)],
                    instrument_id=curr.instrument_id.composite_ticker if curr.instrument_id else None
                ))
    
    def _check_ohlc_consistency(self, bars: List, report: QualityReport):
        """Check OHLC consistency: high >= max(open, close), low <= min(open, close)."""
        for bar in bars:
            if bar.high < max(bar.open, bar.close):
                report.add_issue(QualityIssue(
                    check_type=QualityCheckType.VALIDITY,
                    severity=QualitySeverity.ERROR,
                    rule="ohlc_high_invalid",
                    description=f"High ({bar.high}) < max(open={bar.open}, close={bar.close})",
                    affected_records=1,
                    sample_values=[float(bar.high), float(bar.open), float(bar.close)],
                    field="high",
                    instrument_id=bar.instrument_id.composite_ticker if bar.instrument_id else None
                ))
            
            if bar.low > min(bar.open, bar.close):
                report.add_issue(QualityIssue(
                    check_type=QualityCheckType.VALIDITY,
                    severity=QualitySeverity.ERROR,
                    rule="ohlc_low_invalid",
                    description=f"Low ({bar.low}) > min(open={bar.open}, close={bar.close})",
                    affected_records=1,
                    sample_values=[float(bar.low), float(bar.open), float(bar.close)],
                    field="low",
                    instrument_id=bar.instrument_id.composite_ticker if bar.instrument_id else None
                ))
            
            # Check for negative prices
            for field_name, value in [("open", bar.open), ("high", bar.high), ("low", bar.low), ("close", bar.close)]:
                if value < 0:
                    report.add_issue(QualityIssue(
                        check_type=QualityCheckType.VALIDITY,
                        severity=QualitySeverity.ERROR,
                        rule="negative_price",
                        description=f"Negative {field_name} price: {value}",
                        affected_records=1,
                        sample_values=[float(value)],
                        field=field_name,
                        instrument_id=bar.instrument_id.composite_ticker if bar.instrument_id else None
                    ))
    
    def _check_outliers(self, bars: List, report: QualityReport):
        """Check for statistical outliers using IQR method."""
        if len(bars) < 10:
            return
        
        # Calculate IQR for close prices
        closes = [float(b.close) for b in bars]
        closes.sort()
        
        q1 = closes[len(closes) // 4]
        q3 = closes[3 * len(closes) // 4]
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        for bar in bars:
            close_val = float(bar.close)
            if close_val < lower_bound or close_val > upper_bound:
                report.add_issue(QualityIssue(
                    check_type=QualityCheckType.CONSISTENCY,
                    severity=QualitySeverity.WARNING,
                    rule="price_outlier",
                    description=f"Close price {close_val} is statistical outlier (bounds: {lower_bound:.2f}-{upper_bound:.2f})",
                    affected_records=1,
                    sample_values=[close_val, lower_bound, upper_bound],
                    field="close",
                    instrument_id=bar.instrument_id.composite_ticker if bar.instrument_id else None
                )


# Default validators
def create_default_validator() -> QualityValidator:
    """Create validator with default financial data rules."""
    validator = QualityValidator()
    
    # Quote validation rules
    validator.add_rule(
        "quote_positive_price",
        lambda q: [] if (q.last and q.last.value > 0) else [
            QualityIssue(
                check_type=QualityCheckType.VALIDITY,
                severity=QualitySeverity.ERROR,
                rule="positive_price",
                description="Quote price must be positive",
                affected_records=1,
                sample_values=[float(q.last.value)] if q.last else [],
                field="last",
                instrument_id=q.instrument_id.composite_ticker if q.instrument_id else None
            )
        ],
        QualityCheckType.VALIDITY,
        QualitySeverity.ERROR,
        "Quote price must be positive"
    )
    
    validator.add_rule(
        "quote_bid_ask_spread",
        lambda q: [] if not (q.bid and q.ask) or q.ask.value >= q.bid.value else [
            QualityIssue(
                check_type=QualityCheckType.VALIDITY,
                severity=QualitySeverity.ERROR,
                rule="bid_ask_crossed",
                description=f"Bid ({q.bid.value}) >= Ask ({q.ask.value}) - crossed spread",
                affected_records=1,
                sample_values=[float(q.bid.value), float(q.ask.value)],
                field="bid,ask",
                instrument_id=q.instrument_id.composite_ticker if q.instrument_id else None
            )
        ],
        QualityCheckType.VALIDITY,
        QualitySeverity.ERROR,
        "Bid must be less than ask"
    )
    
    validator.add_rule(
        "quote_reasonable_spread",
        lambda q: [] if not (q.bid and q.ask and q.bid.value > 0) or (q.ask.value - q.bid.value) / q.bid.value < 0.5 else [
            QualityIssue(
                check_type=QualityCheckType.VALIDITY,
                severity=QualitySeverity.WARNING,
                rule="wide_spread",
                description=f"Spread > 50% of bid price: bid={q.bid.value}, ask={q.ask.value}",
                affected_records=1,
                sample_values=[float(q.bid.value), float(q.ask.value)],
                field="bid,ask",
                instrument_id=q.instrument_id.composite_ticker if q.instrument_id else None
            )
        ],
        QualityCheckType.CONSISTENCY,
        QualitySeverity.WARNING,
        "Spread should be reasonable"
    )
    
    # Bar validation rules
    validator.add_rule(
        "bar_positive_volume",
        lambda b: [] if b.volume >= 0 else [
            QualityIssue(
                check_type=QualityCheckType.VALIDITY,
                severity=QualitySeverity.ERROR,
                rule="negative_volume",
                description=f"Negative volume: {b.volume}",
                affected_records=1,
                sample_values=[b.volume],
                field="volume",
                instrument_id=b.instrument_id.composite_ticker if b.instrument_id else None
            )
        ],
        QualityCheckType.VALIDITY,
        QualitySeverity.ERROR,
        "Volume must be non-negative"
    )
    
    # Global rules
    def check_duplicate_timestamps(records):
        issues = []
        seen = set()
        for i, record in enumerate(records):
            key = (record.instrument_id.composite_ticker if record.instrument_id else None, record.timestamp)
            if key in seen:
                issues.append(QualityIssue(
                    check_type=QualityCheckType.CONSISTENCY,
                    severity=QualitySeverity.ERROR,
                    rule="duplicate_timestamp",
                    description=f"Duplicate timestamp for {record.instrument_id.composite_ticker if record.instrument_id else 'unknown'} at {record.timestamp}",
                    affected_records=1,
                    sample_values=[str(record.timestamp)],
                    field="timestamp",
                    instrument_id=record.instrument_id.composite_ticker if record.instrument_id else None
                ))
            seen.add(key)
        return issues
    
    validator.add_global_rule(lambda quotes: check_duplicate_timestamps(quotes))
    
    return validator