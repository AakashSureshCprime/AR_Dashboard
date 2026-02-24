import io
import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch,MagicMock
from models.ar_model import ARDataModel

@pytest.fixture
def raw_ar_dataframe():
    return pd.DataFrame({
        "Customer ID": ["C000437", "", "", "C000446"],
        "Customer Name": ["Cprime, Inc", "Cprime, Inc", "Cprime, Inc", "Croesus"],
        "Invoice": ["INV-78794", "INV-78800", "INV-78801", "INV-81229"],
        "GL posting date": ["5/14/2025", "5/14/2025", "5/14/2025", "1/31/2026"],
        "Invoice date": ["5/14/2025", "5/14/2025", "5/14/2025", "1/31/2026"],
        "Due date": ["6/13/2025", "6/13/2025", "6/13/2025", "3/2/2026"],
        "PMT Terms": ["30", "30", "30", "30"],
        "CUR": ["CAD", "CAD", "CAD", "CAD"],
        "AGE": ["250", "250", "250", "-12"],
        "181-365": ["84,346", "116,849", "75,715", "-"],
        "Total": ["84,346", "116,849", "75,715", "247,440"],
        "ROE": ["1.36", "1.36", "1.36", "1.36"],
        "181-365 .1": ["62,019", "85,918", "55,673", "-"],
        "Total in USD": ["62,019", "85,918", "55,673", "181,941"],
    })

@patch("models.ar_model.download_latest_file")
def test_load_logs_and_raises_runtime_error(mock_download):
    # Arrange
    mock_download.side_effect = Exception("Network error")

    model = ARDataModel()

    # Act + Assert
    with pytest.raises(RuntimeError) as exc_info:
        model.load()

    assert str(exc_info.value) == "AR data download failed"
    assert isinstance(exc_info.value.__cause__, Exception)

# -------------------------------------------------------------------
# Test Cleaning Logic
# -------------------------------------------------------------------

@patch("utils.sharepoint_fetch.download_latest_file")
@patch("models.ar_model.pd.read_excel")
@patch("models.ar_model.pd.read_csv")
def test_load_falls_back_to_excel(
    mock_read_csv,
    mock_read_excel,
    mock_download
):
    # Arrange
    mock_download.return_value = (b"dummy data", {"utc_time": "123", "name": "file.xlsx"})
    mock_read_csv.side_effect = Exception("CSV failed")
    fake_df = MagicMock()
    mock_read_excel.return_value = fake_df

    model = ARDataModel()
    model._clean = MagicMock(return_value=fake_df)

    # Act
    model.load()

    # Assert
    mock_read_csv.assert_called_once()
    mock_read_excel.assert_called_once()

def test_forward_fill_customer_id(raw_ar_dataframe):
    model = ARDataModel()
    cleaned = model._clean(raw_ar_dataframe)

    # Second and third rows should inherit first ID
    assert cleaned.loc[1, "Customer ID"] == "C000437"
    assert cleaned.loc[2, "Customer ID"] == "C000437"


def test_monetary_parsing(raw_ar_dataframe):
    model = ARDataModel()
    cleaned = model._clean(raw_ar_dataframe)

    # Comma removal + numeric conversion
    assert cleaned.loc[0, "181-365"] == 84346.0
    assert cleaned.loc[1, "181-365"] == 116849.0

    # Dash should convert to 0
    assert cleaned.loc[3, "181-365"] == 0.0


def test_total_column_numeric_conversion(raw_ar_dataframe):
    model = ARDataModel()
    cleaned = model._clean(raw_ar_dataframe)

    assert cleaned.loc[3, "Total"] == 247440.0
    assert np.issubdtype(type(cleaned.loc[3, "Total"]), np.number)

def test_usd_columns_parsed(raw_ar_dataframe):
    model = ARDataModel()
    cleaned = model._clean(raw_ar_dataframe)

    assert cleaned.loc[0, "Total in USD"] == 62019.0


def test_numeric_columns(raw_ar_dataframe):
    model = ARDataModel()
    cleaned = model._clean(raw_ar_dataframe)

    assert cleaned.loc[0, "ROE"] == 1.36
    assert cleaned.loc[3, "AGE"] == -12


def test_date_parsing(raw_ar_dataframe):
    model = ARDataModel()
    cleaned = model._clean(raw_ar_dataframe)

    assert pd.api.types.is_datetime64_any_dtype(cleaned["Invoice date"])
    assert cleaned.loc[0, "Due date"].month == 6


# -------------------------------------------------------------------
# Test parse_monetary standalone logic
# -------------------------------------------------------------------

def test_parse_monetary_parentheses():
    series = pd.Series(["(17,033)", "9,452", "-", ""])
    result = ARDataModel._parse_monetary(series)

    assert result.iloc[0] == -17033.0
    assert result.iloc[1] == 9452.0
    assert result.iloc[2] == 0.0
    assert result.iloc[3] == 0.0


# -------------------------------------------------------------------
# Test dataframe property auto-load behavior
# -------------------------------------------------------------------

def test_dataframe_property_triggers_load(monkeypatch, raw_ar_dataframe):
    model = ARDataModel()

    def mock_load():
        model._df = raw_ar_dataframe
        return model

    monkeypatch.setattr(model, "load", mock_load)

    df = model.dataframe
    assert isinstance(df, pd.DataFrame)


# -------------------------------------------------------------------
# Test load() with mocked SharePoint
# -------------------------------------------------------------------

@patch("utils.sharepoint_fetch.download_latest_file")
@patch("models.ar_model.pd.read_csv")
def test_load_method(mock_read_csv, mock_download, raw_ar_dataframe):
    # Convert fixture df to CSV bytes
    csv_bytes = raw_ar_dataframe.to_csv(index=False).encode()

    mock_download.return_value = (
        csv_bytes,
        {"utc_time": "2026-02-01T10:00:00Z", "name": "test.csv"},
    )
    mock_read_csv.return_value = raw_ar_dataframe

    model = ARDataModel()
    model.load()

    assert model.last_modified is not None
    assert isinstance(model.dataframe, pd.DataFrame)
    assert len(model.dataframe) == 4

def test_init_defaults():
    model = ARDataModel()
    assert model._file_path is None
    assert model._df is None
    assert model._last_modified is None

def test_read_csv_reads_all_as_str(tmp_path):
    # Create a CSV file
    csv = tmp_path / "test.csv"
    csv.write_text("A,B\n1,2\n3,4")
    model = ARDataModel(file_path=csv)
    # Patch pd.read_csv to check dtype argument
    with patch("models.ar_model.pd.read_csv") as mock_read_csv:
        model._read_csv()
        assert mock_read_csv.call_args[1]["dtype"] == str
        assert mock_read_csv.call_args[1]["keep_default_na"] is False

def test_clean_missing_columns():
    # DataFrame missing some expected columns
    df = pd.DataFrame({"Customer ID": ["C1", None], "Total": ["1,000", "-"]})
    model = ARDataModel()
    cleaned = model._clean(df)
    assert "Customer Name" not in cleaned.columns or cleaned["Customer ID"].isnull().sum() == 1

def test_clean_extra_whitespace_in_column_names():
    df = pd.DataFrame({
        " Customer ID ": ["C1", "C2"],
        " Total ": ["1,000", "2,000"]
    })
    df.columns = [" Customer ID ", " Total "]
    model = ARDataModel()
    cleaned = model._clean(df)
    assert "Customer ID" in cleaned.columns
    assert "Total" in cleaned.columns

def test_clean_all_blank_forward_fill_columns():
    df = pd.DataFrame({
        "Customer ID": [None, None, None],
        "Customer Name": [None, None, None],
        "Total": ["-", "-", "-"]
    })
    model = ARDataModel()
    cleaned = model._clean(df)
    assert cleaned["Customer ID"].isnull().all()
    assert cleaned["Customer Name"].isnull().all()

def test_clean_nonstandard_date_formats():
    df = pd.DataFrame({
        "Invoice date": ["2024/01/31", "31-01-2024", "bad-date"],
        "Customer ID": ["C1", "C2", "C3"],
        "Total": ["1,000", "2,000", "3,000"]
    })
    model = ARDataModel()
    cleaned = model._clean(df)
    # Should parse valid dates, coerce invalid to NaT
    assert pd.notnull(cleaned.loc[0, "Invoice date"])
    assert pd.notnull(cleaned.loc[1, "Invoice date"])
    assert pd.isnull(cleaned.loc[2, "Invoice date"])

def test_parse_monetary_already_numeric():
    s = pd.Series([1000, 2000.5, -3000])
    result = ARDataModel._parse_monetary(s)
    assert np.allclose(result, [1000, 2000.5, -3000])

def test_last_modified_property():
    model = ARDataModel()
    model._last_modified = "2024-01-01T00:00:00Z"
    assert model.last_modified == "2024-01-01T00:00:00Z"

def test_load_logs_info(monkeypatch):
    model = ARDataModel()
    # Patch download_latest_file to return dummy data
    dummy_content = b"A,B\n1,2"
    dummy_info = {"utc_time": "2024-01-01T00:00:00Z", "name": "file.csv"}
    monkeypatch.setattr("utils.sharepoint_fetch.download_latest_file", lambda: (dummy_content, dummy_info))
    # Patch pd.read_csv to return a DataFrame
    monkeypatch.setattr("models.ar_model.pd.read_csv", lambda *a, **k: pd.DataFrame({"A": [1], "B": [2]}))
    # Patch logger
    with patch("models.ar_model.logger") as mock_logger:
        model.load()
        assert mock_logger.info.called