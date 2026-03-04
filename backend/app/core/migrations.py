"""
데이터베이스 마이그레이션 모듈
Alembic 대신 직접 SQL을 실행하는 방식으로 마이그레이션을 관리합니다.
"""

import logging

from app.core.db import db

logger = logging.getLogger(__name__)


def check_column_exists(table_name: str, column_name: str) -> bool:
    """컬럼이 존재하는지 확인"""
    try:
        with db.get_cursor() as (cursor, conn):
            query = """
                SELECT column_name
                FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
            """
            cursor.execute(query, (table_name, column_name))
            result = cursor.fetchone()
            return result is not None
    except Exception as e:
        logger.error(f"컬럼 존재 확인 중 오류 발생: {e}")
        return False


def add_column_if_not_exists(
    table_name: str,
    column_name: str,
    column_type: str,
    nullable: bool = True,
    default_value: str = None,
) -> bool:
    """컬럼이 없으면 추가"""
    try:
        # 컬럼이 이미 존재하는지 확인
        if check_column_exists(table_name, column_name):
            logger.info(f"컬럼 {table_name}.{column_name}은(는) 이미 존재합니다.")
            return False

        # 컬럼 추가 SQL 생성
        parts = [column_name, column_type]

        if default_value:
            parts.append(f"DEFAULT {default_value}")

        if not nullable:
            parts.append("NOT NULL")

        alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {' '.join(parts)}"

        with db.get_cursor() as (cursor, conn):
            cursor.execute(alter_sql)
            conn.commit()
            logger.info(f"컬럼 {table_name}.{column_name} 추가 완료")
            return True
    except Exception as e:
        logger.error(f"컬럼 추가 중 오류 발생: {e}")
        raise


def check_column_type(table_name: str, column_name: str) -> str | None:
    """컬럼의 데이터 타입 확인"""
    try:
        with db.get_cursor() as (cursor, conn):
            query = """
                SELECT data_type
                FROM information_schema.columns
                WHERE table_name = %s AND column_name = %s
            """
            cursor.execute(query, (table_name, column_name))
            result = cursor.fetchone()
            return result["data_type"] if result else None
    except Exception as e:
        logger.error(f"컬럼 타입 확인 중 오류 발생: {e}")
        return None


def migrate_diner_review_cnt_to_integer():
    """review_cnt(또는 diner_review_cnt) 컬럼 타입을 VARCHAR에서 INTEGER로 변경"""
    try:
        # 신규 컬럼명 우선 확인, 없으면 구 컬럼명 확인
        col_name = None
        if check_column_exists("kakao_diner", "review_cnt"):
            col_name = "review_cnt"
        elif check_column_exists("kakao_diner", "diner_review_cnt"):
            col_name = "diner_review_cnt"
        else:
            logger.info("review_cnt / diner_review_cnt 컬럼이 존재하지 않습니다.")
            return False

        # 현재 타입 확인
        current_type = check_column_type("kakao_diner", col_name)

        if current_type == "integer":
            logger.info(f"{col_name} 컬럼이 이미 INTEGER 타입입니다.")
            return False

        if current_type != "character varying":
            logger.warning(
                f"{col_name} 컬럼의 현재 타입이 {current_type}입니다. "
                "VARCHAR 타입이 아니므로 마이그레이션을 건너뜁니다."
            )
            return False

        # 컬럼 타입 변경
        logger.info(f"{col_name} 컬럼 타입을 INTEGER로 변경 중...")
        with db.get_cursor() as (cursor, conn):
            alter_sql = f"""
                ALTER TABLE kakao_diner
                ALTER COLUMN {col_name} TYPE INTEGER
                USING CASE
                    WHEN {col_name} IS NULL OR TRIM({col_name}) = '' THEN 0
                    WHEN {col_name} ~ '^[0-9]+\\.?[0-9]*$' THEN
                        CAST(CAST({col_name} AS NUMERIC) AS INTEGER)
                    ELSE 0
                END
            """
            cursor.execute(alter_sql)
            conn.commit()
            logger.info(f"{col_name} 컬럼이 INTEGER 타입으로 변경되었습니다.")
            return True
    except Exception as e:
        logger.error(f"review_cnt 컬럼 타입 변경 중 오류 발생: {e}")
        raise


def check_index_exists(table_name: str, index_name: str) -> bool:
    """인덱스가 존재하는지 확인"""
    try:
        with db.get_cursor() as (cursor, conn):
            query = """
                SELECT indexname
                FROM pg_indexes
                WHERE tablename = %s AND indexname = %s
            """
            cursor.execute(query, (table_name, index_name))
            result = cursor.fetchone()
            return result is not None
    except Exception as e:
        logger.error(f"인덱스 존재 확인 중 오류 발생: {e}")
        return False


def create_performance_indexes():
    """성능 최적화를 위한 인덱스 생성"""
    logger.info("성능 최적화 인덱스 생성 시작...")

    # 기본 정렬 인덱스 (High Priority)
    basic_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_kakao_diner_bayesian_score ON kakao_diner(bayesian_score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_kakao_diner_hidden_score ON kakao_diner(hidden_score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_kakao_diner_review_avg ON kakao_diner(review_avg DESC)",
    ]

    # PostGIS 확장 설치
    postgis_setup = [
        "CREATE EXTENSION IF NOT EXISTS postgis",
    ]

    # 공간 인덱스 (High Priority) - PostGIS GIST 인덱스
    spatial_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_kakao_diner_location ON kakao_diner USING GIST (ST_MakePoint(lon, lat))",
    ]

    # PostGIS가 없을 경우 대체 인덱스
    fallback_spatial_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_kakao_diner_lat_lon ON kakao_diner(lat, lon)",
    ]

    # 복합 인덱스 (Medium Priority)
    composite_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_kakao_diner_cat_large_bayesian ON kakao_diner(category_large, bayesian_score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_kakao_diner_cat_middle_bayesian ON kakao_diner(category_middle, bayesian_score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_kakao_diner_cat_large_hidden ON kakao_diner(category_large, hidden_score DESC)",
        "CREATE INDEX IF NOT EXISTS idx_kakao_diner_cat_large_rating ON kakao_diner(category_large, review_avg DESC)",
    ]

    # pg_trgm 확장 및 GIN 인덱스 (LIKE 검색 최적화)
    trgm_setup = [
        "CREATE EXTENSION IF NOT EXISTS pg_trgm",
    ]

    trgm_indexes = [
        "CREATE INDEX IF NOT EXISTS idx_kakao_diner_cat_large_trgm ON kakao_diner USING GIN (category_large gin_trgm_ops)",
        "CREATE INDEX IF NOT EXISTS idx_kakao_diner_cat_middle_trgm ON kakao_diner USING GIN (category_middle gin_trgm_ops)",
    ]

    # 각 인덱스를 독립적인 트랜잭션으로 생성
    def create_index_safe(index_sql: str, description: str):
        """안전하게 인덱스 생성 (독립 트랜잭션)"""
        try:
            with db.get_cursor() as (cursor, conn):
                cursor.execute(index_sql)
                conn.commit()
                logger.info(f"{description} 생성 완료: {index_sql[:80]}...")
                return True
        except Exception as e:
            logger.warning(f"{description} 생성 실패 (무시): {str(e)[:100]}")
            return False

    # 기본 인덱스 생성
    logger.info("기본 정렬 인덱스 생성 중...")
    for index_sql in basic_indexes:
        create_index_safe(index_sql, "기본 인덱스")

    # PostGIS 확장 설치
    logger.info("PostGIS 확장 설치 중...")
    postgis_available = False
    for setup_sql in postgis_setup:
        if create_index_safe(setup_sql, "PostGIS 확장"):
            postgis_available = True

    # 공간 인덱스 생성
    logger.info("공간 인덱스 생성 중...")
    if postgis_available:
        # PostGIS GIST 인덱스 사용
        for index_sql in spatial_indexes:
            if not create_index_safe(index_sql, "PostGIS GIST 인덱스"):
                # GIST 인덱스 실패 시 일반 인덱스로 대체
                logger.warning(
                    "PostGIS GIST 인덱스 생성 실패, 일반 인덱스로 대체합니다."
                )
                for fallback_sql in fallback_spatial_indexes:
                    create_index_safe(fallback_sql, "공간 인덱스 (대체)")
    else:
        # PostGIS 없으면 일반 인덱스 사용
        logger.warning("PostGIS를 사용할 수 없어 일반 B-tree 인덱스를 사용합니다.")
        for fallback_sql in fallback_spatial_indexes:
            create_index_safe(fallback_sql, "공간 인덱스 (대체)")

    # 복합 인덱스 생성
    logger.info("복합 인덱스 생성 중...")
    for index_sql in composite_indexes:
        create_index_safe(index_sql, "복합 인덱스")

    # pg_trgm 확장 설치
    logger.info("pg_trgm 확장 설치 중...")
    trgm_available = False
    for setup_sql in trgm_setup:
        if create_index_safe(setup_sql, "pg_trgm 확장"):
            trgm_available = True

    # pg_trgm 인덱스 생성 (확장이 설치된 경우만)
    if trgm_available:
        logger.info("LIKE 검색 최적화 인덱스 생성 중...")
        for index_sql in trgm_indexes:
            create_index_safe(index_sql, "pg_trgm 인덱스")
    else:
        logger.warning("pg_trgm 확장을 사용할 수 없어 GIN 인덱스를 건너뜁니다.")

    # 통계 업데이트
    logger.info("테이블 통계 업데이트 중...")
    try:
        with db.get_cursor() as (cursor, conn):
            cursor.execute("ANALYZE kakao_diner")
            conn.commit()
            logger.info("테이블 통계 업데이트 완료")
    except Exception as e:
        logger.warning(f"통계 업데이트 실패 (무시): {e}")

    logger.info("성능 최적화 인덱스 생성 완료")


def create_kakao_diner_open_hours_table():
    """kakao_diner_open_hours 테이블 생성 및 인덱스 추가"""
    logger.info("kakao_diner_open_hours 테이블 생성 시작...")

    try:
        with db.get_cursor() as (cursor, conn):
            # 테이블 존재 여부 확인
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'kakao_diner_open_hours'
                ) AS exists;
            """)
            result = cursor.fetchone()
            table_exists = result.get("exists", False) if result else False

            if table_exists:
                logger.info("kakao_diner_open_hours 테이블이 이미 존재합니다.")

                # UNIQUE 제약조건 또는 인덱스 확인
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_constraint
                        WHERE conrelid = 'kakao_diner_open_hours'::regclass
                        AND contype = 'u'
                    ) OR EXISTS (
                        SELECT 1 FROM pg_indexes
                        WHERE tablename = 'kakao_diner_open_hours'
                        AND indexdef LIKE '%UNIQUE%'
                        AND (indexdef LIKE '%diner_id%' OR indexdef LIKE '%diner_idx%')
                        AND indexdef LIKE '%day_of_week%'
                    ) AS exists;
                """)
                result = cursor.fetchone()
                unique_exists = result.get("exists", False) if result else False

                if not unique_exists:
                    # UNIQUE 제약조건 추가 시도
                    try:
                        cursor.execute("""
                            ALTER TABLE kakao_diner_open_hours
                            ADD CONSTRAINT kakao_diner_open_hours_diner_idx_day_of_week_unique
                            UNIQUE (diner_idx, day_of_week);
                        """)
                        conn.commit()
                        logger.info("UNIQUE 제약조건 추가 완료")
                    except Exception as e:
                        # 제약조건 추가 실패 시 UNIQUE 인덱스 생성 시도
                        logger.warning(
                            f"UNIQUE 제약조건 추가 실패, UNIQUE 인덱스 생성 시도: {e}"
                        )
                        try:
                            cursor.execute("""
                                CREATE UNIQUE INDEX IF NOT EXISTS
                                idx_kakao_diner_open_hours_unique
                                ON kakao_diner_open_hours(diner_idx, day_of_week);
                            """)
                            conn.commit()
                            logger.info("UNIQUE 인덱스 생성 완료")
                        except Exception as e2:
                            logger.error(f"UNIQUE 인덱스 생성도 실패: {e2}")
                else:
                    logger.info("UNIQUE 제약조건 또는 인덱스가 이미 존재합니다.")
            else:
                # 테이블 생성
                cursor.execute("""
                    CREATE TABLE kakao_diner_open_hours (
                        id VARCHAR(26) PRIMARY KEY,
                        diner_id INTEGER NOT NULL,
                        day_of_week INTEGER NOT NULL,
                        is_open BOOLEAN NOT NULL DEFAULT TRUE,
                        start_time TIME,
                        end_time TIME,
                        description TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

                        FOREIGN KEY (diner_id) REFERENCES kakao_diner(diner_id) ON DELETE CASCADE,
                        CONSTRAINT kakao_diner_open_hours_diner_id_day_of_week_unique
                        UNIQUE(diner_id, day_of_week)
                    );
                """)
                conn.commit()
                logger.info("kakao_diner_open_hours 테이블 생성 완료")

            # 인덱스 생성
            indexes = [
                ("idx_open_hours_diner_idx", "diner_idx"),
                ("idx_open_hours_day_of_week", "day_of_week"),
                ("idx_open_hours_is_open", "is_open"),
            ]

            for index_name, column_name in indexes:
                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_indexes
                        WHERE tablename = 'kakao_diner_open_hours'
                        AND indexname = '{index_name}'
                    ) AS exists;
                """)
                result = cursor.fetchone()
                index_exists = result.get("exists", False) if result else False

                if not index_exists:
                    cursor.execute(f"""
                        CREATE INDEX {index_name}
                        ON kakao_diner_open_hours({column_name});
                    """)
                    conn.commit()
                    logger.info(f"인덱스 {index_name} 생성 완료")
                else:
                    logger.info(f"인덱스 {index_name}은(는) 이미 존재합니다.")

            logger.info("kakao_diner_open_hours 테이블 및 인덱스 생성 완료")

    except Exception as e:
        logger.error(f"kakao_diner_open_hours 테이블 생성 중 오류 발생: {e}")
        raise


def create_kakao_diner_menus_table():
    """kakao_diner_menus 테이블 생성 및 인덱스 추가"""
    logger.info("kakao_diner_menus 테이블 생성 시작...")

    try:
        with db.get_cursor() as (cursor, conn):
            # 테이블 존재 여부 확인
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'kakao_diner_menus'
                ) AS exists;
            """)
            result = cursor.fetchone()
            table_exists = result.get("exists", False) if result else False

            if table_exists:
                logger.info("kakao_diner_menus 테이블이 이미 존재합니다.")
            else:
                # 테이블 생성
                cursor.execute("""
                    CREATE TABLE kakao_diner_menus (
                        id VARCHAR(26) PRIMARY KEY,
                        diner_id INTEGER NOT NULL,
                        name VARCHAR(255) NOT NULL,
                        product_id VARCHAR(255) NOT NULL,
                        price DOUBLE PRECISION,
                        is_ai_mate BOOLEAN,
                        photo_url TEXT,
                        is_recommend BOOLEAN,
                        "desc" TEXT,
                        mod_at TIMESTAMP WITH TIME ZONE,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

                        FOREIGN KEY (diner_id) REFERENCES kakao_diner(diner_id) ON DELETE CASCADE
                    );
                """)
                conn.commit()
                logger.info("kakao_diner_menus 테이블 생성 완료")

            # 인덱스 생성
            indexes = [
                ("idx_menus_diner_idx", "diner_idx"),
                ("idx_menus_product_id", "product_id"),
                ("idx_menus_is_recommend", "is_recommend"),
                ("idx_menus_is_ai_mate", "is_ai_mate"),
            ]

            for index_name, column_name in indexes:
                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_indexes
                        WHERE tablename = 'kakao_diner_menus'
                        AND indexname = '{index_name}'
                    ) AS exists;
                """)
                result = cursor.fetchone()
                index_exists = result.get("exists", False) if result else False

                if not index_exists:
                    cursor.execute(f"""
                        CREATE INDEX {index_name}
                        ON kakao_diner_menus({column_name});
                    """)
                    conn.commit()
                    logger.info(f"인덱스 {index_name} 생성 완료")
                else:
                    logger.info(f"인덱스 {index_name}은(는) 이미 존재합니다.")

            logger.info("kakao_diner_menus 테이블 및 인덱스 생성 완료")

    except Exception as e:
        logger.error(f"kakao_diner_menus 테이블 생성 중 오류 발생: {e}")
        raise


def create_kakao_diner_ai_data_table():
    """kakao_diner_ai_data 테이블 생성"""
    try:
        with db.get_cursor() as (cursor, conn):
            # 테이블 존재 여부 확인
            cursor.execute("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables
                    WHERE table_name = 'kakao_diner_ai_data'
                ) AS exists;
            """)
            result = cursor.fetchone()
            table_exists = result.get("exists", False) if result else False

            if not table_exists:
                # 테이블 생성
                cursor.execute("""
                    CREATE TABLE kakao_diner_ai_data (
                        id VARCHAR(26) PRIMARY KEY,
                        diner_id INTEGER NOT NULL UNIQUE,
                        ai_bottom_sheet_title VARCHAR(500),
                        ai_bottom_sheet_summary TEXT,
                        ai_bottom_sheet_sheets JSONB,
                        ai_bottom_sheet_landing_url TEXT,
                        blog_summaries JSONB,
                        all_keywords TEXT,
                        created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                        updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

                        FOREIGN KEY (diner_id) REFERENCES kakao_diner(diner_id) ON DELETE CASCADE
                    );
                """)
                conn.commit()
                logger.info("kakao_diner_ai_data 테이블 생성 완료")
            else:
                # 테이블이 이미 존재하는 경우, 누락된 컬럼 추가
                logger.info(
                    "kakao_diner_ai_data 테이블이 이미 존재합니다. 누락된 컬럼 확인 중..."
                )

                # 필수 컬럼 목록
                required_columns = {
                    "created_at": "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP",
                    "updated_at": "TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP",
                    "all_keywords": "TEXT",
                }

                for column_name, column_type in required_columns.items():
                    if not check_column_exists("kakao_diner_ai_data", column_name):
                        logger.info(f"컬럼 {column_name} 추가 중...")
                        add_column_if_not_exists(
                            table_name="kakao_diner_ai_data",
                            column_name=column_name,
                            column_type=column_type,
                            nullable=True,
                        )
                    else:
                        logger.info(f"컬럼 {column_name}은(는) 이미 존재합니다.")

            # 인덱스 생성
            indexes = [
                # diner_idx UNIQUE 인덱스 (이미 UNIQUE 제약조건으로 생성됨)
                ("idx_ai_data_diner_idx", "diner_idx", None),
                # JSONB GIN 인덱스 (jsonb_path_ops)
                (
                    "idx_ai_data_sheets_gin",
                    "ai_bottom_sheet_sheets",
                    "GIN (ai_bottom_sheet_sheets jsonb_path_ops)",
                ),
                (
                    "idx_ai_data_blog_summaries_gin",
                    "blog_summaries",
                    "GIN (blog_summaries jsonb_path_ops)",
                ),
                # all_keywords GIN 인덱스 (tsvector)
                (
                    "idx_ai_data_keywords_gin",
                    "all_keywords",
                    "GIN (to_tsvector('simple', COALESCE(all_keywords, '')))",
                ),
            ]

            for index_info in indexes:
                if len(index_info) == 3:
                    index_name, column_name, custom_index = index_info
                else:
                    index_name, column_name = index_info
                    custom_index = None

                cursor.execute(f"""
                    SELECT EXISTS (
                        SELECT 1 FROM pg_indexes
                        WHERE tablename = 'kakao_diner_ai_data'
                        AND indexname = '{index_name}'
                    ) AS exists;
                """)
                result = cursor.fetchone()
                index_exists = result.get("exists", False) if result else False

                if not index_exists:
                    if custom_index:
                        # 커스텀 인덱스 (GIN 등)
                        cursor.execute(f"""
                            CREATE INDEX {index_name}
                            ON kakao_diner_ai_data USING {custom_index};
                        """)
                    else:
                        # 일반 인덱스
                        cursor.execute(f"""
                            CREATE INDEX {index_name}
                            ON kakao_diner_ai_data({column_name});
                        """)
                    conn.commit()
                    logger.info(f"인덱스 {index_name} 생성 완료")
                else:
                    logger.info(f"인덱스 {index_name}은(는) 이미 존재합니다.")

            logger.info("kakao_diner_ai_data 테이블 및 인덱스 생성 완료")

    except Exception as e:
        logger.error(f"kakao_diner_ai_data 테이블 생성 중 오류 발생: {e}")
        raise


def rename_column_if_exists(table_name: str, old_name: str, new_name: str) -> bool:
    """컬럼이 존재하면 이름 변경 (이미 변경된 경우 스킵)"""
    try:
        if not check_column_exists(table_name, old_name):
            if check_column_exists(table_name, new_name):
                logger.info(f"{table_name}.{old_name} → {new_name}: 이미 변경됨")
            else:
                logger.warning(f"{table_name}.{old_name}: 컬럼이 존재하지 않음")
            return False

        with db.get_cursor() as (cursor, conn):
            cursor.execute(
                f"ALTER TABLE {table_name} RENAME COLUMN {old_name} TO {new_name}"
            )
            conn.commit()
            logger.info(f"{table_name}.{old_name} → {new_name} 변경 완료")
            return True
    except Exception as e:
        logger.error(
            f"컬럼 이름 변경 중 오류: {table_name}.{old_name} → {new_name}: {e}"
        )
        raise


def migrate_rename_kakao_diner_columns():
    """kakao_diner 테이블 컬럼 이름 변경 (diner_ 접두사 제거, diner_idx → diner_id)"""
    logger.info("kakao_diner 컬럼 이름 변경 시작...")

    # 자식 테이블의 diner_idx 먼저 rename (FK 정합성)
    for child_table in (
        "kakao_review",
        "kakao_diner_open_hours",
        "kakao_diner_menus",
        "kakao_diner_ai_data",
    ):
        rename_column_if_exists(child_table, "diner_idx", "diner_id")

    renames = [
        ("diner_idx", "diner_id"),
        ("diner_name", "name"),
        ("diner_tag", "tag"),
        ("diner_menu_name", "menu_name"),
        ("diner_menu_price", "menu_price"),
        ("diner_review_cnt", "review_cnt"),
        ("diner_review_avg", "review_avg"),
        ("diner_blog_review_cnt", "blog_review_cnt"),
        ("diner_review_tags", "review_tags"),
        ("diner_road_address", "road_address"),
        ("diner_num_address", "num_address"),
        ("diner_phone", "phone"),
        ("diner_lat", "lat"),
        ("diner_lon", "lon"),
        ("diner_open_time", "open_time"),
        ("diner_category_large", "category_large"),
        ("diner_category_middle", "category_middle"),
        ("diner_category_small", "category_small"),
        ("diner_category_detail", "category_detail"),
        ("diner_grade", "grade"),
    ]

    for old_name, new_name in renames:
        rename_column_if_exists("kakao_diner", old_name, new_name)

    logger.info("kakao_diner 컬럼 이름 변경 완료")


def migrate_rename_kakao_reviewer_columns():
    """kakao_reviewer 테이블 컬럼 이름 변경 (reviewer_ 접두사 제거)"""
    logger.info("kakao_reviewer 컬럼 이름 변경 시작...")

    renames = [
        ("reviewer_user_name", "user_name"),
        ("reviewer_review_cnt", "review_cnt"),
        ("reviewer_avg", "avg"),
    ]

    for old_name, new_name in renames:
        rename_column_if_exists("kakao_reviewer", old_name, new_name)

    logger.info("kakao_reviewer 컬럼 이름 변경 완료")


def migrate_rename_kakao_review_columns():
    """kakao_review 테이블 컬럼 이름 변경 + 신규 컬럼 추가"""
    logger.info("kakao_review 컬럼 이름 변경 및 추가 시작...")

    renames = [
        ("reviewer_review", "text"),
        ("reviewer_review_date", "date"),
        ("reviewer_review_score", "star"),
    ]

    for old_name, new_name in renames:
        rename_column_if_exists("kakao_review", old_name, new_name)

    new_columns = [
        ("near", "BOOLEAN", True, None),
        ("is_place_owner_pick", "BOOLEAN", True, None),
        ("like_count", "INTEGER", True, None),
        ("photo_count", "INTEGER", True, None),
    ]

    for col_name, col_type, nullable, default in new_columns:
        add_column_if_not_exists("kakao_review", col_name, col_type, nullable, default)

    logger.info("kakao_review 컬럼 이름 변경 및 추가 완료")


def run_migrations():
    """모든 마이그레이션 실행"""
    logger.info("데이터베이스 마이그레이션 시작...")

    try:
        # kakao_diner 테이블에 컬럼 추가
        migrations = [
            {
                "table": "kakao_diner",
                "column": "diner_grade",
                "type": "INTEGER",
                "nullable": False,
                "default": "0",
            },
            {
                "table": "kakao_diner",
                "column": "hidden_score",
                "type": "DOUBLE PRECISION",
                "nullable": False,
                "default": "0.0",
            },
            {
                "table": "kakao_diner",
                "column": "bayesian_score",
                "type": "DOUBLE PRECISION",
                "nullable": False,
                "default": "0.0",
            },
        ]

        for migration in migrations:
            add_column_if_not_exists(
                table_name=migration["table"],
                column_name=migration["column"],
                column_type=migration["type"],
                nullable=migration["nullable"],
                default_value=migration["default"],
            )

        # diner_review_cnt 컬럼 타입 변경 (VARCHAR -> INTEGER)
        migrate_diner_review_cnt_to_integer()

        # 성능 최적화 인덱스 생성
        create_performance_indexes()

        # kakao_diner_open_hours 테이블 생성
        create_kakao_diner_open_hours_table()

        # kakao_diner_menus 테이블 생성
        create_kakao_diner_menus_table()

        # kakao_diner_ai_data 테이블 생성
        create_kakao_diner_ai_data_table()

        # 컬럼 이름 변경 (diner_ 접두사 제거, diner_idx → diner_id 등)
        migrate_rename_kakao_diner_columns()
        migrate_rename_kakao_reviewer_columns()
        migrate_rename_kakao_review_columns()

        logger.info("데이터베이스 마이그레이션 완료")
    except Exception as e:
        logger.error(f"마이그레이션 실행 중 오류 발생: {e}")
        raise
