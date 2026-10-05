import os



import certifi



from dotenv import load_dotenv







load_dotenv()



os.environ["SSL_CERT_FILE"] = certifi.where()



os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()







from typing import Any, TypedDict, Annotated



import operator



import uuid



import asyncio



import json



import re



import ast



import time

from datetime import datetime



import psycopg



from psycopg.rows import dict_row



from langgraph.graph import StateGraph, START, END



from langgraph.checkpoint.postgres import PostgresSaver



from langgraph.types import Command, interrupt



from langchain_core.messages import (



    AnyMessage,



    HumanMessage,



    AIMessage,



    SystemMessage,



)



from langchain_groq import ChatGroq







from client.mcp_client import (



    tavily_mcp_search,



    aviation_mcp_call,



    extract_destination,



    forecast_mcp_search,



    weather_mcp_search,



)











DATABASE_URL = os.getenv("DATABASE_URL")







if not DATABASE_URL:



    raise ValueError("DATABASE_URL is missing. Please add it to your .env file.")











GROQ_API_KEY = os.getenv("GROQ_API_KEY")







if not GROQ_API_KEY:



    raise ValueError("GROQ_API_KEY is missing. Please add it to your .env file.")







GROQ_TPM_LIMIT = 8000



GROQ_MAX_OUTPUT_TOKENS = 2200  



GROQ_MAX_INPUT_TOKENS = 4800   



_tpm_events: list[tuple[float, int]] = []







# =========================



# LLM - original model kept



# =========================



llm = ChatGroq(



    model="openai/gpt-oss-120b",



    api_key=GROQ_API_KEY,



    max_tokens=GROQ_MAX_OUTPUT_TOKENS,



)







# =========================



# State



# =========================



class TravelState(TypedDict, total=False):



    messages: Annotated[list[AnyMessage], operator.add]



    user_query: str







    # Supervisor + guardrail state



    guardrail_allowed: bool



    guardrail_reason: str



    selected_agents: list[str]



    trip_constraints: dict[str, Any]



    supervisor_reasoning: str







    # Original specialist results



    flight_results: str



    hotel_results: str



    weather_results: str



    itinerary: str







    # New budget + HITL state



    budget_results: str



    approval_request: str



    approved: bool



    human_feedback: str



    final_response: str







    llm_calls: int











# =========================



# Shared helpers



# =========================



KNOWN_AGENTS = {



    "flight_agent",



    "hotel_agent",



    "weather_agent",



    "budget_agent",



    "itinerary_agent",



}







AGENT_ORDER = [



    "flight_agent",



    "hotel_agent",



    "weather_agent",



    "budget_agent",



    "itinerary_agent",



]











def _estimate_tokens(text: str) -> int:



    """Conservative token estimate so we stay under Groq TPM, not just char length."""



    return max(1, (len(text or "") + 2) // 3)











def _clip_text(text: str, max_chars: int) -> str:



    text = text or ""



    if max_chars <= 0:



        return ""



    if len(text) <= max_chars:



        return text



    marker = "\n...[truncated to fit model token limit]..."



    keep = max(0, max_chars - len(marker))



    return text[:keep].rstrip() + marker











def _clip_to_tokens(text: str, max_tokens: int) -> str:



    return _clip_text(text or "", max(0, max_tokens) * 3)











def _is_token_limit_error(exc: BaseException) -> bool:



    status = getattr(exc, "status_code", None) or getattr(exc, "status", None)



    if status in (413, 429):



        return True



    text = str(exc).lower()



    return any(



        marker in text



        for marker in (



            "413",



            "request too large",



            "rate_limit_exceeded",



            "tokens per minute",



            "please reduce your message size",



        )



    )











def _compact_tool_output(data: Any, max_chars: int = 1800) -> str:



    """Keep Tavily / MCP payloads as short notes instead of raw JSON dumps."""



    if data is None:



        return ""







    parsed: Any = data



    if isinstance(data, str):



        stripped = data.strip()



        if stripped.startswith("{") or stripped.startswith("["):



            try:



                parsed = json.loads(stripped)



            except Exception:



                return _clip_text(data, max_chars)



        else:



            return _clip_text(data, max_chars)







    results = None



    if isinstance(parsed, dict):



        results = parsed.get("results") or parsed.get("organic") or parsed.get("data")



    elif isinstance(parsed, list):



        results = parsed







    if isinstance(results, list) and results:



        lines: list[str] = []



        for item in results[:6]:



            if isinstance(item, dict):



                title = str(



                    item.get("title")



                    or item.get("name")



                    or item.get("airline_name")



                    or item.get("airport_name")



                    or ""



                ).strip()



                url = str(item.get("url") or "").strip()



                snippet = str(



                    item.get("content")



                    or item.get("snippet")



                    or item.get("description")



                    or item.get("iata_code")



                    or ""



                ).strip()



                line = " - ".join(part for part in (title, snippet) if part)



                if url:



                    line = f"{line} ({url})" if line else url



                if line:



                    lines.append(f"- {_clip_text(line, 280)}")



            else:



                lines.append(f"- {_clip_text(str(item), 280)}")



        if lines:



            return _clip_text("\n".join(lines), max_chars)







    return _clip_text(str(parsed), max_chars)











def _reserve_tpm(estimated_tokens: int) -> None:



    """Stay under Groq's rolling 60-second token budget across graph steps."""



    global _tpm_events



    now = time.monotonic()



    _tpm_events = [(stamp, count) for stamp, count in _tpm_events if now - stamp < 60]



    used = sum(count for _, count in _tpm_events)



    headroom = GROQ_TPM_LIMIT - 400



    if used + estimated_tokens <= headroom:



        _tpm_events.append((now, estimated_tokens))



        return







    oldest = min(stamp for stamp, _ in _tpm_events) if _tpm_events else now



    wait = max(0.5, 61 - (now - oldest))



    print(



        f"Pacing Groq TPM: waiting {wait:.1f}s "



        f"(used ~{used}, next ~{estimated_tokens})",



        flush=True,



    )



    time.sleep(wait)



    _reserve_tpm(estimated_tokens)











def _llm_text(system_prompt: str, user_prompt: str) -> str:



    system_prompt = system_prompt or ""



    user_prompt = user_prompt or ""



    input_budget = GROQ_MAX_INPUT_TOKENS







    last_error: Exception | None = None



    for attempt in range(4):



        system_fitted = _clip_to_tokens(system_prompt, min(800, input_budget // 4))



        remaining = max(200, input_budget - _estimate_tokens(system_fitted) - 40)



        user_fitted = _clip_to_tokens(user_prompt, remaining)



        _reserve_tpm(



            _estimate_tokens(system_fitted)



            + _estimate_tokens(user_fitted)



            + GROQ_MAX_OUTPUT_TOKENS



        )



        try:



            response = llm.invoke(



                [



                    SystemMessage(content=system_fitted),



                    HumanMessage(content=user_fitted),



                ]



            )



            return _message_text(response.content)



        except Exception as exc:



            last_error = exc



            if not _is_token_limit_error(exc):



                raise



            print(



                f"Groq token limit hit (attempt {attempt + 1}), "



                f"shrinking prompt: {exc}",



                flush=True,



            )



            input_budget = max(800, int(input_budget * 0.55))







    raise last_error or RuntimeError("Groq request exceeded the token limit.")











def _message_text(content: Any) -> str:



    if content is None:



        return ""



    if isinstance(content, str):



        return content



    if isinstance(content, list):



        parts: list[str] = []



        for item in content:



            if isinstance(item, str):



                parts.append(item)



            elif isinstance(item, dict):



                parts.append(str(item.get("text") or item.get("content") or ""))



        return "\n".join(part for part in parts if part)



    return str(content)











def _extract_json_object(text: str) -> str | None:



    """Return the first balanced JSON object embedded in text, if any."""



    if not text or not str(text).strip():



        return None







    cleaned = str(text).strip()







    # Look for fenced code blocks first



    code_block_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned, re.IGNORECASE)



    if code_block_match:



        extracted = code_block_match.group(1).strip()



        if extracted.startswith("{") and extracted.endswith("}"):



            return extracted







    start = -1



    depth = 0



    in_string = False



    escaped = False







    for idx, char in enumerate(cleaned):



        if in_string:



            if escaped:



                escaped = False



            elif char == "\\\\\\\\":



                escaped = True



            elif char == '"':



                in_string = False



            continue







        if char == '"':



            in_string = True



            continue







        if char == "{":



            if depth == 0:



                start = idx



            depth += 1



        elif char == "}":



            if depth > 0:



                depth -= 1



                if depth == 0 and start != -1:



                    return cleaned[start : idx + 1]







    # Fallback to outer braces if string tracking got misaligned by unescaped quotes



    first_brace = cleaned.find("{")



    last_brace = cleaned.rfind("}")



    if first_brace != -1 and last_brace > first_brace:



        return cleaned[first_brace : last_brace + 1]







    return None











def _repair_json_string(candidate: str) -> str:



    cleaned = re.sub(r"//.*", "", candidate)



    cleaned = re.sub(r"\bTrue\b", "true", cleaned)



    cleaned = re.sub(r"\bFalse\b", "false", cleaned)



    cleaned = re.sub(r"\bNone\b", "null", cleaned)



    # Remove trailing commas before closing braces/brackets



    cleaned = re.sub(r",\s*([****\\\**]**}])", r"\1", cleaned)



    return cleaned











def _json_from_llm(text: str) -> dict[str, Any]:



    """Extract and parse the JSON object returned by the model with multiple repair layers."""



    candidate = _extract_json_object(text)



    if candidate is None:



        raise ValueError("The model did not return a JSON object.")







    # 1. Standard parse with strict=False (allows unescaped control characters/newlines in strings)



    try:



        return json.loads(candidate, strict=False)



    except Exception:



        pass







    # 2. Parse after repairing trailing commas, python booleans, comments



    repaired = _repair_json_string(candidate)



    try:



        return json.loads(repaired, strict=False)



    except Exception:



        pass







    # 3. Try ast.literal_eval in case LLM output single-quoted Python dict



    try:



        val = ast.literal_eval(repaired)



        if isinstance(val, dict):



            return val



    except Exception:



        pass







    try:



        val = ast.literal_eval(candidate)



        if isinstance(val, dict):



            return val



    except Exception:



        pass







    # 4. Try regex quote cleanup for unescaped internal quotes



    try:



        fixed_quotes = re.sub(r'(?<=:\s")([^"]*?)"([^"]*?)(?=")', r'&#x31;**\\"**\2', candidate)



        return json.loads(_repair_json_string(fixed_quotes), strict=False)



    except Exception:



        pass







    # Final attempt: let standard strict=False raise the informative error



    return json.loads(candidate, strict=False)











def _empty_constraints() -> dict[str, Any]:



    return {



        "destination": "",



        "origin": "",



        "duration": "",



        "travel_date": "",



        "budget": "",



        "travel_style": "",



        "special_preferences": [],



    }











TRIP_PLAN_JSON_INSTRUCTIONS = """Return strict JSON only. No markdown wrapping.







Schema:



{



  "headline": "Short trip title",



  "overview": "1-2 sentences about the plan",



  "highlights": ["1-2 key highlights"],



  "trip_summary": {



    "destination": "",



    "origin": "",



    "duration": "",



    "travel_style": "",



    "best_for": ""



  },



  "flights": {



    "summary": "Brief route paragraph",



    "route": "Origin → destination",



    "airlines": ["Only airline names explicitly present in provided flight data"],



    "duration": "Only if explicitly available in provided flight data",



    "price_range": "Only provided flight pricing or 'Check live fares'",



    "tips": ["1-2 booking tips"]



  },



  "hotels": [



    {



      "name": "Hotel/stay name",



      "area": "Neighborhood",



      "why": "Why it fits",



      "price_range": "Only provided hotel price or empty string"



    }



  ],



  "weather": {



    "summary": "Feel of the weather",



    "forecast": "Short notes",



    "packing_tips": ["1-2 items to pack"]



  },



  "itinerary": [



    {



      "day": 1,



      "title": "Day theme",



      "morning": "Short plan",



      "afternoon": "Short plan",



      "evening": "Short plan",



      "tips": "One local tip"



    }



  ],



  "budget": {



    "feasible": true,



    "total_estimate": "Total cost estimate",



    "breakdown": [



      {"category": "Flights", "amount": "", "notes": ""}



    ],



    "saving_tips": ["1-2 cost-saving ideas"]



  },



  "recommendations": ["1-2 closing tips"]



}







Style: Warm, concise, second person. Omit sections if data unavailable.



"""











def _extract_structured_plan(text: str) -> dict[str, Any] | None:



    if not text or not str(text).strip():



        return None







    cleaned = str(text).strip()







    try:



        parsed = _json_from_llm(cleaned)



    except Exception:



        return None







    if not isinstance(parsed, dict):



        return None







    useful_keys = {



        "headline",



        "overview",



        "highlights",



        "trip_summary",



        "flights",



        "hotels",



        "weather",



        "itinerary",



        "budget",



        "recommendations",



    }







    # Unwrap if wrapped inside an outer object



    if len(parsed) == 1:



        inner = next(iter(parsed.values()), None)



        if isinstance(inner, dict) and useful_keys & set(inner.keys()):



            parsed = inner







    return parsed if useful_keys & set(parsed.keys()) else None











def _validate_trip_plan_completeness(plan: dict[str, Any]) -> tuple[bool, list[str]]:



    """Check if trip plan JSON has all critical sections populated."""



    missing_sections = []







    # Required sections



    required = ["headline", "overview", "flights", "hotels", "itinerary", "budget"]



    for section in required:



        if not plan.get(section):



            missing_sections.append(section)







    # Check nested completeness



    if plan.get("flights"):



        flights = plan["flights"]



        if isinstance(flights, dict):



            for key in ["route", "airlines", "duration"]:



                if not flights.get(key):



                    missing_sections.append(f"flights.{key}")







    if plan.get("itinerary"):



        itinerary = plan["itinerary"]



        if isinstance(itinerary, list) and len(itinerary) > 0:



            first_day = itinerary[0]



            if isinstance(first_day, dict):



                for key in ["day", "morning", "afternoon", "evening"]:



                    if not first_day.get(key):



                        missing_sections.append(f"itinerary[0].{key}")



        else:



            missing_sections.append("itinerary (empty)")







    if plan.get("budget"):



        budget = plan["budget"]



        if isinstance(budget, dict):



            if "feasible" not in budget or not budget.get("total_estimate"):



                missing_sections.append("budget (incomplete)")







    is_complete = len(missing_sections) == 0



    return is_complete, missing_sections











def _friendly_answer_from_plan(plan: dict[str, Any]) -> str:



    parts: list[str] = []



    headline = str(plan.get("headline") or "").strip()



    overview = str(plan.get("overview") or "").strip()







    if headline:



        parts.append(headline)



    if overview:



        parts.append(overview)







    highlights = plan.get("highlights") or []



    if isinstance(highlights, list) and highlights:



        parts.append("Highlights: " + "; ".join(str(item) for item in highlights[:5]))



    elif isinstance(highlights, str) and highlights.strip():



        parts.append("Highlights: " + highlights.strip())







    return "\n\n".join(parts) if parts else ""















# =========================



# Supervisor Agent + Input Guardrail



# =========================



def supervisor_agent(state: TravelState):



    query = state["user_query"]



    llm_calls = state.get("llm_calls", 0)







    guardrail_prompt = f"""



        Determine whether the following request belongs to travel planning or travel



        information. Valid requests can include destinations, flights, hotels, weather,



        budgets, visas, transportation, sightseeing, food, packing, or itineraries.







        Block clearly unrelated requests and requests asking for harmful or illegal



        instructions. Do not block a valid travel request merely because some details



        are missing.







        Return strict JSON only:



        {{



        "allowed": true,



        "reason": ""



        }}







        User request:



        {query}



        """







    # Fail open on parser/model errors so a temporary JSON-format issue does not



    # break the original travel-planning behavior.



    try:



        guardrail_raw = _llm_text(



            "You are the input guardrail for a travel-planning application. "



            "Return strict JSON only.",



            guardrail_prompt,



        )



        guardrail_result = _json_from_llm(guardrail_raw)



        allowed = bool(guardrail_result.get("allowed", True))



        guardrail_reason = str(guardrail_result.get("reason", "")).strip()



        llm_calls += 1



    except Exception as exc:



        print(f"Guardrail fallback used: {exc}")



        allowed = True



        guardrail_reason = "Guardrail validation fallback allowed the request."







    if not allowed:



        reason = guardrail_reason or (



            "TripMate AI can only help with travel-planning requests. "



            "Please ask about a destination, flight, hotel, weather, budget, "



            "or itinerary."



        )



        return {



            "guardrail_allowed": False,



            "guardrail_reason": reason,



            "selected_agents": [],



            "trip_constraints": _empty_constraints(),



            "supervisor_reasoning": reason,



            "final_response": reason,



            "messages": [AIMessage(content=f"Guardrail blocked request: {reason}")],



            "llm_calls": llm_calls,



        }







    supervisor_prompt = f"""Route work to specialist travel agents.







Available: flight_agent, hotel_agent, weather_agent, budget_agent, itinerary_agent (always include)







Return JSON only:



{{



  "selected_agents": ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"],



  "trip_constraints": {{



    "destination": "",



    "origin": "",



    "duration": "",



    "travel_date": "YYYY-MM-DD or empty if not provided",



    "budget": "",



    "travel_style": "",



    "special_preferences": []



  }},



  "reasoning": "One sentence why these agents"



}}







Travel date rules:

- Extract an explicitly stated travel/start date into travel_date as YYYY-MM-DD.

- If the user does not provide a specific travel date, set travel_date to "".

- Never invent, assume, or infer a travel date such as tomorrow.



User request: {_clip_text(query, 400)}"""







    try:



        supervisor_raw = _llm_text(



            "You route work to travel specialist agents. Return strict JSON only.",



            supervisor_prompt,



        )



        parsed = _json_from_llm(supervisor_raw)



        requested_agents = parsed.get("selected_agents", [])



        selected_agents = [



            name for name in AGENT_ORDER



            if name in requested_agents and name in KNOWN_AGENTS



        ]







        # The itinerary agent integrates whichever specialist results were selected.



        if "itinerary_agent" not in selected_agents:



            selected_agents.append("itinerary_agent")







        constraints = _empty_constraints()



        parsed_constraints = parsed.get("trip_constraints", {})



        if isinstance(parsed_constraints, dict):



            constraints.update(parsed_constraints)







        reasoning = str(parsed.get("reasoning", "")).strip()



        llm_calls += 1



    except Exception as exc:



        print(f"Supervisor fallback used: {exc}")



        # Original workflow behavior is preserved as the fallback.



        selected_agents = AGENT_ORDER.copy()



        constraints = _empty_constraints()



        reasoning = (



            "Supervisor parsing failed, so the original full travel workflow "



            "was selected as a safe fallback."



        )







    return {



        "guardrail_allowed": True,



        "guardrail_reason": guardrail_reason,



        "selected_agents": selected_agents,



        "trip_constraints": constraints,



        "supervisor_reasoning": reasoning,



        "messages": [AIMessage(content="Supervisor created the agent plan.")],



        "llm_calls": llm_calls,



    }











# =========================



# Guardrail blocked response



# =========================



def guardrail_blocked_agent(state: TravelState):



    reason = state.get("final_response") or state.get("guardrail_reason") or (



        "This request was blocked by the travel input guardrail."



    )



    return {



        "final_response": reason,



        "messages": [AIMessage(content=reason)],



    }



# =========================

# Flight Agent

# =========================



FLIGHT_AGENT_PROMPT = """You are a flight expert.



Analyze ONLY the available flight schedule data and give brief,

traveler-friendly flight recommendations.



User query:

{query}



Flight schedule data:

{flight_data}



Cover:

1. Departure and arrival airports

2. Airlines available

3. Flight numbers if available

4. Scheduled timings if available

5. Duration if available

6. Booking advice

7. Clearly state when live airfare prices are unavailable



IMPORTANT:

- Use ONLY information present in the flight schedule data.

- Do NOT invent flight numbers.

- Do NOT invent airline names.

- Do NOT invent prices.

- Do NOT invent departure or arrival times.

- Do NOT claim that a price is live unless the tool provides it.

- If the schedule data is unavailable, clearly say so.

- Do NOT replace unavailable live data with typical or estimated

  flight schedules.

"""





def flight_agent(state: TravelState):



    print("\nINSIDE FLIGHT AGENT\n")



    query = state["user_query"]

    constraints = state.get("trip_constraints", {})



    try:



        # ---------------------------------

        # Get travel information

        # ---------------------------------



        destination = str(

            constraints.get("destination")

            or extract_destination(query)

        ).strip()



        origin = str(

            constraints.get("origin") or ""

        ).strip()



        travel_date = str(

            constraints.get("travel_date") or ""

        ).strip()



        print(

            f"\nFLIGHT ORIGIN: {origin}"

            f"\nFLIGHT DESTINATION: {destination}"

            f"\nFLIGHT DATE: {travel_date}",

            flush=True,

        )



        # ---------------------------------

        # Travel date is required

        # ---------------------------------



        if not travel_date:



            return {

                "flight_results": (

                    "A specific travel date was not provided, "

                    "so live flight schedules cannot be queried. "

                    "Please provide the travel date. "

                    "Live airfare prices are not available through "

                    "the configured AviationStack integration."

                ),

                "messages": [

                    AIMessage(

                        content="Flight information requires a travel date."

                    )

                ],

                "llm_calls": state.get("llm_calls", 0),

            }



        # ---------------------------------

        # Airport mapping

        # ---------------------------------



        airport_codes = {

            "delhi": "DEL",

            "new delhi": "DEL",

            "mumbai": "BOM",

            "bombay": "BOM",

            "bangalore": "BLR",

            "bengaluru": "BLR",

            "hyderabad": "HYD",

            "chennai": "MAA",

            "kolkata": "CCU",

            "pune": "PNQ",

            "goa": "GOI",

            "ahmedabad": "AMD",

            "jaipur": "JAI",

            "lucknow": "LKO",

            "chandigarh": "IXC",

            "srinagar": "SXR",

            "jammu": "IXJ",

            "kochi": "COK",

            "cochin": "COK",

        }



        destination_iata = airport_codes.get(

            destination.lower()

        )



        if not destination_iata:

            raise ValueError(

                f"No airport code mapping available for "

                f"destination: {destination}"

            )



        origin_iata = (

            airport_codes.get(origin.lower())

            if origin

            else None

        )



        if origin and not origin_iata:

            raise ValueError(

                f"No airport code mapping available for "

                f"origin: {origin}"

            )



        # ---------------------------------

        # Validate date

        # ---------------------------------



        parsed_date = datetime.strptime(

            travel_date,

            "%Y-%m-%d",

        ).date()



        today = datetime.now().date()



        if parsed_date < today:

            raise ValueError(

                f"Travel date {travel_date} is in the past. "

                "Please provide a future travel date."

            )



        # ---------------------------------

        # Select AviationStack tool

        # ---------------------------------



        if parsed_date == today:



            schedule_tool = (

                "flight_arrival_departure_schedule"

            )



        else:



            schedule_tool = (

                "future_flights_arrival_departure_schedule"

            )



        flight_sections = []



        origin_schedule_ok = False

        destination_schedule_ok = False



        # ---------------------------------

        # Origin departure schedule

        # ---------------------------------



        if origin_iata:



            try:



                if schedule_tool == (

                    "flight_arrival_departure_schedule"

                ):



                    origin_schedule = asyncio.run(

                        aviation_mcp_call(

                            schedule_tool,

                            {

                                "airport_iata_code": origin_iata,

                                "schedule_type": "departure",

                                "number_of_flights": 10,

                            },

                        )

                    )



                else:



                    origin_schedule = asyncio.run(

                        aviation_mcp_call(

                            schedule_tool,

                            {

                                "airport_iata_code": origin_iata,

                                "schedule_type": "departure",

                                "date": travel_date,

                                "number_of_flights": 10,

                            },

                        )

                    )



                print(

                    "\nORIGIN FLIGHT SCHEDULE:",

                    origin_schedule,

                    flush=True,

                )



                origin_text = _compact_tool_output(

                    origin_schedule,

                    1800,

                )



                # Detect obvious MCP/API failure

                if (

                    '"ok": false' not in origin_text.lower()

                    and '"error"' not in origin_text.lower()

                ):



                    origin_schedule_ok = True



                    flight_sections.append(

                        "Origin departure board:\n"

                        + origin_text

                    )



                else:



                    print(

                        "\nOrigin flight schedule unavailable.",

                        flush=True,

                    )



            except Exception as exc:



                print(

                    f"\nORIGIN FLIGHT ERROR: "

                    f"{type(exc).__name__}: {exc}",

                    flush=True,

                )



        # ---------------------------------

        # Destination arrival schedule

        # ---------------------------------



        try:



            if schedule_tool == (

                "flight_arrival_departure_schedule"

            ):



                destination_schedule = asyncio.run(

                    aviation_mcp_call(

                        schedule_tool,

                        {

                            "airport_iata_code": destination_iata,

                            "schedule_type": "arrival",

                            "number_of_flights": 10,

                        },

                    )

                )



            else:



                destination_schedule = asyncio.run(

                    aviation_mcp_call(

                        schedule_tool,

                        {

                            "airport_iata_code": destination_iata,

                            "schedule_type": "arrival",

                            "date": travel_date,

                            "number_of_flights": 10,

                        },

                    )

                )



            print(

                "\nDESTINATION FLIGHT SCHEDULE:",

                destination_schedule,

                flush=True,

            )



            destination_text = _compact_tool_output(

                destination_schedule,

                1800,

            )



            if (

                '"ok": false' not in destination_text.lower()

                and '"error"' not in destination_text.lower()

            ):



                destination_schedule_ok = True



                flight_sections.append(

                    "Destination arrival board:\n"

                    + destination_text

                )



            else:



                print(

                    "\nDestination flight schedule unavailable.",

                    flush=True,

                )



        except Exception as exc:



            print(

                f"\nDESTINATION FLIGHT ERROR: "

                f"{type(exc).__name__}: {exc}",

                flush=True,

            )



        # ---------------------------------

        # No usable flight data

        # ---------------------------------



        if not origin_schedule_ok and not destination_schedule_ok:



            flight_result = (

                "Live flight schedule data is currently "

                "unavailable from the configured flight provider. "

                "No flight numbers, timings, airlines, or fares "

                "are being estimated or invented. "

                "Please check live flight availability before booking."

            )



            print(

                "\nNo usable flight data. "

                "Skipping flight LLM call.",

                flush=True,

            )



        else:



            # ---------------------------------

            # Generate recommendation only when

            # actual schedule data exists

            # ---------------------------------



            flight_data = _clip_text(

                "\n\n".join(flight_sections),

                3200,

            )



            prompt = FLIGHT_AGENT_PROMPT.format(

                query=_clip_text(query, 800),

                flight_data=flight_data,

            )



            flight_result = _llm_text(

                "You are an expert travel flight planner.",

                prompt,

            )



    except Exception as exc:



        print(

            f"\nFLIGHT AGENT ERROR: "

            f"{type(exc).__name__}: {exc}",

            flush=True,

        )



        flight_result = (

            "Live flight schedule information is currently "

            "unavailable through the configured AviationStack "

            "integration. No estimated flight details are "

            "being presented as live data."

        )



    return {

        "flight_results": flight_result,



        "messages": [

            AIMessage(

                content="Flight recommendations generated"

            )

        ],



        "llm_calls": (

            state.get("llm_calls", 0)

            + (1 if 'flight_data' in locals() else 0)

        ),

    }





## =========================

# Hotel Agent

# =========================

def hotel_agent(state: TravelState):

    print("\nInside Hotel agent\n")



    constraints = state.get("trip_constraints", {})



    destination = constraints.get("destination", "")

    duration = constraints.get("duration", "")

    travel_date = constraints.get("travel_date", "")

    budget = constraints.get("budget", "")



    query = (

        f"Best budget hotels in {destination}, India "

        f"for {duration}, starting {travel_date}, "

        f"for 2 people within a budget of {budget}. "

        f"Include hotel name, area, approximate price per night, "

        f"rating/reviews if available, and key amenities."

    )



    print(f"HOTEL SEARCH QUERY: {query}\n")



    # ---------------------------------------------------------

    # 1. GET RAW HOTEL DATA FROM TAVILY MCP

    # ---------------------------------------------------------



    try:

        raw_hotel_results = asyncio.run(

            tavily_mcp_search(query)

        )



        print("\n========== RAW HOTEL MCP OUTPUT ==========")

        print(raw_hotel_results)

        print("==========================================\n")



    except Exception as exc:

        print(

            f"HOTEL AGENT MCP ERROR: "

            f"{type(exc).__name__}: {exc}",

            flush=True,

        )



        return {

            "hotel_results": json.dumps({

                "hotels": [],

                "error": "Live hotel search is temporarily unavailable."

            }),

            "messages": [

                AIMessage(content="Hotel search was unavailable.")

            ],

            "llm_calls": state.get("llm_calls", 0),

        }



    # ---------------------------------------------------------

    # 2. EXTRACT TEXT FROM MCP RESPONSE

    # ---------------------------------------------------------



    try:

        if isinstance(raw_hotel_results, list):



            text_block = next(

                (

                    item.get("text")

                    for item in raw_hotel_results

                    if isinstance(item, dict)

                    and item.get("type") == "text"

                    and item.get("text")

                ),

                None,

            )



            if text_block:

                tavily_data = json.loads(text_block)

            else:

                tavily_data = {}



        elif isinstance(raw_hotel_results, str):

            tavily_data = json.loads(raw_hotel_results)



        else:

            tavily_data = raw_hotel_results



    except Exception as exc:



        print(

            f"HOTEL JSON PARSE ERROR: "

            f"{type(exc).__name__}: {exc}",

            flush=True,

        )



        tavily_data = {}



    # ---------------------------------------------------------

    # 3. KEEP ONLY USEFUL TAVILY DATA

    # ---------------------------------------------------------



    try:



        search_results = tavily_data.get("results", [])



        compact_sources = []



        for result in search_results[:5]:



            compact_sources.append({

                "title": result.get("title", ""),

                "url": result.get("url", ""),

                "content": result.get("content", "")[:2500],

            })



        hotel_source_text = json.dumps(

            compact_sources,

            ensure_ascii=False,

        )



    except Exception as exc:



        print(

            f"HOTEL SOURCE PREPARATION ERROR: "

            f"{type(exc).__name__}: {exc}",

            flush=True,

        )



        hotel_source_text = "No usable hotel search results."



    # ---------------------------------------------------------

    # 4. GROQ STRUCTURED EXTRACTION

    # ---------------------------------------------------------



    extraction_prompt = f"""

You are a hotel information extraction system.



The following data was retrieved from web search:



{hotel_source_text}



Extract REAL hotel information from the provided sources.



Return ONLY valid JSON.

Do NOT return markdown.

Do NOT explain anything.

Do NOT invent information.



Required format:



{{

  "hotels": [

    {{

      "name": "hotel name",

      "area": "area or location",

      "rating": "rating if available",

      "reviews": "number of reviews if available",

      "price": "price if available",

      "amenities": ["amenity 1", "amenity 2"],

      "url": "source URL"

    }}

  ]

}}



Rules:



1. Only include hotels actually mentioned in the source data.

2. Never invent hotel names.

3. Never invent prices.

4. Never invent ratings.

5. Never invent reviews.

6. If a field is unavailable, use an empty string.

7. Amenities must only contain amenities explicitly mentioned.

8. Use the hotel's actual URL when available.

9. Return at most 5 hotels.

10. Prefer budget/value hotels relevant to the user's request.

"""



    try:



        extraction_response = llm.invoke(

            [

                SystemMessage(

                    content=(

                        "You extract structured hotel data from search results. "

                        "Always return valid JSON only."

                    )

                ),

                HumanMessage(

                    content=extraction_prompt

                ),

            ]

        )



        extracted_text = extraction_response.content



        # Some model responses can contain ```json ... ```

        if isinstance(extracted_text, list):

            extracted_text = "".join(

                str(part) for part in extracted_text

            )



        extracted_text = str(extracted_text).strip()



        if extracted_text.startswith("```"):

            extracted_text = re.sub(

                r"^```(?:json)?\s*",

                "",

                extracted_text,

                flags=re.IGNORECASE,

            )



            extracted_text = re.sub(

                r"\s*```$",

                "",

                extracted_text,

            )



        hotels_data = json.loads(extracted_text)



        # Make sure expected structure exists

        if not isinstance(hotels_data, dict):

            raise ValueError("LLM did not return a JSON object.")



        if not isinstance(hotels_data.get("hotels"), list):

            raise ValueError("LLM JSON does not contain a hotels list.")



    except Exception as exc:



        print(

            f"HOTEL STRUCTURED EXTRACTION ERROR: "

            f"{type(exc).__name__}: {exc}",

            flush=True,

        )



        hotels_data = {

            "hotels": []

        }



    # ---------------------------------------------------------

    # 5. FINAL CLEAN JSON FOR FRONTEND

    # ---------------------------------------------------------



    final_hotel_results = json.dumps(

        hotels_data,

        ensure_ascii=False,

    )



    print("\n========== STRUCTURED HOTEL DATA ==========")

    print(final_hotel_results)

    print("===========================================\n")



    return {

        "hotel_results": final_hotel_results,

        "messages": [

            AIMessage(content="Hotel information processed.")

        ],

        "llm_calls": state.get("llm_calls", 0) + 1,

    }











# =========================



# Weather Agent 



# =========================



def weather_agent(state: TravelState):



    print("\nInside weather agent\n")



    city = extract_destination(



        state["user_query"]



    )







    try:



        weather_data = asyncio.run(



            weather_mcp_search(city)



        )







        forecast_data = asyncio.run(



            forecast_mcp_search(city)



        )







        weather_results = _clip_text(



            f"Current Weather:\n{_compact_tool_output(weather_data, 700)}\n\n"



            f"Forecast:\n{_compact_tool_output(forecast_data, 700)}",



            1600,



        )



        print(weather_results)







    except Exception as exc:



        print(



            f"WEATHER AGENT MCP ERROR: "



            f"{type(exc).__name__}: {exc}",



            flush=True,



        )







        weather_results = (



            f"Live weather information for {city} "



            "is temporarily unavailable. Give general "



            "seasonal guidance and advise the traveler "



            "to verify the forecast before departure."



        )







    return {



        "weather_results": weather_results,



        "messages": [



            AIMessage(



                content="Weather information processed."



            )



        ],



    }











# =========================



# Budget Agent 



# =========================



def _sanitize_unavailable_flights(text: str) -> str:
    """Force flight fields to reflect unavailable live data after LLM generation."""
    try:
        parsed = _json_from_llm(text)
        if not isinstance(parsed, dict):
            return text

        flights = parsed.get("flights")
        if isinstance(flights, dict):
            flights["airlines"] = []
            flights["duration"] = ""
            flights["price_range"] = "Check live fares"
            flights["summary"] = "Live flight schedule unavailable — check current flight availability before booking."

        budget = parsed.get("budget")
        if isinstance(budget, dict) and isinstance(budget.get("breakdown"), list):
            for item in budget["breakdown"]:
                if isinstance(item, dict) and str(item.get("category", "")).lower() == "flights":
                    item["amount"] = "Not available"
                    item["notes"] = "Live flight data unavailable; check current fares before booking."

        return json.dumps(parsed, ensure_ascii=False)
    except Exception:
        return text


def budget_agent(state: TravelState):

    print("\nInside Budget agent\n")

    flight_data = str(state.get("flight_results", ""))
    hotel_data = str(state.get("hotel_results", ""))

    flight_unavailable = (
        not flight_data.strip()
        or "live flight data unavailable" in flight_data.lower()
        or "no usable flight data" in flight_data.lower()
        or "flight information unavailable" in flight_data.lower()
        or "uvx was not found" in flight_data.lower()
        or "live flight schedule data is currently unavailable" in flight_data.lower()
    )

    if flight_unavailable:
        flight_instruction = """
LIVE FLIGHT DATA IS UNAVAILABLE.

Do NOT invent or present as live:
- flight numbers
- airline names
- flight timings
- exact flight fares
- exact flight duration

If a flight budget estimate is useful, label it explicitly as a
GENERAL ESTIMATE and NOT as a live fare.
"""
    else:
        flight_instruction = """
Use only the flight information actually present in the provided data.
Clearly distinguish live information from estimates.
Do not add missing flight details.
"""

    prompt = f"""Analyze the travel budget.

USER QUERY:
{_clip_text(state.get('user_query', ''), 600)}

FLIGHT DATA:
{_clip_text(flight_data, 1000)}

HOTEL DATA:
{_clip_text(hotel_data, 1000)}

FLIGHT DATA RULE:
{flight_instruction}

IMPORTANT:
- Never fabricate live travel data.
- Clearly label every estimate as an estimate.
- If hotel prices are missing, do not invent exact hotel prices.
- If flight data is unavailable, explicitly say so.
- Do not name specific airlines unless they are present in the flight data.

Provide:
1. Estimated cost breakdown
2. Risk areas
3. 2-3 money-saving tips
4. Overall feasibility
"""

    budget_text = _llm_text(
        "You are a careful travel budget analyst. Never fabricate unavailable live travel data.",
        prompt,
    )

    if flight_unavailable:
        budget_text = _sanitize_unavailable_flights(budget_text)

    return {
        "budget_results": budget_text,
        "messages": [AIMessage(content="Budget assessment generated.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }



# =========================
# Itinerary Agent
# =========================
def itinerary_agent(state: TravelState):

    print("\nInside Itinerary agent\n")

    flight_data = str(state.get("flight_results", ""))
    hotel_data = str(state.get("hotel_results", ""))
    budget_data = str(state.get("budget_results", ""))

    flight_unavailable = (
        not flight_data.strip()
        or "live flight data unavailable" in flight_data.lower()
        or "no usable flight data" in flight_data.lower()
        or "flight information unavailable" in flight_data.lower()
        or "uvx was not found" in flight_data.lower()
        or "live flight schedule data is currently unavailable" in flight_data.lower()
    )

    if flight_unavailable:
        flight_rules = """
CRITICAL FLIGHT RULE:

Live flight information is unavailable.

Therefore you MUST NOT invent:
- airline names
- flight numbers
- departure times
- arrival times
- flight fares
- exact flight duration

Use wording such as:
"Live flight schedule unavailable — check current flight availability before booking."
Do not create fake flight details merely to complete the JSON fields.
"""
    else:
        flight_rules = """
Use only flight details actually present in the flight data.
Do not invent or extrapolate flight numbers, airlines, timings, fares, or durations.
"""

    prompt = f"""{TRIP_PLAN_JSON_INSTRUCTIONS}

Draft a realistic travel itinerary.

USER QUERY:
{_clip_text(state.get('user_query', ''), 700)}

FLIGHT DATA:
{_clip_text(flight_data, 1200)}

HOTEL DATA:
{_clip_text(hotel_data, 1200)}

BUDGET DATA:
{_clip_text(budget_data, 1000)}

{flight_rules}

GENERAL RULES:
1. Never fabricate live travel information.
2. Base the plan only on the provided agent data and general itinerary ideas.
3. If information is unavailable, say that it must be checked before booking.
4. Do not create fake flight numbers or airline names.
5. Do not create fake exact flight fares.
6. Do not claim that anything is booked.
7. Hotel names, prices, ratings and amenities must come from the provided hotel data.
8. Budget figures must be labelled as estimates when applicable.
9. Keep the itinerary practical and concise.
10. Return valid JSON only.
11. Do not return markdown.
"""

    response_text = _llm_text(
        "You are a careful travel concierge. Never fabricate unavailable travel data. Return strict JSON only.",
        prompt,
    )

    if flight_unavailable:
        response_text = _sanitize_unavailable_flights(response_text)

    approval_request = (
        "Take a look at this draft trip. Approve it or tell us what to change."
    )

    return {
        "itinerary": response_text,
        "approval_request": approval_request,
        "messages": [AIMessage(content="Draft itinerary created for human review.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }



# =========================
# Human-in-the-Loop approval
# =========================
def human_approval_agent(state: TravelState):







    review = interrupt(



        {



            "question": "Do you approve this itinerary?",



            "draft_itinerary": state.get("itinerary", ""),



            "approval_request": state.get("approval_request", ""),



            "selected_agents": state.get("selected_agents", []),



            "supervisor_reasoning": state.get("supervisor_reasoning", ""),



            "expected_response": {



                "approved": True,



                "feedback": "Optional revision feedback",



            },



        }



    )







    approved = bool(review.get("approved", False))



    human_feedback = str(review.get("feedback", "")).strip()







    return {



        "approved": approved,



        "human_feedback": human_feedback,



        "messages": [AIMessage(content="Human approval step completed.")],



    }











# =========================



# Final Response Agent



# =========================



def final_agent(state: TravelState):



    if state.get("approved", False):



        review_instruction = (



            "User approved the draft. Polish it without major changes."



        )



    else:



        review_instruction = f"""User requested revision: {_clip_text(state.get('human_feedback', '') or 'Improve the draft.', 300)}"""







    final_prompt = f"""{TRIP_PLAN_JSON_INSTRUCTIONS}







Finalize the travel plan.







Review: {review_instruction}



Query: {_clip_text(str(state.get('user_query', '')), 600)}



Flights: {_clip_text(str(state.get('flight_results', '')), 700)}



Hotels: {_clip_text(str(state.get('hotel_results', '')), 700)}



Budget: {_clip_text(str(state.get('budget_results', '')), 600)}



Draft: {_clip_text(str(state.get('itinerary', '')), 1200)}







Return JSON only. Complete all sections that are supported by the data.

CRITICAL: Do not invent unavailable flight or hotel information. If live flight data is unavailable, keep airline names, flight numbers, timings and exact fares empty or state that live availability must be checked. Do not turn budget estimates into confirmed live prices."""







    response_text = _llm_text(



        "You are a travel concierge. Return complete JSON only.",



        final_prompt,



    )







    return {



        "final_response": response_text,



        "messages": [AIMessage(content=response_text)],



        "llm_calls": state.get("llm_calls", 0) + 1,



    }















# =========================



# Dynamic Supervisor Routing



# =========================



ROUTE_MAP = {



    "guardrail_blocked": "guardrail_blocked",



    "flight_agent": "flight_agent",



    "hotel_agent": "hotel_agent",



    "weather_agent": "weather_agent",



    "budget_agent": "budget_agent",



    "itinerary_agent": "itinerary_agent",



}











def _selected_agents(state: TravelState) -> list[str]:



    selected = state.get("selected_agents", [])



    return [agent for agent in AGENT_ORDER if agent in selected]











def route_from_supervisor(state: TravelState) -> str:



    if not state.get("guardrail_allowed", True):



        return "guardrail_blocked"







    selected = _selected_agents(state)



    return selected[0] if selected else "itinerary_agent"











def route_after_agent(current_agent: str):



    def route(state: TravelState) -> str:



        selected = _selected_agents(state)



        current_index = AGENT_ORDER.index(current_agent)







        for next_agent in AGENT_ORDER[current_index + 1 :]:



            if next_agent in selected:



                return next_agent







        return "itinerary_agent"







    return route











# =========================



# Build Graph



# =========================



graph = StateGraph(TravelState)







graph.add_node("supervisor", supervisor_agent)



graph.add_node("guardrail_blocked", guardrail_blocked_agent)



graph.add_node("flight_agent", flight_agent)



graph.add_node("hotel_agent", hotel_agent)



graph.add_node("weather_agent", weather_agent)



graph.add_node("budget_agent", budget_agent)



graph.add_node("itinerary_agent", itinerary_agent)



graph.add_node("human_approval", human_approval_agent)



graph.add_node("final_agent", final_agent)







graph.add_edge(START, "supervisor")



graph.add_conditional_edges("supervisor", route_from_supervisor, ROUTE_MAP)







graph.add_conditional_edges(



    "flight_agent", route_after_agent("flight_agent"), ROUTE_MAP



)



graph.add_conditional_edges(



    "hotel_agent", route_after_agent("hotel_agent"), ROUTE_MAP



)



graph.add_conditional_edges(



    "weather_agent", route_after_agent("weather_agent"), ROUTE_MAP



)



graph.add_conditional_edges(



    "budget_agent", route_after_agent("budget_agent"), ROUTE_MAP



)







graph.add_edge("itinerary_agent", "human_approval")



graph.add_edge("human_approval", "final_agent")



graph.add_edge("final_agent", END)



graph.add_edge("guardrail_blocked", END)











# =========================



# PostgreSQL Checkpointer



# =========================



# LangGraph stores durable graph checkpoints in PostgreSQL.



# Keep this connection open for the lifetime of the application.



postgres_conn = psycopg.connect(



    DATABASE_URL,



    autocommit=True,



    row_factory=dict_row,



)







checkpointer = PostgresSaver(postgres_conn)



checkpointer.setup()



travel_graph = graph.compile(checkpointer=checkpointer)







# =========================



# FastAPI-facing helpers



# =========================



def _interrupt_payload(result: dict[str, Any]) -> dict[str, Any] | None:



    interrupts = result.get("__interrupt__", [])



    if not interrupts:



        return None







    first_interrupt = interrupts[0]



    payload = getattr(first_interrupt, "value", first_interrupt)



    return payload if isinstance(payload, dict) else {"value": payload}











def _serialize_result(



    result: dict[str, Any],



    thread_id: str,



) -> dict[str, Any]:



    messages = result.get("messages", [])



    last_message = _message_text(messages[-1].content) if messages else ""



    answer = _message_text(result.get("final_response") or last_message)



    interrupt_payload = _interrupt_payload(result)



    itinerary_text = _message_text(result.get("itinerary", ""))







    if interrupt_payload:



        answer = _message_text(



            interrupt_payload.get("draft_itinerary") or itinerary_text



        )



        itinerary_text = _message_text(



            interrupt_payload.get("draft_itinerary", "") or itinerary_text



        )







    structured_plan = _extract_structured_plan(answer) or _extract_structured_plan(



        itinerary_text



    )







    # Validate plan completeness



    plan_is_complete = False



    missing_fields = []



    if structured_plan:



        plan_is_complete, missing_fields = _validate_trip_plan_completeness(structured_plan)



        if not plan_is_complete:



            print(f"Warning: Incomplete trip plan. Missing: {', '.join(missing_fields)}")







    friendly_answer = (



        _friendly_answer_from_plan(structured_plan) if structured_plan else ""



    )







    if structured_plan:



        display_answer = (



            friendly_answer



            or str(



                structured_plan.get("overview")



                or structured_plan.get("headline")



                or ""



            ).strip()



            or "Here is your custom travel plan."



        )



    else:



        trimmed_ans = (answer or itinerary_text or "").strip()



        if trimmed_ans.startswith("{") or "```json" in trimmed_ans:



            display_answer = (



                "I've drafted your travel plan. Please review the details below."



            )



        else:



            display_answer = answer or "I have processed your request."







    return {



        "thread_id": thread_id,



        "answer": display_answer,



        "plan": structured_plan,



        "structured_plan": structured_plan,



        "plan_is_complete": plan_is_complete,



        "missing_fields": missing_fields,



        "requires_approval": interrupt_payload is not None,



        "approval_request": (



            interrupt_payload.get("approval_request", "")



            if interrupt_payload



            else result.get("approval_request", "")



        ),



        "flight_results": result.get("flight_results", ""),



        "hotel_results": result.get("hotel_results", ""),



        "weather_results": result.get("weather_results", ""),



        "budget_results": result.get("budget_results", ""),



        "itinerary": itinerary_text,



        "selected_agents": result.get("selected_agents", []),



        "trip_constraints": result.get("trip_constraints", {}),



        "supervisor_reasoning": result.get("supervisor_reasoning", ""),



        "guardrail_allowed": result.get("guardrail_allowed", True),



        "guardrail_reason": result.get("guardrail_reason", ""),



        "approved": result.get("approved"),



        "human_feedback": result.get("human_feedback", ""),



        "llm_calls": result.get("llm_calls", 0),



    }











def run_travel_agent(user_input: str, thread_id: str | None = None):



    """Start a new travel-planning run and pause at human approval."""



    if not thread_id:



        thread_id = f"user_{uuid.uuid4().hex}"







    config = {"configurable": {"thread_id": thread_id}}







    result = travel_graph.invoke(



        {



            "messages": [HumanMessage(content=user_input)],



            "user_query": user_input,



            "guardrail_allowed": True,



            "guardrail_reason": "",



            "selected_agents": [],



            "trip_constraints": _empty_constraints(),



            "supervisor_reasoning": "",



            "flight_results": "",



            "hotel_results": "",



            "weather_results": "",



            "budget_results": "",



            "itinerary": "",



            "approval_request": "",



            "approved": False,



            "human_feedback": "",



            "final_response": "",



            "llm_calls": 0,



        },



        config=config,



    )







    return _serialize_result(result, thread_id)











def resume_travel_agent(



    thread_id: str,



    approved: bool,



    feedback: str = "",



):



    """Resume the paused LangGraph thread after human review."""



    if not thread_id:



        raise ValueError("thread_id is required to resume a travel plan.")







    config = {"configurable": {"thread_id": thread_id}}



    result = travel_graph.invoke(



        Command(



            resume={



                "approved": approved,



                "feedback": feedback.strip(),



            }



        ),



        config=config,



    )







    return _serialize_result(result, thread_id)
