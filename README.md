# FinRLExtention

FinRLExtention is a powerful financial analysis and report generation platform that leverages the Model Context Protocol (MCP) and multiple AI backends (Gemini, Claude, Perplexity) to provide deep stock research, interactive charts, and professionally formatted PDF reports.

## Features

- **Deep Stock Research**: Integrated with Perplexity AI for real-time market data and comprehensive equity research.
- **Dynamic Chart Generation**: Automated creation of technical and fundamental charts using Matplotlib.
- **AI-Powered Formatting**: Professional HTML/PDF report generation using Claude for high-quality layout and styling.
- **MCP Architecture**: Modular design using Model Context Protocol (MCP) to separate research, charting, and formatting services.
- **Interactive Web UI**: Modern React-based frontend for chatting with the AI and previewing generated reports.
- **Automated PDF Export**: Pixel-perfect PDF conversion using Playwright.

## Project Structure

```
FinRLExtention/
├── config/                 # Configuration files
│   ├── config.yml          # Main API keys and model settings (User created)
│   └── mcpservers.yml      # MCP server definitions
├── reports/                # Generated HTML and PDF reports
├── src/
│   ├── backend/            # FastAPI backend and MCP client
│   │   ├── app.py          # Main FastAPI application
│   │   ├── generate_report.py # CLI tool for report generation
│   │   ├── mcp_client.py   # Gemini-based MCP client
│   │   └── mcp_servers/    # Specialized MCP services
│   │       ├── mcp_research/ # Perplexity-based research
│   │       ├── mcp_chart_generation/ # Matplotlib charting
│   │       └── mcp_formatting/ # Claude-based HTML formatting
│   └── frontend/           # React + Vite frontend
│        ├── public/        # Images for frontend
│        └── src/
│           ├── App.css     # Static styles for the frontend
│           ├── App.jsx     # Loads the frontend
│           ├── Frontend.jsx # Frontend functionality
│           ├── index.css   # Basic page styles
│           ├── main.jsx    # Where the frontend runs from
│           └── PdfPreviewOverlay.jsx # PDF preview overlay styles and functionality
├── requirements.txt        # Python dependencies
└── README.md
```

## Prerequisites

- Python 3.10+
- Node.js & npm (for frontend)
- API Keys for:
  - Google Gemini (Main Orchestrator)
  - Anthropic Claude (Formatting)
  - Perplexity (Research)

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd FinRLExtention
   ```

2. **Set up the Python environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Install Playwright browser** (required for PDF generation — the pip package alone is not enough):
   ```bash
   playwright install chromium
   ```

4. **Set up the Frontend**:
   ```bash
   cd src/frontend
   npm install
   cd ../..
   ```

## Configuration

1. Create a `config/config.yml` file based on the following structure:

   ```yaml
   gemini:
     api_key: "YOUR_GOOGLE_API_KEY"
     model: "gemini-2.5-flash"
     temperature: 0.7

   claude:
     api_key: "YOUR_ANTHROPIC_API_KEY"
     model: "claude-sonnet-4-6"
     temperature: 0.7
     max_output_tokens: 16000

   perplexity:
     api_key: "YOUR_PERPLEXITY_API_KEY"
     model: "sonar"
     temperature: 0.7
   ```

   > The same structure is also required in `src/backend/mcp_servers/mcp_formatting/config.yml` for the formatting server.

2. Verify `config/mcpservers.yml` points to the correct server paths.

## Running the Application

### 1. Start the Backend
From the project root:
```bash
python -m uvicorn src.backend.app:app --reload --port 8000
```

### 2. Start the Frontend
In a new terminal:
```bash
cd src/frontend
npm run dev
```
The frontend will typically be available at `http://localhost:5173`.
