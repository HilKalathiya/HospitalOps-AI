"""
HospitalOps AI — Data Ingestion Parser Tests.
"""

from datetime import UTC, datetime

from app.data_ingestion.pipelines.hero_dmc import parse_date as hero_parse_date
from app.data_ingestion.pipelines.hero_dmc import parse_int as hero_parse_int
from app.data_ingestion.pipelines.nhsn_hrd import parse_date as nhsn_parse_date
from app.data_ingestion.pipelines.nhsn_hrd import parse_int as nhsn_parse_int


def test_hero_parse_date():
    assert hero_parse_date("2017-04-20") == datetime(2017, 4, 20, tzinfo=UTC)
    assert hero_parse_date("") is None
    assert hero_parse_date("null") is None
    assert hero_parse_date("invalid") is None

def test_hero_parse_int():
    assert hero_parse_int("45") == 45
    assert hero_parse_int("45.0") == 45
    assert hero_parse_int("") is None
    assert hero_parse_int("na") is None

def test_nhsn_parse_date():
    assert nhsn_parse_date("12/31/2021") == datetime(2021, 12, 31, tzinfo=UTC)
    assert nhsn_parse_date("2021-12-31") == datetime(2021, 12, 31, tzinfo=UTC)
    assert nhsn_parse_date("2021-12-31T00:00:00") == datetime(2021, 12, 31, tzinfo=UTC)
    assert nhsn_parse_date("invalid") is None

def test_nhsn_parse_int():
    assert nhsn_parse_int("1,234") == 1234
    assert nhsn_parse_int("1234") == 1234
    assert nhsn_parse_int("") is None
