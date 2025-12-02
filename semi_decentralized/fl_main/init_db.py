"""
Database Initialization Script for Semi-Decentralized FL
=========================================================
This script initializes the SQLite database for the semi-decentralized
federated learning system.

Usage:
    python -m fl_main.init_db

This will create the database with all necessary tables for:
- Agent registration
- Aggregator selection
- Round control
- Model storage (local and cluster models)
"""

import sys
import logging
from fl_main.lib.util.helpers import read_config, set_config_file
from fl_main.pseudodb.sqlite_db import SQLiteDBHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def init_database():
    """
    Initialize the database for semi-decentralized FL
    """
    logging.info("=" * 60)
    logging.info("🗄️  INITIALIZING DATABASE FOR SEMI-DECENTRALIZED FL")
    logging.info("=" * 60)
    
    # Load DB configuration
    config_file = set_config_file("db")
    db_config = read_config(config_file)
    
    # Construct DB path
    db_path = f"{db_config['db_data_path']}/{db_config['db_name']}.db"
    
    logging.info(f"--- Database path: {db_path} ---")
    
    # Create DB handler and initialize
    db_handler = SQLiteDBHandler(db_path)
    
    try:
        db_handler.initialize_DB()
        logging.info("✅ --- Database initialized successfully ---")
        logging.info("")
        logging.info("Tables created:")
        logging.info("  - local_models: Stores local models from agents")
        logging.info("  - cluster_models: Stores aggregated global models")
        logging.info("  - registered_agents: Tracks all registered agents with random values")
        logging.info("  - current_aggregator: Stores current aggregator information")
        logging.info("  - round_control: Manages FL rounds and thresholds")
        logging.info("")
        logging.info("✨ Database is ready for semi-decentralized FL!")
        
    except Exception as e:
        logging.error(f"❌ --- Error initializing database: {e} ---")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    init_database()
