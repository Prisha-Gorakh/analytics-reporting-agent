# Analytics Reporting Agent

A conversational analytics reporting system built on **ClickHouse** and **LibreChat**. Ask a question in plain English, get a live data answer, a styled PDF report, or have it delivered to your inbox — all from a single chat interface.

![Architecture](architecture.png)

---

## What it does

| You say | What happens |
|---|---|
| *"Which UTM sources bring the most users?"* | Query Agent answers directly in chat |
| *"Generate a PDF report of UTM sources"* | Query Agent → Report Agent → download link |
| *"Email me a UTM source report"* | Query Agent → Report Agent → Email Agent → inbox |

---

## Stack

| Component | Role |
|---|---|
| [LibreChat](https://librechat.ai) | Chat interface and agent orchestration |
| [ClickHouse](https://clickhouse.com) | Analytics database |
| [ClickHouse MCP](https://github.com/ClickHouse/mcp-clickhouse) | Connects Query Agent to ClickHouse |
| [html2pdf MCP](https://github.com/jesamkim/html2pdf) | Converts HTML template to PDF |
| [nginx](https://nginx.org) | Serves generated PDFs |
| [Resend](https://resend.com) | Email delivery |
| [Grafana](https://grafana.com) | Live dashboard embedded in LibreChat |
| [Langfuse](https://langfuse.com) | LLM observability and tracing |

---

## Prerequisites

- Docker and Docker Compose
- Python 3.8+ (for data generation)
- A [Resend](https://resend.com) account and API key
- A [Langfuse](https://langfuse.com) account (optional, for tracing)

---

## Data schema

Two tables power the system:

```sql
-- analytics.events
-- Stores every user interaction
CREATE TABLE analytics.events
(
    user_id      String,
    session_id   String,
    event_name   String,          -- view_homepage, view_product_page, view_cart,
                                  -- view_checkout, view_purchase, click,
                                  -- rage_click, form_error, scroll
    timestamp    DateTime64,
    page_url     String,
    device       LowCardinality(String),   -- desktop, mobile, tablet
    country      LowCardinality(String),   -- US, IN, GB, DE, CA, AU, FR
    utm_source   LowCardinality(String)    -- google, facebook, direct, email, twitter
)
ENGINE = MergeTree()
ORDER BY (utm_source, device, timestamp);

-- analytics.sessions
-- Session-level aggregates
CREATE TABLE analytics.sessions
(
    session_id    String,
    user_id       String,
    session_start DateTime64,
    session_end   DateTime64,
    event_count   UInt32,
    entry_page    String,
    exit_page     String,
    device        LowCardinality(String),
    country       LowCardinality(String),
    utm_source    LowCardinality(String)
)
ENGINE = MergeTree()
ORDER BY (session_start, device, country);
```

---

## Agent prompts

Each agent prompt is in the `agents/` folder. They are plain markdown files — paste the contents directly into the LibreChat agent system prompt field.

- `agents/query_agent.md` — queries ClickHouse, answers or hands off
- `agents/report_agent.md` — fills HTML template, generates PDF
- `agents/email_agent.md` — sends PDF link via Resend

The HTML report template used by the Report Agent is in `templates/report_template.txt`.

---

## Grafana dashboard

Grafana is not included in this docker-compose but can be connected to the same ClickHouse instance as a data source. To embed it inside LibreChat, add an iframe in your LibreChat configuration pointing to your Grafana dashboard URL.

---

## Observability with Langfuse

If Langfuse credentials are set in `.env`, LibreChat will automatically send traces for every agent interaction. No custom instrumentation needed.

Traces include:
- Which agent handled each step
- Prompt and response at each stage
- Token usage and cost per step
- End-to-end latency

---



## Project structure

```
analytics-reporting-agent/
├── README.md
├── docker-compose.yml
├── librechat.yaml
├── .env.example
├── .gitignore
├── data/
│   ├── generate_data.py
│   └── requirements.txt
├── html2pdf/
│   └── dist/
├── agents/
│   ├── query_agent.md
│   ├── report_agent.md
│   └── email_agent.md
└── architecture.png
```

---
## Acknowledgements

- [html2pdf MCP](https://github.com/jesamkim/html2pdf) by [jesamkim](https://github.com/jesamkim) — HTML to PDF conversion server using Puppeteer. The `html2pdf/` directory is based on this open source project.

---

## License

MIT
