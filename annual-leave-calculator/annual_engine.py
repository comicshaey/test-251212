# ============================================================
# annual_engine.py
# Pyodide / Python3.11 기준 완전 호환 모듈
# - 나이스 근무상황 자동 집계
# - 연차 추천 계산(규정 세트별 로직)
# - 임금 계산(시급/일급/월급)
# - 미사용 연차수당 산정
# - 10원 단위 절사 규칙 포함
# ============================================================

from dataclasses import dataclass
from typing import List, Dict, Any, Optional


# ============================================================
# 0. 유틸
# ============================================================

def drop_to_10won(amount: float) -> int:
    """
    1원 단위 절삭 기능 → 10원 단위로 내림.
    예: 11111 → 11110 / 14567 → 14560
    """
    try:
        return (int(amount) // 10) * 10
    except Exception:
        return 0


# ============================================================
# 1. 나이스 근무상황 구조체
# ============================================================

@dataclass
class NiceRecord:
    leave_type: str        # 종별
    duration_raw: str      # "1일5시간" 또는 "0.5" 등
    hours_per_day: float   # 1일 소정근로시간(예: 8)

    def parse_duration(self) -> Dict[str, Any]:
        """
        duration_raw → 일 / 시간 / 분 형태로 파싱.
        가능한 입력 예:
            "1일 5시간"
            "2.5"
            "3시간 30분"
            "1일"
            "5시간"
            "30분"
        """
        txt = str(self.duration_raw).strip()
        if not txt:
            return {"days": 0, "hours": 0, "minutes": 0}

        # case1: "X일Y시간Z분"
        days = hours = minutes = 0

        # 일 단위
        if "일" in txt:
            try:
                val = txt.split("일")[0]
                days = float(val)
                txt = txt.split("일")[1]
            except Exception:
                pass

        # 시간 단위
        if "시간" in txt:
            try:
                val = txt.split("시간")[0]
                hours = float(val)
                txt = txt.split("시간")[1]
            except Exception:
                pass

        # 분 단위
        if "분" in txt:
            try:
                val = txt.split("분")[0]
                minutes = float(val)
            except Exception:
                pass

        # case2: 순수 숫자 (0.5일 or 2.25일 등)
        if days == 0 and hours == 0 and minutes == 0:
            try:
                # "2.5" → 2.5일
                val = float(self.duration_raw)
                days = val
            except Exception:
                pass

        return {"days": days, "hours": hours, "minutes": minutes}

    def to_total_hours(self) -> float:
        """
        총 시간을 10진법 시간으로 계산. (1일 = hours_per_day)
        """
        d = self.parse_duration()
        total = d["days"] * self.hours_per_day
        total += d["hours"]
        total += d["minutes"] / 60.0
        return total


# ============================================================
# 2. 나이스 근무상황 집계
# ============================================================

def summarize_nice_records(records: List[NiceRecord]) -> List[Dict[str, Any]]:
    """
    같은 leave_type(종별)끼리 건수 및 합계 계산.
    리턴 예:
    [
      {
        "leave_type": "병가",
        "count": 3,
        "sum_d_h_m": "2일 3시간",
        "sum_hours_decimal": 19.5,
        "converted_days_hours": "2일 3.5시간"
      },
      ...
    ]
    """
    if not records:
        return []

    grouped = {}
    for r in records:
        lt = r.leave_type
        grouped.setdefault(lt, []).append(r)

    output = []
    for lt, recs in grouped.items():
        total_hours = 0.0

        for r in recs:
            total_hours += r.to_total_hours()

        # 총시간 → 일·시간·분 변환
        hpd = recs[0].hours_per_day
        days = int(total_hours // hpd)
        remain = total_hours - days * hpd
        hours = int(remain)
        minutes = int(round((remain - hours) * 60))

        # 보기용 문자열
        dhm_str = f"{days}일 {hours}시간 {minutes}분"
        # 10진법 환산: remain은 순수시간
        converted = f"{days}일 {round(remain, 1)}시간"

        output.append({
          "leave_type": lt,
          "count": len(recs),
          "sum_d_h_m": dhm_str,
          "sum_hours_decimal": round(total_hours, 1),
          "converted_days_hours": converted
        })

    return output


# ============================================================
# 3. 연차 규정 세트 정의
# ============================================================

@dataclass
class RuleProfile:
    id: str
    name: str
    rounding_step: int = 10   # 10원단위 절사
    rounding_mode: str = "floor"  # 일단 버림
    base_days: Dict[str, Any] = None


# 규정 테이블(샘플 + 확장 가능)
RULE_PROFILES = {
    "law_basic": RuleProfile(
        id="law_basic",
        name="법정 기본형",
    ),
    "gw_school_cba": RuleProfile(
        id="gw_school_cba",
        name="학교근무자 CBA (예시)"
    ),
    "gw_institute_cba": RuleProfile(
        id="gw_institute_cba",
        name="기관근무자 CBA (예시)"
    ),
    "gw_wage_guideline": RuleProfile(
        id="gw_wage_guideline",
        name="통상임금 지침형 (예시)"
    ),
    "custom": RuleProfile(
        id="custom",
        name="커스텀"
    ),
}


# ============================================================
# 4. 연차 추천 로직
# ============================================================

def suggest_annual_days(rule_id: str, svc: Dict[str, Any]) -> Dict[str, Any]:
    """
    규정별 연차 “추천” 계산.
    svc = {
        service_years, full_years, attendance_rate, full_months ...
    }
    """
    fy = svc.get("full_years", 0)
    rate = svc.get("attendance_rate", 0)
    fm = svc.get("full_months", 0)

    # -------------------------
    # A) 법정 기본형
    # -------------------------
    if rule_id == "law_basic":
        if fy < 1:
            # 1년 미만 → 월개근 수 = 연차일수 (최대 11일)
            days = min(fm, 11)
            return {
                "suggested_days": days,
                "description": f"법정기본형: 1년 미만 → 월개근 {fm}개월 → {days}일"
            }
        else:
            # 1년 이상
            if rate < 80:
                # 출근율 <80 → 월 개근수 = 연차일수
                days = fm
                return {
                    "suggested_days": days,
                    "description": f"법정기본형: 출근율 {rate}% < 80 → 월개근 {fm} → {days}일"
                }
            else:
                # 출근율 ≥80: 15 + 가산
                extra = max(0, min(10, (fy - 1) // 2))
                days = 15 + extra
                return {
                    "suggested_days": days,
                    "description": f"법정기본형: 근속 {fy}년 → 기본 15 + 가산 {extra} = {days}일"
                }

    # -------------------------
    # B) 학교근무자 CBA (예시)
    # -------------------------
    if rule_id == "gw_school_cba":
        if fy < 1:
            days = min(fm, 11)
            return {
                "suggested_days": days,
                "description": f"학교 CBA: 1년 미만 → {fm}개월 → {days}일"
            }
        else:
            if rate >= 80:
                days = 26
                return {
                    "suggested_days": days,
                    "description": f"학교 CBA: 출근율 {rate}% ≥80 → {days}일"
                }
            else:
                days = fm
                return {
                    "suggested_days": days,
                    "description": f"학교 CBA: 출근율 {rate}% <80 → {days}일"
                }

    # -------------------------
    # C) 기관근무자 CBA (예시)
    # -------------------------
    if rule_id == "gw_institute_cba":
        if fy < 1:
            days = min(fm, 11)
            return {
                "suggested_days": days,
                "description": f"기관 CBA: 1년 미만 → {fm}개월 → {days}일"
            }
        else:
            if rate >= 80:
                days = 25
                return {
                    "suggested_days": days,
                    "description": f"기관 CBA: 출근율 {rate}% ≥80 → {days}일"
                }
            else:
                days = fm
                return {
                    "suggested_days": days,
                    "description": f"기관 CBA: 출근율 {rate}% <80 → {days}일"
                }

    # -------------------------
    # D) 통상임금 지침형 (예시)
    # -------------------------
    if rule_id == "gw_wage_guideline":
        if fy < 1:
            days = min(fm, 11)
            return {
                "suggested_days": days,
                "description": f"지침형: 1년 미만 → {fm} → {days}일"
            }
        else:
            days = 26
            return {
                "suggested_days": days,
                "description": f"지침형: 근속 {fy}년 → {days}일"
            }

    # -------------------------
    # E) 커스텀
    # -------------------------
    return {
        "suggested_days": None,
        "description": "커스텀 모드: 직접 입력"
    }


# ============================================================
# 5. 1일 통상임금 계산
# ============================================================

def calc_daily_wage(wage: Dict[str, Any]) -> float:
    """
    wage = {
      wage_type: hourly/daily/monthly
      wage_amount,
      hours_per_day,
      monthly_work_days
    }
    """
    wtype = wage.get("wage_type")
    amt = wage.get("wage_amount", 0)
    hpd = wage.get("hours_per_day", 8)
    mwd = wage.get("monthly_work_days", 20)

    if wtype == "hourly":
        return amt * hpd
    elif wtype == "daily":
        return amt
    elif wtype == "monthly":
        if mwd > 0:
            return amt / mwd
        return 0
    return 0


# ============================================================
# 6. 전체 파이프라인
# ============================================================

def full_pipeline(rule_id: str,
                  svc: Dict[str, Any],
                  wage: Dict[str, Any],
                  granted_days: float,
                  used_days: float) -> Dict[str, Any]:
    """
    HTML에서 호출하는 핵심 엔진.
    반환 구조:
    {
        rule: {...},
        suggestion: {...},
        payout: {...}
    }
    """

    # 1) 규정 세트 로딩
    profile = RULE_PROFILES.get(rule_id, RULE_PROFILES["custom"])

    # 2) 연차 추천
    suggestion = suggest_annual_days(rule_id, svc)

    # 3) 미사용 연차 산출
    unused = max(granted_days - used_days, 0)

    # 4) 1일 통상임금 계산
    daily_raw = calc_daily_wage(wage)

    # 5) 미사용수당 산정
    payout_raw = unused * daily_raw

    # 6) 10원단위 절사 적용
    daily_cut = drop_to_10won(daily_raw)
    payout_cut = drop_to_10won(payout_raw)

    return {
        "rule": {
            "id": profile.id,
            "name": profile.name
        },
        "suggestion": suggestion,
        "payout": {
            "granted_days": granted_days,
            "used_days": used_days,
            "unused_days": unused,
            "daily_wage_raw": daily_raw,
            "payout_raw": payout_raw,
            "daily_wage_rounded": daily_cut,
            "payout_rounded": payout_cut
        }
    }
