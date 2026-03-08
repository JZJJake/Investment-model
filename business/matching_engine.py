import pandas as pd
import numpy as np
import os
import glob
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MatchingEngine:
    """
    Business matching engine to match dynamic inputs from user (via Excel)
    with high-scoring enterprise requirements.
    """

    def __init__(self, input_dir: str = "./data/inputs", processed_dir: str = "./data/processed"):
        self.input_dir = input_dir
        self.processed_dir = processed_dir
        os.makedirs(self.input_dir, exist_ok=True)
        os.makedirs(self.processed_dir, exist_ok=True)

        # Define the dimensions expected in the matrix
        self.dimensions = ['energy_limit', 'land_area', 'supply_chain_proximity', 'capital_support']

    def poll_directory(self, interval_seconds: int = 5):
        """Poll the input directory for new Excel files."""
        logger.info(f"Started polling directory: {self.input_dir}")
        try:
            while True:
                excel_files = glob.glob(os.path.join(self.input_dir, "*.xlsx"))
                for file_path in excel_files:
                    logger.info(f"Found new file: {file_path}")
                    self.process_file(file_path)

                    # Move to processed directory
                    filename = os.path.basename(file_path)
                    os.rename(file_path, os.path.join(self.processed_dir, filename))

                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Polling stopped by user.")

    def parse_excel_constraints(self, file_path: str) -> pd.DataFrame:
        """Parse the input Excel file to extract constraints."""
        try:
            # Expecting columns: region_name, energy_limit, land_area, supply_chain_proximity, capital_support
            df = pd.read_excel(file_path)

            # Basic validation
            missing_cols = [col for col in self.dimensions if col not in df.columns]
            if missing_cols:
                raise ValueError(f"Missing expected columns in Excel: {missing_cols}")

            return df
        except Exception as e:
            logger.error(f"Error parsing {file_path}: {e}")
            raise

    def match_enterprises(self, constraints_df: pd.DataFrame, enterprise_needs_df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculate match score using matrix dot product.
        constraints_df: region profiles
        enterprise_needs_df: enterprise profiles and requirements
        """
        # Ensure both dataframes have the necessary dimensions aligned
        c_matrix = constraints_df[self.dimensions].values # Shape: (num_regions, num_dims)
        e_matrix = enterprise_needs_df[self.dimensions].values # Shape: (num_enterprises, num_dims)

        # Normalization (optional, but good practice for dot product similarity)
        # Using L2 norm for cosine similarity like approach, or standard scaling
        c_norm = np.linalg.norm(c_matrix, axis=1, keepdims=True)
        c_norm[c_norm == 0] = 1 # avoid div by zero
        c_matrix_normalized = c_matrix / c_norm

        e_norm = np.linalg.norm(e_matrix, axis=1, keepdims=True)
        e_norm[e_norm == 0] = 1
        e_matrix_normalized = e_matrix / e_norm

        # Matrix dot product -> score matrix (num_regions x num_enterprises)
        scores = np.dot(c_matrix_normalized, e_matrix_normalized.T)

        # Format the result
        results = []
        for i, region_row in constraints_df.iterrows():
            region_name = region_row.get('region_name', f'Region_{i}')
            for j, ent_row in enterprise_needs_df.iterrows():
                enterprise_name = ent_row.get('enterprise_name', f'Ent_{j}')
                score = scores[i, j]

                results.append({
                    'region_name': region_name,
                    'enterprise_name': enterprise_name,
                    'match_score': score
                })

        # Return sorted by match score descending
        result_df = pd.DataFrame(results).sort_values(by='match_score', ascending=False)
        return result_df

    def process_file(self, file_path: str):
        """End-to-end processing of a single uploaded constraints file."""
        logger.info(f"Processing constraints from {file_path}")
        constraints_df = self.parse_excel_constraints(file_path)

        # Mocking enterprise needs (normally this would come from the DB/NLP processing pipeline)
        mock_enterprise_needs = pd.DataFrame([
            {'enterprise_name': 'Tech Corp A', 'energy_limit': 0.8, 'land_area': 0.5, 'supply_chain_proximity': 0.9, 'capital_support': 0.6},
            {'enterprise_name': 'Mfg Co B', 'energy_limit': 0.2, 'land_area': 0.9, 'supply_chain_proximity': 0.3, 'capital_support': 0.8},
        ])

        results_df = self.match_enterprises(constraints_df, mock_enterprise_needs)
        logger.info(f"Match Results:\n{results_df}")
        return results_df
