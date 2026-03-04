from pydantic import BaseModel, Field


class KakaoReviewBase(BaseModel):
    diner_id: int = Field(..., description="음식점 인덱스")
    reviewer_id: int = Field(..., description="리뷰어 ID")
    review_id: int = Field(..., description="리뷰 고유 ID")
    text: str | None = Field(None, description="리뷰 내용")
    date: str | None = Field(None, description="리뷰 작성일")
    star: float = Field(..., ge=1, le=5, description="리뷰 평점")
    near: bool | None = Field(None, description="근처 방문 여부")
    is_place_owner_pick: bool | None = Field(None, description="사장님 픽 여부")
    like_count: int | None = Field(None, ge=0, description="좋아요 수")
    photo_count: int | None = Field(None, ge=0, description="사진 수")


class KakaoReviewCreate(KakaoReviewBase):
    pass


class KakaoReviewUpdate(BaseModel):
    text: str | None = None
    date: str | None = None
    star: float | None = Field(None, ge=1, le=5)
    near: bool | None = None
    is_place_owner_pick: bool | None = None
    like_count: int | None = Field(None, ge=0)
    photo_count: int | None = Field(None, ge=0)


class KakaoReview(KakaoReviewBase):
    id: str  # ULID
    crawled_at: str
    updated_at: str

    class Config:
        from_attributes = True


class KakaoReviewResponse(BaseModel):
    id: str  # ULID
    diner_id: int
    reviewer_id: int
    review_id: int
    text: str | None
    date: str | None
    star: float
    near: bool | None
    is_place_owner_pick: bool | None
    like_count: int | None
    photo_count: int | None
    crawled_at: str
    updated_at: str


class KakaoReviewWithDetails(KakaoReviewResponse):
    name: str | None
    tag: str | None
    user_name: str | None
