from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional, Dict, Any


class ExchangeCategory(str, Enum):
    MAINBOARD = "MAINBOARD"
    SME_NSE = "SME_NSE"
    SME_BSE = "SME_BSE"


class VerdictTier(str, Enum):
    STRONG_BUY = "LONG_TERM_COMPOUNDER"
    BUY_ON_DIPS = "CONDITIONAL_BUY_ON_DIPS"
    SPECULATIVE = "SPECULATIVE_HIGH_RISK"
    AVOID_TRAP = "AVOID_PROMOTER_TRAP"


@dataclass
class IPOMeta:
    company_name: str
    symbol: str
    sector: str
    category: ExchangeCategory
    issue_price: float              # Upper price band or fixed price in INR
    price_band_low: float
    price_band_high: float
    lot_size: int
    issue_size_crores: float
    open_date: str = ""
    close_date: str = ""
    listing_date: str = ""


@dataclass
class FinancialYear:
    year_label: str                 # e.g., "FY22", "FY23", "FY24"
    revenue_crores: float
    ebitda_crores: float
    pat_crores: float               # Profit After Tax
    net_worth_crores: float
    total_debt_crores: float
    cfo_crores: float               # Cash Flow from Operating Activities
    roce_pct: Optional[float] = None
    ronw_pct: Optional[float] = None


@dataclass
class IssueStructure:
    fresh_issue_crores: float
    ofs_crores: float               # Offer For Sale
    promoter_pre_holding_pct: float
    promoter_post_holding_pct: float
    promoter_pledge_pct: float = 0.0
    objects_of_issue: List[str] = field(default_factory=list)

    @property
    def fresh_issue_pct(self) -> float:
        total = self.fresh_issue_crores + self.ofs_crores
        if total <= 0:
            return 100.0
        return round((self.fresh_issue_crores / total) * 100.0, 2)

    @property
    def ofs_pct(self) -> float:
        total = self.fresh_issue_crores + self.ofs_crores
        if total <= 0:
            return 0.0
        return round((self.ofs_crores / total) * 100.0, 2)


@dataclass
class PeerInfo:
    name: str
    pe_ratio: float
    pb_ratio: float
    roe_pct: float
    ev_ebitda: Optional[float] = None


@dataclass
class PeerComparison:
    peers: List[PeerInfo] = field(default_factory=list)
    industry_pe_median: float = 0.0
    industry_pb_median: float = 0.0


@dataclass
class SMERiskMetrics:
    is_sme: bool = False
    top_3_clients_revenue_pct: float = 0.0
    top_5_clients_revenue_pct: float = 0.0
    debtor_days: float = 60.0
    working_capital_days: float = 90.0
    single_facility_risk: bool = False
    market_maker_spread_pct: float = 2.0


@dataclass
class GovernanceAndRisks:
    pending_litigations_crores: float = 0.0
    contingent_liabilities_crores: float = 0.0
    auditor_qualifications: bool = False
    related_party_transactions_high: bool = False
    promoter_legal_disputes: bool = False


@dataclass
class IPOProfile:
    meta: IPOMeta
    financials: List[FinancialYear]
    issue_structure: IssueStructure
    peers: PeerComparison
    governance: GovernanceAndRisks
    sme_metrics: Optional[SMERiskMetrics] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IPOProfile":
        meta_data = data["meta"]
        meta = IPOMeta(
            company_name=meta_data["company_name"],
            symbol=meta_data.get("symbol", ""),
            sector=meta_data["sector"],
            category=ExchangeCategory(meta_data.get("category", "MAINBOARD")),
            issue_price=float(meta_data["issue_price"]),
            price_band_low=float(meta_data.get("price_band_low", meta_data["issue_price"])),
            price_band_high=float(meta_data.get("price_band_high", meta_data["issue_price"])),
            lot_size=int(meta_data.get("lot_size", 1)),
            issue_size_crores=float(meta_data["issue_size_crores"]),
            open_date=meta_data.get("open_date", ""),
            close_date=meta_data.get("close_date", ""),
            listing_date=meta_data.get("listing_date", "")
        )

        fin_list = []
        for f in data.get("financials", []):
            fin_list.append(FinancialYear(
                year_label=f["year_label"],
                revenue_crores=float(f["revenue_crores"]),
                ebitda_crores=float(f["ebitda_crores"]),
                pat_crores=float(f["pat_crores"]),
                net_worth_crores=float(f["net_worth_crores"]),
                total_debt_crores=float(f["total_debt_crores"]),
                cfo_crores=float(f["cfo_crores"]),
                roce_pct=float(f["roce_pct"]) if f.get("roce_pct") is not None else None,
                ronw_pct=float(f["ronw_pct"]) if f.get("ronw_pct") is not None else None
            ))

        issue_data = data["issue_structure"]
        issue_structure = IssueStructure(
            fresh_issue_crores=float(issue_data["fresh_issue_crores"]),
            ofs_crores=float(issue_data["ofs_crores"]),
            promoter_pre_holding_pct=float(issue_data["promoter_pre_holding_pct"]),
            promoter_post_holding_pct=float(issue_data["promoter_post_holding_pct"]),
            promoter_pledge_pct=float(issue_data.get("promoter_pledge_pct", 0.0)),
            objects_of_issue=issue_data.get("objects_of_issue", [])
        )

        peer_data = data.get("peers", {})
        peer_list = [
            PeerInfo(
                name=p["name"],
                pe_ratio=float(p["pe_ratio"]),
                pb_ratio=float(p.get("pb_ratio", 0.0)),
                roe_pct=float(p.get("roe_pct", 0.0)),
                ev_ebitda=float(p["ev_ebitda"]) if p.get("ev_ebitda") is not None else None
            )
            for p in peer_data.get("peers", [])
        ]
        peers = PeerComparison(
            peers=peer_list,
            industry_pe_median=float(peer_data.get("industry_pe_median", 0.0)),
            industry_pb_median=float(peer_data.get("industry_pb_median", 0.0))
        )

        gov_data = data.get("governance", {})
        governance = GovernanceAndRisks(
            pending_litigations_crores=float(gov_data.get("pending_litigations_crores", 0.0)),
            contingent_liabilities_crores=float(gov_data.get("contingent_liabilities_crores", 0.0)),
            auditor_qualifications=bool(gov_data.get("auditor_qualifications", False)),
            related_party_transactions_high=bool(gov_data.get("related_party_transactions_high", False)),
            promoter_legal_disputes=bool(gov_data.get("promoter_legal_disputes", False))
        )

        sme_metrics = None
        if "sme_metrics" in data or meta.category in (ExchangeCategory.SME_NSE, ExchangeCategory.SME_BSE):
            sme_raw = data.get("sme_metrics", {})
            sme_metrics = SMERiskMetrics(
                is_sme=True,
                top_3_clients_revenue_pct=float(sme_raw.get("top_3_clients_revenue_pct", 0.0)),
                top_5_clients_revenue_pct=float(sme_raw.get("top_5_clients_revenue_pct", 0.0)),
                debtor_days=float(sme_raw.get("debtor_days", 60.0)),
                working_capital_days=float(sme_raw.get("working_capital_days", 90.0)),
                single_facility_risk=bool(sme_raw.get("single_facility_risk", False)),
                market_maker_spread_pct=float(sme_raw.get("market_maker_spread_pct", 2.0))
            )

        return cls(
            meta=meta,
            financials=fin_list,
            issue_structure=issue_structure,
            peers=peers,
            governance=governance,
            sme_metrics=sme_metrics
        )
