from pydantic import BaseModel


class InvestmentAnalysis(BaseModel):
    rating: str
    points: list[str]


class LivabilityAnalysis(BaseModel):
    rating: str
    points: list[str]


class AiScoreResult(BaseModel):
    score: int
    summary: str
    investment: InvestmentAnalysis
    livability: LivabilityAnalysis
    red_flags: list[str]
    green_flags: list[str]
