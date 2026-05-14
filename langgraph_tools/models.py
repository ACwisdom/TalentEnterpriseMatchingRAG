from __future__ import annotations

from datetime import datetime
from typing import Any, Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class PageInfo(BaseModel):
    model_config = {"populate_by_name": True}

    number: int
    size: int
    totalElements: int
    totalPages: int


class PagedResponse(BaseModel, Generic[T]):
    model_config = {"populate_by_name": True}

    items: list[T]
    page: PageInfo


class CandidateDto(BaseModel):
    model_config = {"populate_by_name": True}

    id: int
    name: str
    phone: str | None = None
    email: str | None = None
    skills: str | None = None
    expYears: int | None = None
    expectedSalaryMin: Any | None = None
    expectedSalaryMax: Any | None = None
    city: str | None = None
    status: str | None = None
    createdAt: datetime | None = None


class JobDto(BaseModel):
    model_config = {"populate_by_name": True}

    id: int
    companyId: int
    companyName: str
    title: str
    description: str | None = None
    salaryMin: Any | None = None
    salaryMax: Any | None = None
    city: str | None = None
    headcount: int | None = None
    urgency: str | None = None
    status: str
    createdAt: datetime | None = None
    updatedAt: datetime | None = None


class RecommendationDto(BaseModel):
    model_config = {"populate_by_name": True}

    id: int
    jobId: int
    candidateId: int
    matchScore: float | None = None
    scoreModel: str | None = None
    reason: str | None = None
    status: str
    createdAt: datetime | None = None
    updatedAt: datetime | None = None


class CommunicationDto(BaseModel):
    model_config = {"populate_by_name": True}

    id: int
    recommendationId: int
    channel: str
    direction: str
    body: str
    createdAt: datetime | None = None


class ReminderDto(BaseModel):
    model_config = {"populate_by_name": True}

    id: int
    recommendationId: int | None = None
    message: str
    dueAt: datetime
    channel: str | None = None
    status: str
    createdAt: datetime | None = None


class OutboundQueuedResponse(BaseModel):
    model_config = {"populate_by_name": True}

    deliveryId: str
    status: str


class CreateRecommendationRequest(BaseModel):
    jobId: int
    candidateId: int
    reason: str | None = None
    matchScore: float | None = None
    scoreModel: str | None = None


class PatchRecommendationStatusRequest(BaseModel):
    status: str
    note: str | None = None


class CreateCommunicationRequest(BaseModel):
    channel: str
    direction: str
    body: str


class OutboundMessageRequest(BaseModel):
    to: str | None = None
    body: str


class CreateReminderRequest(BaseModel):
    recommendationId: int | None = None
    dueAt: datetime
    message: str
