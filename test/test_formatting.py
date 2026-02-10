from src.backend.mcp_servers.mcp_formatting.server import *
import pytest
import re


def test_html_only():
    pass


@pytest.mark.asyncio
async def test_same_text():
    # Setup: input text
    text_blocks = [
    "Annual Insight: Horizon Pulse (HPX) - The Intersection of Quantum Compute and Low-Orbit Logistics",
    "Market Position: As of Q2 2026, HPX has solidified its position as a Tier-1 defense and infrastructure provider. With a focus on 'Deep-Tech' integration, our valuation has surpassed the $2.8T mark, driven by a 400% increase in autonomous satellite deployment contracts.",
    "The 'Aether' Network Status:\n* Total Satellites in Orbit: 12,400\n* Latency: <15ms Global Average\n* User Base: 45 Million (Commercial & Defense)\n* Projected Revenue (2027): $22 Billion",
    "Segmented Earnings Analysis (Q1 2026):\n* Orbital Logistics: 42% (Leading via the Falcon-X Partner Program)\n* Quantum Computing (QaaS): 28% (Serving pharmaceutical and financial sectors)\n* Autonomous Defense: 18% (Focusing on non-kinetic interception)\n* Consumer Connectivity: 12% (The 'Aether' home terminal units)",
    "Strategic Pivot: The transition from Silicon to Graphene-based processors has yielded a 30% reduction in thermal output across our server farms. This 'Cold-Compute' initiative is expected to save $400M in annual cooling costs while doubling the FLOPs-per-watt efficiency. We are currently scaling this to our Reykjavik and Singapore data hubs.",
    "Executive Leadership & Governance: Following the appointment of Dr. Aris Thorne as CTO, HPX has pivoted toward 'Explainable AI' (XAI) architectures. This move is designed to satisfy the rigorous audit requirements of the 2025 AI Accountability Act, ensuring our autonomous systems remain transparent and legally defensible.",
    "Global Logistics Footprint: Our 2026 roadmap includes the completion of 'Port Horizon' in the Atacama Desert. This site will serve as the world's first carbon-neutral spaceport, utilizing 100% solar-thermal energy to fuel hydrogen-based heavy-lift rockets. Construction is currently 74% complete.",
    "Financial Risk Matrix:\nRegulatory: High (Ongoing EU antitrust probes regarding orbital spectrum hoarding)\nTechnical: Medium (Graphene yield stability at scale)\nGeopolitical: Low (Diversified manufacturing across 12 NATO-aligned nations)\nCurrency: Medium (Hedging against Euro/USD volatility)",
    "The 2026 Dividend Outlook: The Board has authorized a 12% increase in the annual dividend, totaling $3.80 per share. This is supported by a free cash flow (FCF) margin of 22%, which remains top-of-class in the aerospace sector. We anticipate maintaining this payout ratio through the 2028 cycle.",
    "Environmental, Social, and Governance (ESG): HPX has achieved its 'Plastic-Negative' status for the third consecutive year. Our hardware recycling program successfully reclaimed 92,000 metric tons of circuit-board grade copper in 2025. We are on track to become a 'Carbon-Sovereign' entity by 2029.",
    "Technical Sentiment (Stock): HPX is currently trading at a P/E ratio of 34x, reflecting high growth expectations. The stock is holding above its 200-day EMA, with a significant accumulation zone identified between $310 and $325. Institutional ownership stands at a record 82%.",
    "Summary Conclusion: Horizon Pulse is no longer just an aerospace company; it is a global utility. By owning the data (Quantum) and the delivery (Orbital), HPX has created an unbreakable recurring revenue moat. We remain overweight on HPX for the 2026-2030 decade."
]

    images = []

    # Prepare html to be scanned
    def extract_text(html: str) -> str:
        # Remove HTML tags
        no_tags = re.sub(r"<[^>]+>", " ", html)
 
        # Collapse whitespace
        return re.sub(r"\s+", " ", no_tags).strip()
    def tokenize(s: str) -> list[str]:
        # Split on whitespace and punctuation
        return re.findall(r"[A-Za-z0-9]+", s)

    # Invoke: call tool
    html_path = Path("latest_report.html")
    html = html_path.read_text(encoding="utf-8")

    # Extract text from html
    extracted_text = extract_text(html)

    # Tokenize text
    html_tokens = tokenize(extracted_text)

    # Tokenize text blocks
    for block in text_blocks:
        block_tokens = tokenize(block)

        # Assert: make sure each text block appears in HTML unchanged
        index = 0
        for token in block_tokens:
            try:
                index = html_tokens.index(token, index) + 1
            except ValueError:
                raise AssertionError(f"Missing token: {token!r} from block: {block!r}")
