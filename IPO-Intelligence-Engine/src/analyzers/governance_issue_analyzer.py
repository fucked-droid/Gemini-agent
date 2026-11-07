from dataclasses import dataclass, field
from typing import List
from src.models.ipo_schema import IPOProfile, IssueStructure, GovernanceAndRisks


@dataclass
class GovernanceAnalysisResult:
    fresh_issue_pct: float
    ofs_pct: float
    promoter_post_holding_pct: float
    promoter_pledge_pct: float
    litigation_to_networth_pct: float
    auditor_qualification_flag: bool
    score: float                      # 0 to 100
    strengths: List[str] = field(default_factory=list)
    red_flags: List[str] = field(default_factory=list)


def analyze_governance_and_structure(profile: IPOProfile) -> GovernanceAnalysisResult:
    """Audits issue structure, promoter alignment, capital deployment objects, and legal risks."""
    issue = profile.issue_structure
    gov = profile.governance
    latest_networth = profile.financials[-1].net_worth_crores if profile.financials else 100.0

    fresh_pct = issue.fresh_issue_pct
    ofs_pct = issue.ofs_pct

    # Litigations as % of Net Worth
    lit_total = gov.pending_litigations_crores + gov.contingent_liabilities_crores
    lit_pct = round((lit_total / latest_networth) * 100.0, 2) if latest_networth > 0 else 0.0

    score = 50.0
    strengths = []
    red_flags = []

    # 1. Fresh Issue vs OFS Split
    if fresh_pct >= 80.0:
        score += 20.0
        strengths.append(f"Growth capital alignment: {fresh_pct}% of the IPO is Fresh Issue (money directly fuels company expansion/debt paydown).")
    elif fresh_pct >= 50.0:
        score += 10.0
        strengths.append(f"Balanced issue structure: {fresh_pct}% Fresh Issue / {ofs_pct}% OFS.")
    elif ofs_pct >= 80.0:
        score -= 25.0
        red_flags.append(f"Promoter/PE Exit Vehicle: {ofs_pct}% of the IPO is Offer for Sale (OFS). Zero or negligible growth capital enters the company.")
    elif ofs_pct >= 60.0:
        score -= 15.0
        red_flags.append(f"Heavy OFS concentration: {ofs_pct}% OFS indicates significant pre-IPO investor cashing out.")

    # 2. Promoter Skin in the Game
    if issue.promoter_post_holding_pct >= 60.0:
        score += 15.0
        strengths.append(f"High promoter commitment: Post-issue promoter holding remains strong at {issue.promoter_post_holding_pct}%.")
    elif issue.promoter_post_holding_pct < 40.0:
        score -= 15.0
        red_flags.append(f"Low promoter skin in the game: Post-issue promoter stake drops to {issue.promoter_post_holding_pct}%.")

    # 3. Promoter Pledge Check
    if issue.promoter_pledge_pct == 0.0:
        score += 5.0
        strengths.append("Zero encumbrance: 0.0% promoter share pledge.")
    elif issue.promoter_pledge_pct > 20.0:
        score -= 25.0
        red_flags.append(f"High pledge danger: {issue.promoter_pledge_pct}% of promoter shares are pledged to lenders.")
    elif issue.promoter_pledge_pct > 0.0:
        score -= 10.0
        red_flags.append(f"Encumbrance flag: {issue.promoter_pledge_pct}% of promoter shares are pledged.")

    # 4. Auditor Qualifications & Related Party Transactions
    if gov.auditor_qualifications:
        score -= 25.0
        red_flags.append("Audit Integrity Warning: Statutory auditors have included adverse remarks or qualifications in financial statements.")
    if gov.related_party_transactions_high:
        score -= 10.0
        red_flags.append("Corporate Governance Concern: High volume of related-party transactions with promoter-owned entities.")
    if gov.promoter_legal_disputes:
        score -= 10.0
        red_flags.append("Promoter Background: Ongoing criminal or serious regulatory proceedings against key management/promoters.")

    # 5. Litigation vs Net Worth
    if lit_pct > 30.0:
        score -= 20.0
        red_flags.append(f"Litigation overhang: Contingent liabilities & lawsuits total ₹{lit_total} Cr ({lit_pct}% of Net Worth).")
    elif lit_pct <= 5.0:
        score += 5.0
        strengths.append("Negligible legal liabilities: Clean track record with minimal litigation exposure.")

    score = max(0.0, min(100.0, round(score, 1)))

    return GovernanceAnalysisResult(
        fresh_issue_pct=fresh_pct,
        ofs_pct=ofs_pct,
        promoter_post_holding_pct=issue.promoter_post_holding_pct,
        promoter_pledge_pct=issue.promoter_pledge_pct,
        litigation_to_networth_pct=lit_pct,
        auditor_qualification_flag=gov.auditor_qualifications,
        score=score,
        strengths=strengths,
        red_flags=red_flags
    )
