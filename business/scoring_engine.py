import pandas as pd
import numpy as np
import logging
import random
from typing import List, Dict
from nlp.deepseek_client import DeepSeek_LLM_Client
from database.batch_writer import BatchWriter
from datetime import datetime
import time

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class JobStatusTracker:
    """Simple in-memory tracker for background job progress."""
    def __init__(self):
        self.status = "Idle"
        self.total_companies = 0
        self.stage2_total = 0
        self.processed = 0
        self.stage = "Not Started"

    def reset(self, total: int):
        self.status = "Running"
        self.total_companies = total
        self.stage2_total = 0
        self.processed = 0
        self.stage = "Initializing"

    def update(self, processed: int, stage: str = None, stage2_total: int = None):
        self.processed = processed
        if stage:
            self.stage = stage
        if stage2_total is not None:
            self.stage2_total = stage2_total

    def finish(self):
        self.status = "Completed"
        self.stage = "Finished"

# Global instance to track progress
job_tracker = JobStatusTracker()

class TwoStageFunnel:
    """
    Two-Stage Funnel Scoring Engine for Full Market Analysis.
    Stage 1: Quantitative Hard Filter (Top 20% threshold).
    Stage 2: Qualitative Soft Analysis (DeepSeek LLM).
    """
    def __init__(self, api_key: str = None):
        self.nlp_client = DeepSeek_LLM_Client(api_key=api_key)
        # Initialize batch writer with threshold of 500
        self.writer = BatchWriter(batch_size=500)

    def _mock_market_data(self, n: int = 5000) -> pd.DataFrame:
        """Mock full market A-share data."""
        logger.info(f"Loading mocked wide table for {n} companies...")
        data = {
            'company_code': [f"{str(i).zfill(6)}.SZ" for i in range(1, n + 1)],
            # Simplified mock calculation factors
            'physical_capacity_saturation': np.random.uniform(0, 1, n),
            'financial_expansion_support': np.random.uniform(0, 1, n),
            'local_expansion_limitation': np.random.uniform(0, 1, n)
        }
        return pd.DataFrame(data)

    def stage_one_hard_filter(self, df: pd.DataFrame, top_percentile: float = 0.20) -> pd.DataFrame:
        """
        Stage 1: Calculate combined score from quantitative factors and filter top X%.
        """
        logger.info(f"Executing Stage 1: Quantitative Hard Filter on {len(df)} companies.")
        job_tracker.update(0, f"Stage 1: Quantitative Hard Filter")

        # Calculate a combined quantitative score (simple average for illustration)
        df['quant_score'] = (df['physical_capacity_saturation'] + df['financial_expansion_support']) / 2.0

        # Determine the threshold value
        threshold = df['quant_score'].quantile(1 - top_percentile)

        # Filter high potential candidates
        high_potential_df = df[df['quant_score'] >= threshold].copy()

        logger.info(f"Stage 1 completed. {len(high_potential_df)} companies passed the threshold ({top_percentile*100}%).")
        return high_potential_df

    def stage_two_soft_analysis(self, high_potential_df: pd.DataFrame):
        """
        Stage 2: Asynchronous qualitative analysis using DeepSeek.
        Pushes results to the BatchWriter.
        """
        total = len(high_potential_df)
        logger.info(f"Executing Stage 2: Qualitative Soft Analysis on {total} companies.")
        job_tracker.update(0, stage="Stage 2: Initializing", stage2_total=total)

        for idx, row in high_potential_df.iterrows():
            company_code = row['company_code']

            # Update global tracker for frontend polling
            job_tracker.update(idx + 1, f"Stage 2: Qualitative Soft Analysis ({idx+1}/{total})")

            # Mocking recent announcements fetching for the NLP model
            mock_announcement = f"Company {company_code} recently announced a plan to expand its manufacturing base due to current capacity constraints and strong financial backing."

            # Call DeepSeek API
            try:
                analysis = self.nlp_client.analyze_document(mock_announcement)
                strategic_intent_score = analysis.get('expansion_intent_score', 0.0)
            except Exception as e:
                logger.error(f"Failed NLP analysis for {company_code}: {e}")
                strategic_intent_score = 0.0

            # Prepare record for ORM batch insert
            record = {
                'company_code': company_code,
                'physical_capacity_score': row['physical_capacity_saturation'],
                'financial_support_score': row['financial_expansion_support'],
                'local_limitation_score': row['local_expansion_limitation'],
                'strategic_intent_score': strategic_intent_score,
                'last_updated': datetime.utcnow()
            }

            # Push to BatchWriter (will flush automatically at threshold)
            self.writer.add(record)

            # Artificial sleep to avoid overwhelming the API in this demonstration
            time.sleep(0.005)

        # Force flush any remaining records in the buffer at the end of the loop
        self.writer.flush()
        logger.info("Stage 2 completed. All records flushed to database.")

    def run_full_market_scan(self, total_companies: int = 5100):
        """Orchestrate the two-stage funnel process."""
        try:
            job_tracker.reset(total_companies)

            # Load Data
            market_df = self._mock_market_data(total_companies)

            # Stage 1
            high_potential_df = self.stage_one_hard_filter(market_df, top_percentile=0.20)

            # Reset index so iteration matches the length count for progress tracking
            high_potential_df = high_potential_df.reset_index(drop=True)

            # Stage 2
            self.stage_two_soft_analysis(high_potential_df)

            job_tracker.finish()

        except Exception as e:
            logger.error(f"Error during full market scan: {e}")
            job_tracker.status = "Failed"
            job_tracker.stage = f"Error: {str(e)}"