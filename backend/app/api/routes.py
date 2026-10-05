import asyncio

from fastapi import APIRouter
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.backend import (
    run_travel_agent,
    resume_travel_agent,
)


router = APIRouter(
    prefix="/api",
    tags=["Travel"],
)


# =========================================================
# Request Models
# =========================================================

class TravelRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ApprovalRequest(BaseModel):
    thread_id: str = Field(min_length=1)
    approved: bool
    feedback: str = ""


# =========================================================
# Start Travel Planning
# =========================================================

@router.post("/travel")
async def travel_planner(
    request_data: TravelRequest,
):
    try:
        user_message = request_data.message.strip()

        if not user_message:
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": "Message cannot be empty.",
                },
            )

        # Run the synchronous LangGraph function
        # in a separate thread so that asyncio.run()
        # inside the existing backend code does not
        # conflict with FastAPI's event loop.
        result = await asyncio.to_thread(
            run_travel_agent,
            user_input=user_message,
            thread_id=request_data.thread_id,
        )

        return JSONResponse(
            content={
                "success": True,
                **result,
            }
        )

    except Exception as exc:

        print("ERROR:", exc)

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(exc),
            },
        )


# =========================================================
# Human Approval / Resume
# =========================================================

@router.post("/travel/approve")
async def approve_travel_plan(
    request_data: ApprovalRequest,
):
    try:

        if (
            not request_data.approved
            and not request_data.feedback.strip()
        ):
            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "error": (
                        "Please provide revision feedback "
                        "when rejecting the draft."
                    ),
                },
            )

        # Resume the graph in a separate thread
        # for the same asyncio compatibility reason.
        result = await asyncio.to_thread(
            resume_travel_agent,
            thread_id=request_data.thread_id,
            approved=request_data.approved,
            feedback=request_data.feedback,
        )

        return JSONResponse(
            content={
                "success": True,
                **result,
            }
        )

    except Exception as exc:

        print("APPROVAL ERROR:", exc)

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "error": str(exc),
            },
        )