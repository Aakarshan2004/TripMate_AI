# ✈️ TripMate AI — Multi-Agent AI Travel Planner

TripMate AI is an **AI-powered multi-agent travel planning application** that takes a user's natural-language travel request and coordinates multiple specialized agents to build a complete trip plan.

The project uses **LangGraph** for agent orchestration, **Groq** for LLM inference, **MCP (Model Context Protocol)** for external tools, **FastAPI** for the backend API, **PostgreSQL** for persistent LangGraph state/checkpointing, and **React + Vite + Tailwind CSS** for the frontend.

> **Important:** TripMate AI is a travel-planning and decision-support application. External provider availability and API limits can affect flight results. The application does not claim to book flights or guarantee live fares.

---

## 📌 Table of Contents

- [Project Overview](#-project-overview)
- [Why This Project](#-why-this-project)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Multi-Agent Workflow](#-multi-agent-workflow)
- [Agents](#-agents)
- [MCP Integrations](#-mcp-integrations)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [How the Request Flows](#-how-the-request-flows)
- [Prerequisites](#-prerequisites)
- [Installation](#-installation)
- [PostgreSQL Setup](#-postgresql-setup)
- [API Keys](#-api-keys)
- [Environment Variables](#-environment-variables)
- [Running the Backend](#-running-the-backend)
- [Running the Frontend](#-running-the-frontend)
- [Using the Application](#-using-the-application)
- [API Endpoints](#-api-endpoints)
- [Human-in-the-Loop Approval](#-human-in-the-loop-approval)
- [Database and Persistence](#-database-and-persistence)
- [MCP and uvx Setup](#-mcp-and-uvx-setup)
- [Flight Data Limitations](#-flight-data-limitations)
- [Troubleshooting](#-troubleshooting)
- [Security Notes](#-security-notes)
- [Development Notes](#-development-notes)
- [Future Improvements](#-future-improvements)
- [Resume Description](#-resume-description)
- [License](#-license)

---

# 🌍 Project Overview

Planning a trip usually requires searching multiple sources:

- Flights
- Hotels
- Weather
- Budget
- Daily itinerary
- Travel constraints

TripMate AI combines these tasks into a single workflow.

A user can enter a request such as:

> "Plan a 3-day trip from Mumbai to Delhi starting on October 20, 2026."

The system analyzes the request and coordinates specialized agents to collect information and generate a structured travel plan.

The workflow is implemented as a **LangGraph state graph**, allowing the application to maintain shared state between agents and persist the workflow using PostgreSQL.

---

# 🎯 Why This Project?

The main goal of TripMate AI is to demonstrate how a real-world AI application can be built using:

- Multi-agent systems
- LLM orchestration
- LangGraph
- MCP
- External APIs/tools
- FastAPI
- PostgreSQL
- React
- Human-in-the-loop workflows

Instead of asking one LLM to perform every task, TripMate AI divides the problem into specialized agents.

This makes the architecture easier to extend and debug.

---

# ✨ Key Features

### 🤖 Multi-Agent AI Workflow

The application contains specialized agents for:

- Flight planning
- Hotel discovery
- Weather information
- Budget estimation
- Itinerary generation

### 🧠 LangGraph Orchestration

LangGraph controls:

- Agent execution
- Shared state
- Conditional routing
- Workflow sequencing
- Human approval
- Resume/revision flow

### 🔌 MCP Tool Integration

The project uses Model Context Protocol servers for external capabilities including:

- Tavily search
- AviationStack flight information
- Local weather tools

### 🏨 Hotel Search

Hotel information is collected through Tavily search and transformed into structured hotel data containing fields such as:

- Hotel name
- Area
- Rating
- Reviews
- Price
- Amenities
- Source URL

### 🌦️ Weather Information

The weather MCP server provides:

- Current temperature
- Feels-like temperature
- Humidity
- Wind
- Weather conditions
- Forecast information

### 💰 Budget Estimation

The budget agent combines available trip information and produces a trip-level budget estimate.

Where live pricing is unavailable, estimates are explicitly treated as estimates rather than confirmed prices.

### 🗓️ Structured Itinerary

The itinerary agent generates a day-by-day plan with sections such as:

- Morning
- Afternoon
- Evening
- Tips

### 👤 Human-in-the-Loop

Before finalizing the plan, the user can:

- Approve the generated plan
- Reject it
- Provide revision feedback

### 💾 PostgreSQL Persistence

LangGraph state/checkpoints are stored in PostgreSQL using:

`langgraph-checkpoint-postgres`

This allows the workflow to resume using a `thread_id`.

### 🎨 React Dashboard

The frontend displays separate sections for:

- Workflow progress
- Flights
- Hotels
- Weather
- Budget
- Itinerary
- Human approval

---

# 🏗️ Architecture

```text
                         ┌─────────────────────┐
                         │      React UI       │
                         │  Vite + TypeScript  │
                         └──────────┬──────────┘
                                    │
                              HTTP / REST
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │       FastAPI       │
                         │    REST Backend     │
                         └──────────┬──────────┘
                                    │
                                    ▼
                         ┌─────────────────────┐
                         │      LangGraph      │
                         │  Agent Orchestrator │
                         └──────────┬──────────┘
                                    │
              ┌─────────────────────┼─────────────────────┐
              │                     │                     │
              ▼                     ▼                     ▼
        Flight Agent           Hotel Agent          Weather Agent
              │                     │                     │
              ▼                     ▼                     ▼
        AviationStack              Tavily            Weather MCP
              │
              │
              └──────────────┐
                             │
              ┌──────────────┴──────────────┐
              ▼                             ▼
        Budget Agent                  Itinerary Agent
              │                             │
              └──────────────┬──────────────┘
                             ▼
                      Human Approval
                             │
                       ┌─────┴─────┐
                       │           │
                    Approve     Reject
                       │           │
                       ▼           ▼
                  Final Plan   Revision Flow
                             │
                             ▼
                       PostgreSQL
                    LangGraph Checkpoint
```

---

# 🔄 Multi-Agent Workflow

The main workflow is conceptually:

```text
User Request
     │
     ▼
Guardrail
     │
     ▼
Supervisor
     │
     ├──────────────► Flight Agent
     │
     ├──────────────► Hotel Agent
     │
     ├──────────────► Weather Agent
     │
     ├──────────────► Budget Agent
     │
     └──────────────► Itinerary Agent
                             │
                             ▼
                       Human Review
                             │
                  ┌──────────┴──────────┐
                  │                     │
               Approved              Rejected
                  │                     │
                  ▼                     ▼
             Final Response       Revision/Resume
```

The exact routing is handled by the LangGraph graph in the backend.

---

# 🤖 Agents

## 1. Supervisor Agent

The supervisor analyzes the user's request and determines:

- Destination
- Origin
- Travel date
- Trip constraints
- Which specialized agents are required

It also controls the workflow routing.

---

## 2. Flight Agent

The flight agent handles flight-related information.

It uses AviationStack through MCP.

The agent:

1. Extracts origin and destination.
2. Maps supported airport codes.
3. Validates the travel date.
4. Requests flight schedule information.
5. Processes the returned data.
6. Prevents unsupported flight details from being invented.

The application deliberately avoids inventing:

- Flight numbers
- Airlines
- Flight timings
- Exact fares
- Flight duration

when the external provider does not return usable information.

---

## 3. Hotel Agent

The hotel agent uses Tavily through MCP to search for hotel information.

The raw search results are converted into structured data:

```json
{
  "hotels": [
    {
      "name": "Hotel Name",
      "area": "Location",
      "rating": "Rating",
      "reviews": "Number of reviews",
      "price": "Price",
      "amenities": [
        "Wi-Fi",
        "Parking"
      ],
      "url": "Source URL"
    }
  ]
}
```

This structured representation makes it easier for the React frontend to display hotel cards.

---

## 4. Weather Agent

The weather agent uses the project's local weather MCP server.

It can provide:

- Current weather
- Temperature
- Feels-like temperature
- Humidity
- Wind
- Weather description
- Forecast

The weather MCP server communicates with the OpenWeather API.

---

## 5. Budget Agent

The budget agent estimates the approximate trip cost using information available from:

- Flights
- Hotels
- Duration
- General travel expenses

If a live flight price is unavailable, the output should clearly identify the value as an estimate instead of presenting it as a confirmed fare.

---

## 6. Itinerary Agent

The itinerary agent converts the trip information into a structured daily plan.

Example structure:

```json
{
  "days": [
    {
      "day": 1,
      "morning": "...",
      "afternoon": "...",
      "evening": "...",
      "tips": "..."
    }
  ]
}
```

The agent is instructed not to invent unavailable flight details or unsupported hotel information.

---

## 7. Human Approval

Before the final result is accepted, the workflow pauses for human review.

The user can:

### Approve

The generated plan continues to the final response.

### Reject

The user can provide feedback such as:

> "Reduce the hotel budget and add more sightseeing."

The workflow resumes using the same `thread_id`.

---

# 🔌 MCP Integrations

TripMate AI uses MCP to separate tool capabilities from the main agent logic.

## Tavily MCP

Used for web search and hotel discovery.

Capabilities exposed by the current MCP setup include tools such as:

```text
tavily_search
tavily_extract
tavily_crawl
tavily_map
tavily_research
```

---

## AviationStack MCP

Used for flight-related information.

The MCP server exposes tools including:

```text
get_flight_status
flight_arrival_departure_schedule
future_flights_arrival_departure_schedule
flights_with_airline
list_airports
list_airlines
list_routes
```

Some AviationStack capabilities depend on the subscription plan and API limits.

---

## Weather MCP

A local MCP server is implemented in:

```text
backend/client/weather_mcp.py
```

It exposes:

```text
get_current_weather
get_forecast
```

The server uses the OpenWeather API.

---

# 🛠️ Technology Stack

## Backend

- Python 3.13
- FastAPI
- Uvicorn
- LangChain
- LangGraph
- LangGraph PostgreSQL Checkpointer
- LangChain Groq
- MCP
- Tavily
- AviationStack
- OpenWeather
- Psycopg
- PostgreSQL

## Frontend

- React
- TypeScript
- Vite
- Tailwind CSS
- Lucide React

## AI

- Groq-hosted LLM
- LangGraph multi-agent orchestration

## Database

- PostgreSQL

---

# 📁 Project Structure

```text
Tripmate_Ai/
│
├── backend/
│   ├── app/
│   │   ├── agents/
│   │   ├── api/
│   │   │   └── routes.py
│   │   ├── core/
│   │   ├── database/
│   │   ├── graph/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── tools/
│   │   ├── backend.py
│   │   └── main.py
│   │
│   └── client/
│       ├── mcp_client.py
│       └── weather_mcp.py
│
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Sidebar.tsx
│   │   │   ├── Header.tsx
│   │   │   ├── TripInput.tsx
│   │   │   ├── AgentProgress.tsx
│   │   │   ├── FlightCard.tsx
│   │   │   ├── HotelCard.tsx
│   │   │   ├── WeatherCard.tsx
│   │   │   ├── BudgetCard.tsx
│   │   │   ├── ItineraryCard.tsx
│   │   │   ├── ApprovalPanel.tsx
│   │   │   └── ResultsDashboard.tsx
│   │   ├── utils/
│   │   │   └── mcpParser.ts
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   └── vite.config.ts
│
├── myvenv/
├── .env
├── .gitignore
└── requirements.txt
```

---

# 🔁 How a Request Flows

Suppose the user enters:

```text
Plan a 3-day trip from Mumbai to Delhi starting on October 20, 2026.
```

### Step 1 — Frontend

React sends:

```http
POST /api/travel
```

with:

```json
{
  "message": "Plan a 3-day trip from Mumbai to Delhi starting on October 20, 2026."
}
```

### Step 2 — FastAPI

FastAPI receives the request and calls the LangGraph travel workflow.

### Step 3 — Supervisor

The supervisor extracts constraints such as:

```text
Origin: Mumbai
Destination: Delhi
Travel date: 2026-10-20
Duration: 3 days
```

### Step 4 — Specialized Agents

The relevant agents execute:

```text
Flight Agent
Hotel Agent
Weather Agent
Budget Agent
Itinerary Agent
```

### Step 5 — External Tools

Agents communicate with MCP tools:

```text
Flight  → AviationStack
Hotel   → Tavily
Weather → OpenWeather via local MCP
```

### Step 6 — Human Review

The workflow pauses for approval.

### Step 7 — Final Result

The frontend receives structured results and renders the dashboard.

---

# 💻 Prerequisites

Before running the project on another machine, install:

### 1. Python

Recommended:

```text
Python 3.13
```

Verify:

```powershell
python --version
```

or:

```powershell
py --version
```

---

### 2. Node.js

Install a current LTS version.

Verify:

```powershell
node --version
npm --version
```

---

### 3. PostgreSQL

Install PostgreSQL and pgAdmin.

Verify PostgreSQL is running and create a database named:

```text
tripmate
```

---

### 4. Git

Verify:

```powershell
git --version
```

---

### 5. uv / uvx

The AviationStack MCP integration uses `uvx`.

Install uv from the official Astral distribution or using your system package manager.

Verify:

```powershell
uv --version
uvx --version
```

If `uvx` is not recognized after installation, restart the terminal so the updated PATH is loaded.

---

# 🚀 Installation

## 1. Clone the Repository

```powershell
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd Tripmate_Ai
```

---

# 🐍 2. Create the Python Virtual Environment

From the project root:

```powershell
py -3.13 -m venv myvenv
```

Activate it:

```powershell
.\myvenv\Scripts\activate.ps1
```

If PowerShell blocks script execution, run:

```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

Then activate again:

```powershell
.\myvenv\Scripts\activate.ps1
```

---

# 📦 3. Install Backend Dependencies

```powershell
pip install -r requirements.txt
```

Verify:

```powershell
pip list
```

---

# 🐘 PostgreSQL Setup

Open PostgreSQL/pgAdmin.

Create a database:

```text
tripmate
```

Default local connection generally looks like:

```text
Host: localhost
Port: 5432
Database: tripmate
User: postgres
Password: <your PostgreSQL password>
```

The project uses a PostgreSQL connection string:

```text
postgresql://postgres:<PASSWORD>@localhost:5432/tripmate
```

Do not commit this password to GitHub.

---

# 🔑 API Keys

TripMate AI requires external services.

You need credentials for:

### Groq

Used by the LangGraph agents for LLM inference.

Create a Groq API key from your Groq account/dashboard.

---

### Tavily

Used for web search and hotel discovery.

Create a Tavily API key from your Tavily account.

---

### OpenWeather

Used by the local weather MCP server.

Create an OpenWeather API key.

---

### AviationStack

Used for flight information.

Create an AviationStack API key.

> AviationStack results depend on the API subscription, endpoint availability and rate limits.

---

# 🔐 Environment Variables

Create a `.env` file in the **project root**:

```text
Tripmate_Ai/
├── .env
├── backend/
├── frontend/
└── requirements.txt
```

Add:

```env
GROQ_API_KEY=your_groq_api_key
TAVILY_API_KEY=your_tavily_api_key

DATABASE_URL=postgresql://postgres:YOUR_PASSWORD@localhost:5432/tripmate

OPENWEATHER_API_KEY=your_openweather_api_key
AVIATION_STACK_API_KEY=your_aviationstack_api_key
```

Replace every placeholder with your own credentials.

### Never commit `.env`

The repository already ignores:

```text
.env
```

---

# 🔍 Verify PostgreSQL Connection

From the activated virtual environment:

```powershell
python -c "import psycopg; from dotenv import load_dotenv; import os; load_dotenv(); conn=psycopg.connect(os.getenv('DATABASE_URL')); print('PostgreSQL connection: OK'); conn.close()"
```

Expected:

```text
PostgreSQL connection: OK
```

---

# 🔌 Verify MCP Tools

The project uses three MCP integrations:

```text
Tavily
AviationStack
Weather
```

Make sure:

```powershell
uvx --version
```

works before starting the backend.

The MCP client automatically loads the required environment variables from the root `.env`.

---

# ▶️ Running the Backend

Open Terminal 1.

```powershell
cd D:\Tripmate_Ai
.\myvenv\Scripts\activate.ps1
```

Then:

```powershell
cd backend
uvicorn app.main:app --reload
```

Expected output will indicate that Uvicorn is running.

The backend will normally be available at:

```text
http://127.0.0.1:8000
```

---

# ❤️ Health Check

Open:

```text
http://127.0.0.1:8000/health
```

Expected response:

```json
{
  "status": "ok",
  "message": "TripMate AI API is running"
}
```

---

# 📚 Swagger API Documentation

FastAPI automatically provides interactive API documentation.

Open:

```text
http://127.0.0.1:8000/docs
```

You can test API endpoints directly from Swagger.

---

# ▶️ Running the Frontend

Open Terminal 2.

```powershell
cd D:\Tripmate_Ai\frontend
npm install
npm run dev
```

Vite will provide a local URL, normally:

```text
http://localhost:5173
```

Open that URL in your browser.

---

# 🖥️ Using the Application

1. Start PostgreSQL.
2. Start the backend.
3. Start the frontend.
4. Open the Vite URL.
5. Enter a travel request.
6. Submit the request.
7. Wait for the multi-agent workflow.
8. Review:
   - Flights
   - Hotels
   - Weather
   - Budget
   - Itinerary
9. Approve the plan or request changes.

---

# 🔗 API Endpoints

## `GET /health`

Checks whether the backend is running.

Example:

```http
GET http://127.0.0.1:8000/health
```

---

## `POST /api/travel`

Starts a new travel-planning workflow.

Request:

```json
{
  "message": "Plan a 3-day trip from Mumbai to Delhi starting on October 20, 2026.",
  "thread_id": null
}
```

`thread_id` can be supplied when continuing an existing conversation/workflow.

---

## `POST /api/travel/approve`

Approves or rejects a generated plan.

Request:

```json
{
  "thread_id": "your-thread-id",
  "approved": true,
  "feedback": ""
}
```

For a rejection:

```json
{
  "thread_id": "your-thread-id",
  "approved": false,
  "feedback": "Reduce the hotel budget and add more sightseeing."
}
```

Feedback is required when rejecting a plan.

---

# 👤 Human-in-the-Loop Workflow

TripMate AI does not blindly finalize the generated plan.

The workflow can pause at the approval stage.

### Approve

```text
Draft Plan
    ↓
Human Approval
    ↓
Approve
    ↓
Final Response
```

### Request Changes

```text
Draft Plan
    ↓
Human Approval
    ↓
Reject + Feedback
    ↓
Resume Existing Thread
    ↓
Revised Plan
```

PostgreSQL stores the LangGraph checkpoints needed to resume the workflow.

---

# 💾 Database and Persistence

The project originally used MongoDB in the reference implementation.

This implementation uses:

```text
PostgreSQL
```

with:

```text
langgraph-checkpoint-postgres
```

The backend initializes the PostgreSQL checkpointer and uses it when compiling the LangGraph workflow.

This allows the application to persist graph state associated with a workflow/thread.

The database is therefore not simply being used as a traditional CRUD database; it is primarily used for **LangGraph workflow persistence/checkpointing**.

---

# 🧩 Important MCP Setup

The MCP client is located at:

```text
backend/client/mcp_client.py
```

The local weather MCP server is:

```text
backend/client/weather_mcp.py
```

The weather MCP server is started/used as part of the MCP integration.

The AviationStack integration uses `uvx`, so `uvx` must be available in the system PATH.

If you install uv after opening a terminal, close and reopen the terminal before testing:

```powershell
uvx --version
```

---

# ✈️ Flight Data Limitations

Flight information depends on the configured AviationStack provider.

There are two important limitations:

### Provider/API Limits

AviationStack can return errors such as:

```text
rate_limit_reached
```

when the API quota/rate limit is reached.

### Unsupported/Unavailable Data

If the provider does not return usable flight information, TripMate AI intentionally does **not** fabricate:

- Flight numbers
- Airlines
- Exact departure times
- Exact arrival times
- Exact fares
- Flight duration

Instead, the UI can show:

```text
Live flight data unavailable
```

This is intentional and is safer than presenting generated information as real flight data.

---

# 🏨 Hotel Data

Hotel information is obtained through web search and is therefore dependent on:

- Search results
- Source availability
- Search provider response
- Information present on the returned pages

Hotel cards can include:

```text
Name
Area
Rating
Reviews
Price
Amenities
Source URL
```

Prices shown by third-party sources should be treated as indicative and may change.

---

# 🌦️ Weather Data

Weather information is dependent on OpenWeather availability.

Weather is inherently time-sensitive, so users should verify conditions again before actual travel.

---

# 💰 Budget Data

The budget section is an estimate.

It should not be interpreted as a confirmed booking quote.

If a live flight fare is unavailable, the application should not present an estimated value as a confirmed fare.

---

# 🐛 Troubleshooting

## `uvx is not recognized`

Check:

```powershell
uvx --version
```

If it fails:

1. Install uv.
2. Restart PowerShell.
3. Run:

```powershell
uvx --version
```

---

## PostgreSQL connection error

Check:

```text
PostgreSQL service is running
Database name = tripmate
Username is correct
Password is correct
Port = 5432
DATABASE_URL is correct
```

Example:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/tripmate
```

---

## `.env` not loading

Make sure `.env` is here:

```text
Tripmate_Ai/.env
```

not:

```text
Tripmate_Ai/backend/.env
```

unless the code is intentionally changed to use a different location.

---

## Backend import error

Run the backend from:

```powershell
cd Tripmate_Ai\backend
```

Then:

```powershell
uvicorn app.main:app --reload
```

---

## Frontend cannot connect to backend

Make sure both servers are running:

```text
Frontend → http://localhost:5173
Backend  → http://127.0.0.1:8000
```

Also check the browser console for CORS or network errors.

---

## Hotel cards are empty

Check:

- Tavily API key
- Tavily MCP connection
- Backend logs
- Search results returned by Tavily

---

## Weather is unavailable

Check:

- `OPENWEATHER_API_KEY`
- Weather MCP startup
- Backend terminal logs

---

## Flight data is unavailable

Check:

- `AVIATION_STACK_API_KEY`
- AviationStack subscription
- API rate limits
- MCP connection
- `uvx --version`

Remember that an unavailable flight provider does not mean the application itself is broken.

---

# 🔒 Security Notes

Never commit API keys or database passwords.

The following file must remain private:

```text
.env
```

The `.gitignore` already contains:

```gitignore
.env
myvenv/
__pycache__/
```

If an API key is accidentally pushed to GitHub:

1. Revoke the exposed key.
2. Generate a new key.
3. Update `.env`.
4. Remove the secret from Git history if necessary.

Do not rely only on deleting the key from the latest commit because Git history can still contain old secrets.

---

# 🧪 Recommended Testing Order

When setting up the project on a new machine, test in this order:

### 1. Python

```powershell
python --version
```

### 2. Node

```powershell
node --version
npm --version
```

### 3. PostgreSQL

```text
Database: tripmate
```

### 4. Environment

Confirm `.env` exists.

### 5. uvx

```powershell
uvx --version
```

### 6. Python dependencies

```powershell
pip install -r requirements.txt
```

### 7. Backend

```powershell
cd backend
uvicorn app.main:app --reload
```

### 8. Health check

```text
http://127.0.0.1:8000/health
```

### 9. Swagger

```text
http://127.0.0.1:8000/docs
```

### 10. Frontend

```powershell
cd frontend
npm install
npm run dev
```

### 11. End-to-end test

Submit a complete travel request from the frontend.

---

# 🧑‍💻 Development Notes

The project is intentionally separated into:

```text
Frontend
   ↓
FastAPI
   ↓
LangGraph
   ↓
Agents
   ↓
MCP Tools
   ↓
External APIs
```

This separation makes it possible to change one part without rewriting the entire application.

For example:

- React can be redesigned without changing the agents.
- A different LLM provider can be introduced without redesigning the frontend.
- New agents can be added to LangGraph.
- Additional MCP servers can be connected.
- PostgreSQL can continue handling workflow persistence.

---

# 🚀 Future Improvements

Possible future improvements include:

- More reliable live flight provider integration
- Flight booking integration
- Hotel booking integration
- User authentication
- Saved trips
- User profiles
- Currency conversion
- Maps and route visualization
- Calendar integration
- Email trip summaries
- Streaming agent progress
- Better budget calculation
- More destination-specific recommendations
- More robust error handling
- Production deployment
- Automated tests
- CI/CD
- Observability and logging

---

# 📊 Example User Request

```text
Plan a 4-day trip from Mumbai to Delhi starting on
October 20, 2026.

I want a comfortable hotel, moderate budget,
good sightseeing options and a day-wise itinerary.
```

TripMate AI can then coordinate:

```text
Supervisor
    ↓
Flight
Hotel
Weather
Budget
Itinerary
    ↓
Human Review
    ↓
Final Travel Plan
```

---

# 🏆 Resume Description

### TripMate AI — Multi-Agent AI Travel Planner

**Suggested resume bullets:**

- Built a LangGraph-based multi-agent travel planner using Groq LLMs, MCP, FastAPI and PostgreSQL.
- Integrated specialized agents for flights, hotels, weather, budgeting and itinerary generation using external MCP tools.
- Implemented PostgreSQL-backed LangGraph state persistence and a human-in-the-loop approval/revision workflow.
- Developed a React + TypeScript dashboard to visualize agent progress and structured travel recommendations.

---

# 📌 Important Project Claims

For accurate project positioning, the application should be described as a:

> **Multi-Agent AI Travel Planner**

It is appropriate to claim:

- Multi-agent orchestration
- LangGraph workflow
- MCP integrations
- Hotel search
- Weather information
- Budget estimation
- Itinerary generation
- PostgreSQL-backed state persistence
- Human-in-the-loop approval
- FastAPI backend
- React frontend

Avoid claiming:

- Guaranteed live flight availability
- Guaranteed live flight fares
- Actual flight booking
- Actual hotel booking
- Guaranteed travel prices

unless those capabilities are separately implemented and verified.

---

# 📄 License

Add the license you want to use for this repository.

For example, if you choose MIT, create a `LICENSE` file containing the MIT License.

---

# ⭐ Project Summary

TripMate AI demonstrates how a modern AI application can combine:

```text
LLMs
+
LangGraph
+
MCP
+
External APIs
+
FastAPI
+
PostgreSQL
+
React
```

to create an end-to-end intelligent travel planning system.

The key idea is not simply generating a response with an LLM, but building a **stateful, tool-using, multi-agent workflow with human oversight**.
