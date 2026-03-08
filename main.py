import os
import pandas as pd
import logging
from etl.adapters import IfindAdapter, TongdaxinAdapter, GenericFinancialAdapter
from nlp.deepseek_client import DeepSeek_LLM_Client
from business.matching_engine import MatchingEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_etl():
    logger.info("--- Testing ETL Adapters ---")

    ifind = IfindAdapter()
    df_ifind = ifind.get_standardized_10yr_financials("000001.SZ")
    logger.info(f"iFind Data (Top 2):\n{df_ifind.head(2)}")

    tongdaxin = TongdaxinAdapter()
    df_tdx = tongdaxin.get_standardized_10yr_financials("600000.SH")
    logger.info(f"Tongdaxin Data (Top 2):\n{df_tdx.head(2)}")

    generic = GenericFinancialAdapter()
    df_gen = generic.get_standardized_10yr_financials("AAPL")
    logger.info(f"Generic Data (Top 2):\n{df_gen.head(2)}")

def test_nlp():
    logger.info("--- Testing NLP DeepSeek Client ---")
    client = DeepSeek_LLM_Client()

    sample_text = "公司拟在华东地区投资新建产能基地，以解决当前的产能瓶颈问题，并期望获得当地政府的资金支持和产业协同效应。"
    result = client.analyze_document(sample_text)
    logger.info(f"NLP Extracted Result: {result}")

def test_business():
    logger.info("--- Testing Business Matching Engine ---")
    engine = MatchingEngine(input_dir="./data/test_inputs", processed_dir="./data/test_processed")

    # Create a dummy excel file for testing
    test_file = "./data/test_inputs/test_constraints.xlsx"
    dummy_data = {
        'region_name': ['Region A', 'Region B'],
        'energy_limit': [0.7, 0.4],
        'land_area': [0.6, 0.8],
        'supply_chain_proximity': [0.8, 0.5],
        'capital_support': [0.5, 0.9]
    }
    df = pd.DataFrame(dummy_data)
    df.to_excel(test_file, index=False)

    logger.info(f"Created test excel file at {test_file}")

    # Process the file
    engine.process_file(test_file)

    # Clean up test directories
    import shutil
    shutil.rmtree("./data/test_inputs")
    shutil.rmtree("./data/test_processed")
    logger.info("Cleaned up test directories.")

if __name__ == "__main__":
    logger.info("System Initialization Starting...")

    try:
        test_etl()
        test_nlp()
        test_business()
        logger.info("All system checks passed successfully.")
    except Exception as e:
        logger.error(f"System initialization failed: {e}")
