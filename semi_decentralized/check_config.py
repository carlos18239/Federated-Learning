#!/usr/bin/env python3
"""
Configuration Checker for Semi-Decentralized FL
================================================
This script verifies that your JSON configuration files are correctly
set up for the semi-decentralized federated learning system.

Usage:
    python3 check_config.py

It will check:
- All required fields are present
- Semi-decentralized flags are set correctly
- DB IP is configured
- Threshold matches expected setup
- Consistency between config files
"""

import json
import sys
import os
from pathlib import Path

# ANSI color codes for pretty output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
BOLD = '\033[1m'
RESET = '\033[0m'

def print_header(text):
    print(f"\n{BLUE}{BOLD}{'='*70}{RESET}")
    print(f"{BLUE}{BOLD}{text.center(70)}{RESET}")
    print(f"{BLUE}{BOLD}{'='*70}{RESET}\n")

def print_success(text):
    print(f"{GREEN}✅ {text}{RESET}")

def print_error(text):
    print(f"{RED}❌ {text}{RESET}")

def print_warning(text):
    print(f"{YELLOW}⚠️  {text}{RESET}")

def print_info(text):
    print(f"{BLUE}ℹ️  {text}{RESET}")

def load_config(config_path):
    """Load a JSON config file"""
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        print_error(f"Config file not found: {config_path}")
        return None
    except json.JSONDecodeError as e:
        print_error(f"Invalid JSON in {config_path}: {e}")
        return None

def check_db_config(config):
    """Check database configuration"""
    print_header("Checking config_db.json")
    
    issues = []
    
    # Check db_ip
    db_ip = config.get('db_ip', '')
    if not db_ip or db_ip == "172.23.211.109":
        print_error("db_ip is not configured or still has default value")
        print_info("  Set db_ip to the IP address of the Raspberry Pi hosting the database")
        print_info("  Example: '192.168.1.101'")
        issues.append("db_ip needs to be configured")
    elif db_ip == "localhost" or db_ip == "127.0.0.1":
        print_warning("db_ip is set to localhost")
        print_info("  This will only work if all nodes run on the same machine")
        print_info("  For Raspberry Pis, use the actual IP address (e.g., '192.168.1.101')")
    else:
        print_success(f"db_ip is configured: {db_ip}")
    
    # Check other fields
    required_fields = ['db_socket', 'db_name', 'db_data_path', 'db_model_path']
    for field in required_fields:
        if field in config:
            print_success(f"{field}: {config[field]}")
        else:
            print_error(f"Missing required field: {field}")
            issues.append(f"Missing {field}")
    
    return issues, db_ip

def check_aggregator_config(config, db_ip_from_db_config):
    """Check aggregator configuration"""
    print_header("Checking config_aggregator.json")
    
    issues = []
    
    # Check semi_decentralized
    if config.get('semi_decentralized') != True:
        print_error("semi_decentralized is not set to true")
        print_info("  For semi-decentralized mode, this MUST be true")
        issues.append("semi_decentralized must be true")
    else:
        print_success("semi_decentralized: true ✓")
    
    # Check enable_aggregator_rotation
    if config.get('enable_aggregator_rotation') != True:
        print_error("enable_aggregator_rotation is not set to true")
        print_info("  For rotating aggregator, this MUST be true")
        issues.append("enable_aggregator_rotation must be true")
    else:
        print_success("enable_aggregator_rotation: true ✓")
    
    # Check db_ip consistency
    db_ip = config.get('db_ip', '')
    if db_ip != db_ip_from_db_config:
        print_error(f"db_ip mismatch!")
        print_info(f"  config_db.json has: {db_ip_from_db_config}")
        print_info(f"  config_aggregator.json has: {db_ip}")
        print_info("  These MUST be the same!")
        issues.append("db_ip mismatch between config files")
    else:
        print_success(f"db_ip matches config_db.json: {db_ip}")
    
    # Check agent_registration_threshold
    threshold = config.get('agent_registration_threshold', 0)
    if threshold < 2:
        print_error(f"agent_registration_threshold is too low: {threshold}")
        print_info("  Should be at least 2, typically 3-4 for meaningful FL")
        issues.append("agent_registration_threshold too low")
    elif threshold > 10:
        print_warning(f"agent_registration_threshold is high: {threshold}")
        print_info("  Make sure you actually have this many Raspberry Pis!")
    else:
        print_success(f"agent_registration_threshold: {threshold}")
    
    # Check aggregation_threshold
    agg_threshold = config.get('aggregation_threshold', 0)
    if agg_threshold <= 0 or agg_threshold > 1:
        print_warning(f"aggregation_threshold is unusual: {agg_threshold}")
        print_info("  Should be between 0.1 (10%) and 1.0 (100%)")
        print_info("  Typical values: 0.5 (50%), 0.7 (70%), 1.0 (100%)")
    else:
        print_success(f"aggregation_threshold: {agg_threshold} ({int(agg_threshold*100)}%)")
    
    return issues

def check_agent_config(config):
    """Check agent configuration"""
    print_header("Checking config_agent.json")
    
    issues = []
    
    # Check semi_decentralized
    if config.get('semi_decentralized') != True:
        print_error("semi_decentralized is not set to true")
        print_info("  For semi-decentralized mode, this MUST be true")
        issues.append("semi_decentralized must be true")
    else:
        print_success("semi_decentralized: true ✓")
    
    # Check query_db_for_aggregator
    if config.get('query_db_for_aggregator') != True:
        print_error("query_db_for_aggregator is not set to true")
        print_info("  For semi-decentralized mode, this MUST be true")
        issues.append("query_db_for_aggregator must be true")
    else:
        print_success("query_db_for_aggregator: true ✓")
    
    # Info about aggr_ip
    aggr_ip = config.get('aggr_ip', '')
    print_info(f"aggr_ip: {aggr_ip} (ignored in semi-decentralized mode)")
    
    return issues

def main():
    """Main verification function"""
    print_header("🔧 Semi-Decentralized FL Configuration Checker")
    
    # Check if we're in the right directory
    if not os.path.exists('setups'):
        print_error("Cannot find 'setups' directory!")
        print_info("Please run this script from the project root directory:")
        print_info("  cd /path/to/semi_decentralized")
        print_info("  python3 check_config.py")
        sys.exit(1)
    
    all_issues = []
    
    # Load configs
    db_config = load_config('setups/config_db.json')
    aggregator_config = load_config('setups/config_aggregator.json')
    agent_config = load_config('setups/config_agent.json')
    
    if not db_config or not aggregator_config or not agent_config:
        print_error("Failed to load one or more config files!")
        sys.exit(1)
    
    # Check each config
    issues, db_ip = check_db_config(db_config)
    all_issues.extend(issues)
    
    issues = check_aggregator_config(aggregator_config, db_ip)
    all_issues.extend(issues)
    
    issues = check_agent_config(agent_config)
    all_issues.extend(issues)
    
    # Summary
    print_header("Summary")
    
    if not all_issues:
        print_success("All checks passed! ✅")
        print_info("Your configuration looks good for semi-decentralized FL.")
        print_info("")
        print_info("Next steps:")
        print_info("  1. Copy the project to all Raspberry Pis")
        print_info("  2. Initialize DB: python3 -m fl_main.init_db")
        print_info("  3. Start nodes: python3 -m fl_main.unified_node <name> <port> <threshold>")
        print_info("")
        print_info("See INSTRUCCIONES.txt for detailed instructions.")
        return 0
    else:
        print_error(f"Found {len(all_issues)} issue(s) that need attention:")
        for i, issue in enumerate(all_issues, 1):
            print(f"  {i}. {issue}")
        print_info("")
        print_info("Please fix these issues before deploying.")
        print_info("See INSTRUCCIONES.txt for configuration help.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
