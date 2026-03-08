import pandas as pd
from abc import ABC, abstractmethod
import datetime
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FinancialDataAdapter(ABC):
    """Abstract Base Class for Financial Data Adapters (Adapter Pattern)."""

    @abstractmethod
    def fetch_data(self, company_code: str) -> pd.DataFrame:
        """Fetch raw data from the specific data source."""
        pass

    @abstractmethod
    def transform_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        """Transform raw data into the standardized DataFrame format."""
        pass

    def get_standardized_10yr_financials(self, company_code: str) -> pd.DataFrame:
        """
        Template method that dictates the pipeline:
        1. Fetch raw data.
        2. Transform to standardized format.
        3. Filter for the last 10 years.
        """
        try:
            raw_data = self.fetch_data(company_code)
            standardized_df = self.transform_data(raw_data)
            return self._filter_last_10_years(standardized_df)
        except Exception as e:
            logger.error(f"Error processing {company_code}: {e}")
            raise

    def _filter_last_10_years(self, df: pd.DataFrame) -> pd.DataFrame:
        """Utility to filter exactly the last 10 years based on the 'year' column."""
        if 'year' not in df.columns:
            raise ValueError("Standardized DataFrame must contain a 'year' column.")

        current_year = datetime.datetime.now().year
        ten_years_ago = current_year - 10

        filtered_df = df[(df['year'] > ten_years_ago) & (df['year'] <= current_year)]
        return filtered_df.sort_values(by='year', ascending=True).reset_index(drop=True)


class IfindAdapter(FinancialDataAdapter):
    """Adapter for iFinD (同花顺) API."""

    def fetch_data(self, company_code: str) -> pd.DataFrame:
        logger.info(f"Fetching data from iFinD for {company_code}...")
        # Mocking raw data fetch from iFinD API
        # E.g. ThsAPI.req_history(...)
        current_year = datetime.datetime.now().year
        data = {
            'ReportYear': [current_year - i for i in range(12)],
            'TotalRevenue': [1000 + i*10 for i in range(12)],
            'NetProfit': [100 + i for i in range(12)],
            'AssetLiabilityRatio': [0.5 - i*0.01 for i in range(12)]
        }
        return pd.DataFrame(data)

    def transform_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        logger.info("Transforming iFinD data to standardized format...")
        # Map iFinD specific columns to standardized columns
        standardized = raw_data.rename(columns={
            'ReportYear': 'year',
            'TotalRevenue': 'revenue',
            'NetProfit': 'net_profit',
            'AssetLiabilityRatio': 'liability_ratio'
        })
        # Add standardized columns that might be missing
        standardized['data_source'] = 'iFinD'
        return standardized


class TongdaxinAdapter(FinancialDataAdapter):
    """Adapter for Tongdaxin (通达信) API."""

    def fetch_data(self, company_code: str) -> pd.DataFrame:
        logger.info(f"Fetching data from Tongdaxin for {company_code}...")
        # Mocking raw data fetch from Tongdaxin
        current_year = datetime.datetime.now().year
        data = {
            'FiscalYear': [current_year - i for i in range(15)],
            'OperatingIncome': [2000 + i*20 for i in range(15)],
            'NetIncome': [200 + i*2 for i in range(15)],
            'DebtToAsset': [0.6 - i*0.02 for i in range(15)]
        }
        return pd.DataFrame(data)

    def transform_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        logger.info("Transforming Tongdaxin data to standardized format...")
        # Map Tongdaxin specific columns to standardized columns
        standardized = raw_data.rename(columns={
            'FiscalYear': 'year',
            'OperatingIncome': 'revenue',
            'NetIncome': 'net_profit',
            'DebtToAsset': 'liability_ratio'
        })
        standardized['data_source'] = 'Tongdaxin'
        return standardized


class GenericFinancialAdapter(FinancialDataAdapter):
    """Adapter for Generic Public Financial APIs."""

    def fetch_data(self, company_code: str) -> pd.DataFrame:
        logger.info(f"Fetching data from Generic API for {company_code}...")
        # Mocking raw data fetch from a generic REST API
        current_year = datetime.datetime.now().year
        data = {
            'period': [f"{current_year - i}-12-31" for i in range(10)],
            'rev': [500 + i*5 for i in range(10)],
            'profit': [50 + i*0.5 for i in range(10)],
            'leverage': [0.4 - i*0.005 for i in range(10)]
        }
        return pd.DataFrame(data)

    def transform_data(self, raw_data: pd.DataFrame) -> pd.DataFrame:
        logger.info("Transforming Generic API data to standardized format...")

        # Extract year from date string
        raw_data['year'] = pd.to_datetime(raw_data['period']).dt.year

        standardized = raw_data.rename(columns={
            'rev': 'revenue',
            'profit': 'net_profit',
            'leverage': 'liability_ratio'
        })

        # Drop original period column as we now have 'year'
        standardized = standardized.drop(columns=['period'])
        standardized['data_source'] = 'GenericAPI'

        return standardized
