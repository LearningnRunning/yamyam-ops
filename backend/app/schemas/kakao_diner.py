from pydantic import BaseModel, Field


class KakaoDinerBase(BaseModel):
    diner_id: int = Field(..., description="카카오 음식점 고유 인덱스")
    name: str = Field(..., min_length=1, max_length=255, description="음식점 이름")
    tag: str | None = Field(None, description="음식점 태그")
    menu_name: str | None = Field(None, description="대표 메뉴명")
    menu_price: str | None = Field(None, description="메뉴 가격")
    review_cnt: int = Field(..., ge=0, description="리뷰 개수")
    review_avg: float = Field(..., ge=0, le=5, description="평균 평점")
    blog_review_cnt: float = Field(..., ge=0, description="블로그 리뷰 개수")
    review_tags: str | None = Field(None, description="리뷰 태그")
    road_address: str | None = Field(None, description="도로명 주소")
    num_address: str | None = Field(None, description="지번 주소")
    phone: str | None = Field(None, max_length=50, description="전화번호")
    lat: float = Field(..., ge=-90, le=90, description="위도")
    lon: float = Field(..., ge=-180, le=180, description="경도")
    grade: int | None = Field(None, description="음식점 등급")
    hidden_score: float | None = Field(None, description="숨찐맛 점수")
    bayesian_score: float | None = Field(None, description="베이지안 평균 점수")


class KakaoDinerCreate(KakaoDinerBase):
    pass


class KakaoDinerUpdate(BaseModel):
    name: str | None = Field(None, min_length=1, max_length=255)
    tag: str | None = None
    menu_name: str | None = None
    menu_price: str | None = None
    review_cnt: int | None = None
    review_avg: float | None = Field(None, ge=0, le=5)
    blog_review_cnt: float | None = Field(None, ge=0)
    review_tags: str | None = None
    road_address: str | None = None
    num_address: str | None = None
    phone: str | None = Field(None, max_length=50)
    lat: float | None = Field(None, ge=-90, le=90)
    lon: float | None = Field(None, ge=-180, le=180)
    grade: int | None = None
    hidden_score: float | None = None
    bayesian_score: float | None = None


class KakaoDiner(KakaoDinerBase):
    id: str  # ULID
    crawled_at: str
    updated_at: str

    class Config:
        from_attributes = True


class KakaoDinerSortRequest(BaseModel):
    """음식점 정렬/필터링 요청 스키마"""

    diner_ids: list[str] = Field(..., description="정렬할 음식점 ID 리스트 (ULID)")
    user_id: str | None = Field(None, description="사용자 ID (개인화 정렬용)")
    sort_by: str = Field(
        "rating",
        description="정렬 기준 (personalization, popularity, hidden_gem, rating, distance, review_count)",
    )
    min_rating: float | None = Field(None, ge=0, le=5, description="최소 평점")
    user_lat: float | None = Field(
        None, ge=-90, le=90, description="사용자 위도 (거리 정렬용)"
    )
    user_lon: float | None = Field(
        None, ge=-180, le=180, description="사용자 경도 (거리 정렬용)"
    )
    limit: int | None = Field(
        None, ge=1, le=1000, description="반환할 최대 레코드 수 (top-k)"
    )
    offset: int | None = Field(None, ge=0, description="페이지네이션 오프셋")


class FilteredDinerResponse(BaseModel):
    """필터링된 음식점 최소 정보 응답 (id와 distance만)"""

    id: str = Field(..., description="음식점 ULID")
    diner_id: int = Field(..., description="카카오 음식점 고유 인덱스")
    distance: float = Field(..., description="사용자 위치로부터의 거리 (km)")


class KakaoDinerResponse(BaseModel):
    id: str  # ULID
    diner_id: int
    name: str
    tag: str | None
    menu_name: str | None
    menu_price: str | None
    review_cnt: int
    review_avg: float
    blog_review_cnt: float | None
    review_tags: str | None
    road_address: str | None
    num_address: str | None
    phone: str | None
    lat: float
    lon: float
    category_large: str | None
    category_middle: str | None
    category_small: str | None
    category_detail: str | None
    grade: int | None
    hidden_score: float | None
    bayesian_score: float | None
    distance: float | None = Field(None, description="사용자 위치로부터의 거리 (km)")
    crawled_at: str
    updated_at: str


class SearchDinerResponse(BaseModel):
    """음식점 검색 결과 응답 스키마"""

    id: str = Field(..., description="음식점 ULID")
    diner_id: int = Field(..., description="카카오 음식점 고유 인덱스")
    name: str = Field(..., description="음식점 이름")
    match_type: str = Field(
        ..., description="매칭 타입 (정확한 매칭, 부분 매칭, 자모 매칭)"
    )
    jamo_score: float | None = Field(None, description="자모 매칭 점수 (0.0-1.0)")
    distance: float | None = Field(None, description="사용자 위치로부터의 거리 (km)")
    num_address: str | None = Field(None, description="지번 주소")
