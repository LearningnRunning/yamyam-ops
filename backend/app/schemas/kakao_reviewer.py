from pydantic import BaseModel, Field


class KakaoReviewerBase(BaseModel):
    reviewer_id: int = Field(..., description="카카오 리뷰어 고유 ID")
    user_name: str | None = Field(None, max_length=100, description="리뷰어 사용자명")
    review_cnt: int = Field(..., ge=0, description="리뷰 개수")
    avg: float = Field(..., ge=0, le=5, description="평균 평점")
    badge_grade: str = Field(..., description="배지 등급")
    badge_level: int = Field(..., ge=0, description="배지 레벨")


class KakaoReviewerCreate(KakaoReviewerBase):
    pass


class KakaoReviewerUpdate(BaseModel):
    user_name: str | None = Field(None, max_length=100)
    review_cnt: int | None = Field(None, ge=0)
    avg: float | None = Field(None, ge=0, le=5)
    badge_grade: str | None = None
    badge_level: int | None = Field(None, ge=0)


class KakaoReviewer(KakaoReviewerBase):
    id: str  # ULID
    crawled_at: str
    updated_at: str

    class Config:
        from_attributes = True


class KakaoReviewerResponse(BaseModel):
    id: str  # ULID
    reviewer_id: int
    user_name: str | None
    review_cnt: int
    avg: float
    badge_grade: str
    badge_level: int
    crawled_at: str
    updated_at: str
