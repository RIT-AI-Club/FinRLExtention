"""
Test script for verifying report formatting and PDF conversion.
This script uses hardcoded data to simulate a report generation process.
Run this file to generate a report with fake data and images, and convert it to PDF. Check the console logs for success or failure messages.
"""

import asyncio
import logging
from server import format_report
from pdf_converter import html_to_pdf

# Configure logging for the test script
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

TEXT_BLOCKS = [
    "Market Dominance Overview: APX has successfully integrated the 'Synapse-Cloud' protocol across 142 terrestrial data centers spanning six continents. As of Q1 2026, APX controls 62% of the world's Inference-as-a-Service (IaaS) market share — up from just 18% in 2020. With a market capitalization now exceeding $4.5 trillion, APX is the world's first Intelligence Utility, providing the cognitive infrastructure that powers governments, enterprises, and critical systems globally.",        
    "Financial Efficiency & Margins: FY2025 delivered record results across every financial metric. Gross revenue reached $182.4 billion, a 28% increase year-over-year. Operating margin expanded to 44% driven by automated server maintenance reducing labor costs by 61% and Deep-Frost cooling units slashing energy expenditure. Net income of $68.2 billion represents a 34% net margin — exceptional for infrastructure at this scale. Capital expenditures of $42 billion were deployed primarily into Deep-Frost second-generation cooling and Border-Vault sovereign cluster expansion across 14 new NATO-aligned territories.",
    "The Deep-Frost Cooling Initiative: APX's proprietary liquid-nitrogen immersion cooling system represents the most significant advancement in data center thermodynamics in two decades. By deploying H1000-series server pods 200 meters below the North Sea surface, APX exploits consistent 4°C ambient temperatures to achieve a Power Usage Effectiveness of 1.008 — compared to an industry average of 1.49. The thermal stability eliminates 90% of throttle events that degraded peak inference throughput. Annual energy savings are estimated at 47 terawatt-hours — equivalent to the consumption of Denmark.",
    "Sovereignty and Regulation: The 2025 AI Autonomy Act, ratified by 31 nations, mandates that Tier-1 AI providers maintain 100% data residency within national borders for all government and critical infrastructure contracts. APX anticipated this regulatory environment, having begun Border-Vault cluster deployments in 2023. Today, every NATO-aligned country hosts a fully air-gapped APX sovereign cluster. Data processed within a nation's borders never traverses international routing. This positions APX as the only Tier-1 provider fully compliant at launch — competitors face 18–36 month remediation timelines.",
    "Technical Performance Superiority: APX's H1000-series Synapse processors deliver benchmark results that redefine industry expectations. Median inference latency of 0.12 milliseconds versus an industry average of 4.5ms represents a 37x improvement. Tokens-per-watt efficiency of 4,200 versus 850 industry average translates directly to operating cost advantage at scale. Model uptime of 99.999% is achieved through a distributed hot-standby architecture spanning three geographically separated clusters per region. All inter-cluster and client communications use APX Quantum-Encrypted protocol — immune to both classical and quantum decryption attacks.",
    "The 2026 Shareholder Directive: Following a fiscal year of record revenue, margin expansion, and cash generation, the APX Board of Directors authorized the largest capital return program in the history of the technology sector. The program comprises a $60 billion share buyback over 24 months and a one-time special dividend of $5.50 per share. This capital return reflects the Board's conviction that APX's current valuation significantly undervalues the long-term earnings power of the Synapse-Cloud recurring revenue model — which carries a 94% net revenue retention rate and $312 billion in contracted forward revenue.",
    "Risk: Solar Interference — HIGH: APX's Border-Vault satellite mesh represents the largest private satellite constellation in orbit. A Carrington-class solar event — estimated probability of 0.7% per decade — would temporarily disable quantum-encrypted uplinks and could physically damage satellite components. APX has implemented a hardened ground-switching protocol that reroutes all sovereign cluster traffic to terrestrial fiber within 90 seconds of detected solar activity above X-class intensity. Despite this mitigation, solar interference remains the highest-rated systemic risk due to the irreversibility of satellite hardware damage.",
    "Risk: Regulatory Antitrust — MEDIUM: The US Department of Justice commenced a formal investigation into APX's IaaS market practices in September 2025, citing the company's 62% market share and exclusivity clauses in government contracts. APX is cooperating fully with investigators. External legal counsel rates the probability of a forced divestiture at below 8%, given APX's status as critical national infrastructure provider for 14 governments. The most likely outcome is a behavioral remedy requiring open interconnect standards — which APX has proactively offered. European Commission review is expected in Q3 2026.",
    "Neuro-Prosthetics & Ethics: The Cortex-Bridge Phase II clinical trial enrolled 500 patients with complete thoracic spinal cord injuries across 12 international medical centers. Using APX's Deep-Link neural interface — a 2,048-channel cortical array with sub-millisecond signal processing — patients achieved a 92% success rate in autonomous motor-control restoration at six-month follow-up. Sensory feedback restoration was achieved in 78% of patients. APX operates an independent Ethics-Gated review board that must approve all commercial deployments of bio-integrated technology. No Cortex-Bridge system will be deployed outside clinical settings until full Phase III completion in Q2 2027.",
    "Global Logistics: Nexus One: Construction began in Q4 2025 on Nexus One — APX's flagship hyperscale facility located in the Atacama Desert, Chile, at 2,400 meters elevation. The site was selected for 330+ days of solar irradiance annually, proximity to subsea cable landing stations, and seismic stability. At full capacity in 2028, Nexus One will deliver 10 gigawatts of compute from 100% renewable solar generation. The facility employs atmospheric water generators producing 4 million liters per day for cooling — achieving complete water neutrality without drawing from local aquifers. Nexus One will become the world's largest single AI compute installation.",
    "The Black-Box Transparency Initiative: In response to industry-wide concerns about AI hallucination in legal and medical contexts — the so-called Hallucination Crisis of 2025 — APX has deployed Proof-of-Logic (PoL) logging across all production inference endpoints. Every output is accompanied by a cryptographic Merkle chain documenting the specific model weights activated, retrieval sources queried, and confidence intervals at each reasoning step. PoL logs are admissible as evidence in 23 US jurisdictions following landmark rulings in Q3 2025. APX is the only Tier-1 provider offering 100% auditability, creating a regulatory moat in legal, medical, and financial applications.",
    "Technical Market Momentum: APX is the undisputed anchor of the Intelligence Super-Cycle — the infrastructure investment wave driven by enterprise AI adoption that analysts project will generate $14 trillion in cumulative capex through 2035. From a technical analysis perspective, APX shares are forming a textbook monthly Cup and Handle pattern with a measured move target of $1,450, representing 31% upside from current levels. Institutional ownership stands at 91%, with 45 of 45 covering analysts maintaining Buy or Strong Buy ratings — the first unanimous analyst consensus in the history of mega-cap technology coverage.",
    "Summary Statement: Apex-Neuralis is not merely a technology company — it is the reasoning infrastructure of the 21st-century global economy. APX processes more decisions per second than every human institution on Earth combined. Governments depend on it for sovereign intelligence. Hospitals depend on it for diagnostic precision. Financial markets depend on it for real-time risk arbitration. The question for investors is not whether AI infrastructure will define the next decade — it will. The question is which company will own that infrastructure. The answer, by every technical, regulatory, and financial measure, is APX."
]

IMAGES = [
    [
        "http://localhost:8000/revenue_growth.png",
        "Annual gross revenue showing 28% CAGR over 8 years, reaching $182.4B in FY2025."
    ],
    [
        "http://localhost:8000/segment_donut.png",
        "Intelligence segment revenue breakdown. Enterprise Inference dominates at 42%, with Sovereignty-Cloud as the fastest growing segment."
    ],
    [
        "http://localhost:8000/margin_comparison.png",
        "APX operating margin of 44% leads all peers by 13 percentage points."
    ],
    [
        "http://localhost:8000/stock_price.png",
        "APX stock price over 24 months. Cup and Handle formation targeting $1,450 breakout."
    ],
    [
        "http://localhost:8000/rd_spend.png",
        "R&D investment grew 38% YoY. Bio-Interface research saw the highest growth at +95%."
    ],
    [
        "http://localhost:8000/datacenter_capacity.png",
        "APX operates 142 data centers across 6 regions. Rapid expansion in Middle East and Africa."
    ],
    [
        "http://localhost:8000/pue_trend.png",
        "APX PUE improved from 1.42 to a world-record 1.008 following Deep-Frost deployment."
    ],
    [
        "http://localhost:8000/market_share.png",
        "APX IaaS market share grew from 18% in 2020 to 62% in 2025."
    ],
    [
        "http://localhost:8000/latency_scatter.png",
        "APX clusters achieve 0.12ms median latency at 4,200 tokens/watt vs industry 4.5ms at 850."
    ],
    [
        "http://localhost:8000/cortex_bridge.png",
        "Cortex-Bridge Phase II results. 92% motor control restoration vs 12% baseline."
    ],
    [
        "http://localhost:8000/capital_waterfall.png",
        "Of $68.2B net income, $60B returns to shareholders — largest capital return in tech history."
    ],
    [
        "http://localhost:8000/headcount.png",
        "Revenue per employee increased from $1.1M to $2.7M despite 4.3x headcount growth."
    ]
]

async def run_test():
    """Executes the formatting and PDF conversion test."""
    logger.info("Starting report formatting test...")
    
    html_output = await format_report(TEXT_BLOCKS, IMAGES, "red")
    
    if not html_output or html_output.startswith("{\"error\""):
        logger.error(f"Formatting FAILED: {html_output}")
    else:
        logger.info("Formatting successful. Proceeding to PDF conversion...")
        try:
            await html_to_pdf(html_output, "test_report.pdf")
            logger.info("SUCCESS! Report created as 'test_report.pdf'")
        except Exception as e:
            logger.error(f"PDF conversion FAILED: {e}")


async def stress_test():
    """Executes the formatting and PDF conversion test."""
    i = 1
    while (True):
        logger.info("Starting report formatting test...")
        
        html_output = await format_report(TEXT_BLOCKS, IMAGES, "red")

        if not html_output or html_output.startswith("{\"error\""):
            logger.error(f"Formatting FAILED: {html_output}")
            return
        else:
            logger.info("Formatting successful. Proceeding to PDF conversion...")
            try:
                await html_to_pdf(html_output, f"test_report{i}.pdf")
                logger.info("SUCCESS! Report created as 'test_report.pdf'")
            except Exception as e:
                logger.error(f"PDF conversion FAILED: {e}")
        i += 1

async def main():
    """Main entry point for the test script."""
    await run_test()
    # await stress_test()

if __name__ == "__main__":
    asyncio.run(main())

