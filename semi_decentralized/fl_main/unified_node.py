"""
Unified Node Entry Point for Semi-Decentralized Federated Learning
====================================================================
This module implements the main entry point for the semi-decentralized FL system
where all nodes start as agents and one is dynamically selected as aggregator.

Usage:
    python -m fl_main.unified_node <node_name> <port> [threshold]

Arguments:
    node_name: Unique identifier for this node (e.g., 'raspberry1', 'a1', 'a2')
    port: Port number for this node's communication socket
    threshold: (Optional) Number of agents needed before selecting aggregator (default: 4)

Flow:
    1. All nodes register with DB as agents with random value (1-100)
    2. Wait until threshold of agents registered
    3. DB selects agent with highest random value as aggregator
    4. Selected node starts aggregator server
    5. Other nodes connect as clients to aggregator
    6. After aggregation, repeat selection for next round
"""

import sys
import asyncio
import logging
import time
import os
from typing import Optional

# Import existing components
from fl_main.lib.util.helpers import read_config, set_config_file, get_ip, generate_id
from fl_main.pseudodb.sqlite_db import SQLiteDBHandler

# Import for ML training
from fl_main.examples.image_classification.classification_engine import (
    init_models, training, compute_performance, judge_termination, TrainingMetaData
)
from fl_main.examples.image_classification.cnn import Net

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


class UnifiedNode:
    """
    Unified Node that can act as both Agent and Aggregator in semi-decentralized FL
    """

    def __init__(self, node_name: str, node_port: str, threshold: int = 4):
        """
        Initialize a unified node
        
        Args:
            node_name: Unique name for this node
            node_port: Port for this node's communication
            threshold: Number of agents needed before aggregator selection
        """
        self.node_name = node_name
        self.node_port = node_port
        self.node_id = generate_id()
        self.node_ip = get_ip()
        self.threshold = threshold
        
        # Role: None -> 'aggregator' or 'agent'
        self.role = None
        self.current_round = 0
        
        # Load DB configuration
        config_file = set_config_file("db")
        self.db_config = read_config(config_file)
        
        # Initialize DB handler
        db_path = f"{self.db_config['db_data_path']}/{self.db_config['db_name']}.db"
        self.db_handler = SQLiteDBHandler(db_path)
        
        # Try to initialize DB (will skip if already exists)
        try:
            self.db_handler.initialize_DB()
            logging.info("--- Database initialized ---")
        except Exception as e:
            logging.info(f"--- Database already exists or error: {e} ---")
        
        # Server and client instances (lazy loaded)
        self.server_instance = None
        self.client_instance = None
        
        logging.info(f"--- Unified Node '{node_name}' initialized (ID: {self.node_id}) ---")
        logging.info(f"--- IP: {self.node_ip}, Port: {self.node_port} ---")

    async def register_with_db(self) -> int:
        """
        Register this node with the database
        Returns the random value assigned (1-100)
        """
        logging.info(f"--- Registering node '{self.node_name}' with DB ---")
        random_value = self.db_handler.register_agent(
            agent_id=self.node_id,
            agent_name=self.node_name,
            agent_ip=self.node_ip,
            agent_port=self.node_port
        )
        logging.info(f"--- Node registered with random value: {random_value} ---")
        return random_value

    async def wait_for_threshold(self):
        """
        Wait until enough agents have registered (threshold reached)
        """
        logging.info(f"--- Waiting for {self.threshold} agents to register ---")
        
        while True:
            count = self.db_handler.get_registered_agents_count()
            logging.info(f"--- Currently {count}/{self.threshold} agents registered ---")
            
            if count >= self.threshold:
                logging.info("--- Threshold reached! ---")
                break
            
            await asyncio.sleep(2)  # Check every 2 seconds

    async def determine_role(self):
        """
        Query DB to determine if this node is the selected aggregator
        Sets self.role to 'aggregator' or 'agent'
        """
        logging.info("--- Determining role from DB ---")
        
        # Get current round from DB
        self.current_round = self.db_handler.get_current_round()
        
        # Select aggregator (DB picks highest random value)
        aggregator_info = self.db_handler.select_aggregator(self.current_round)
        
        if aggregator_info is None:
            logging.error("--- Failed to select aggregator ---")
            return False
        
        # Check if this node is the selected aggregator
        if aggregator_info['agent_id'] == self.node_id:
            self.role = 'aggregator'
            logging.info(f"🎯 --- THIS NODE SELECTED AS AGGREGATOR for round {self.current_round} ---")
        else:
            self.role = 'agent'
            logging.info(f"👤 --- This node will act as AGENT (Aggregator: {aggregator_info['agent_name']}) ---")
        
        # Small delay to ensure DB writes are visible to all nodes
        await asyncio.sleep(1)
        return True

    async def run_as_aggregator(self):
        """
        Execute the aggregator logic for this node
        """
        logging.info("=" * 60)
        logging.info("🔧 STARTING AS AGGREGATOR")
        logging.info("=" * 60)
        
        # Lazy import to avoid circular dependencies
        from fl_main.aggregator.server_th import Server
        
        # Update config to use this node's settings
        config_file = set_config_file("aggregator")
        config = read_config(config_file)
        
        # Override with semi-decentralized settings
        config['aggr_ip'] = self.node_ip
        config['semi_decentralized'] = True
        config['node_id'] = self.node_id
        config['node_name'] = self.node_name
        
        # Create and run server
        self.server_instance = Server()
        
        # Start server tasks
        try:
            # Create registration and receiving servers
            reg_task = asyncio.create_task(
                self._run_aggregator_server(
                    self.server_instance.register,
                    int(self.server_instance.reg_socket)
                )
            )
            
            recv_task = asyncio.create_task(
                self._run_aggregator_server(
                    self.server_instance.receive_msg_from_agent,
                    int(self.server_instance.recv_socket)
                )
            )
            
            synthesis_task = asyncio.create_task(
                self.server_instance.model_synthesis_routine()
            )
            
            # Wait for tasks
            await asyncio.gather(reg_task, recv_task, synthesis_task)
            
        except Exception as e:
            logging.error(f"--- Aggregator error: {e} ---")
            import traceback
            traceback.print_exc()

    async def _run_aggregator_server(self, handler, port):
        """Helper to run websocket server"""
        import websockets
        server = await websockets.serve(handler, "0.0.0.0", port)
        logging.info(f"--- Aggregator server listening on port {port} ---")
        await server.wait_closed()

    async def run_as_agent(self):
        """
        Execute the agent/client logic for this node
        """
        logging.info("=" * 60)
        logging.info("👤 STARTING AS AGENT")
        logging.info("=" * 60)
        
        # Get aggregator info from DB
        aggregator_info = self.db_handler.get_current_aggregator()
        
        if aggregator_info is None:
            logging.error("--- No aggregator information in DB ---")
            return
        
        logging.info(f"--- Connecting to aggregator: {aggregator_info['aggregator_id']} ---")
        logging.info(f"--- Aggregator IP: {aggregator_info['aggregator_ip']}, Port: {aggregator_info['aggregator_port']} ---")
        
        # Lazy import
        from fl_main.agent.client import Client
        
        # Override sys.argv to simulate the agent initialization
        # Format: script_name simulation_flag exch_socket agent_name
        original_argv = sys.argv.copy()
        sys.argv = [
            sys.argv[0],  # script name
            '1',  # simulation flag
            self.node_port,  # exchange socket
            self.node_name  # agent name
        ]
        
        try:
            # Create client instance
            self.client_instance = Client()
            
            # Override aggregator connection info from DB
            self.client_instance.aggr_ip = aggregator_info['aggregator_ip']
            
            # Start agent logic with ML training
            await self._run_agent_with_training()
            
        except Exception as e:
            logging.error(f"--- Agent error: {e} ---")
            import traceback
            traceback.print_exc()
        finally:
            # Restore original argv
            sys.argv = original_argv

    async def _run_agent_with_training(self):
        """
        Run the full agent lifecycle including ML training
        """
        from fl_main.lib.util.helpers import save_model_file, create_data_dict_from_models, create_meta_data_dict
        
        client = self.client_instance
        training_count = 0
        gm_arrival_count = 0
        
        # Initialize models
        logging.info("--- Initializing models ---")
        models = init_models()
        
        # Save initial models
        model_data_dict = create_data_dict_from_models(client.id, models)
        performance = 0.0
        meta_dict = create_meta_data_dict(performance, TrainingMetaData.num_training_data)
        save_model_file(client.model_path, client.lmfile, model_data_dict, meta_dict)
        
        # Participate (register with aggregator)
        logging.info("--- Participating in FL ---")
        await client.participate()
        
        # Start exchange routines
        if client.is_polling:
            exch_routine = asyncio.create_task(client.model_exchange_routine())
        else:
            import websockets
            wait_server = await websockets.serve(
                client.wait_models, "0.0.0.0", int(client.exch_socket)
            )
            exch_routine = asyncio.create_task(client.model_exchange_routine())
        
        # Main training loop
        while not judge_termination(training_count, gm_arrival_count):
            await asyncio.sleep(5)
            
            # Check for new global model and train
            from fl_main.lib.util.helpers import read_state
            from fl_main.lib.util.states import ClientState
            
            state = read_state(client.model_path, client.statefile)
            
            if state == ClientState.gm_ready:
                logging.info("--- New global model received, starting training ---")
                
                # Load global model
                from fl_main.lib.util.helpers import load_model_file
                data_dict, _ = load_model_file(client.model_path, client.gmfile)
                _, _, models, _ = data_dict
                
                # Train
                trained_models = training(models, init_flag=False)
                training_count += 1
                
                # Compute performance
                performance = compute_performance(trained_models, None, is_local=True)
                
                # Save trained model
                model_data_dict = create_data_dict_from_models(client.id, trained_models)
                meta_dict = create_meta_data_dict(performance, TrainingMetaData.num_training_data)
                save_model_file(client.model_path, client.lmfile, model_data_dict, meta_dict)
                
                # Update state to sending
                from fl_main.lib.util.helpers import write_state
                write_state(client.model_path, client.statefile, ClientState.sending)
                
                gm_arrival_count += 1
                logging.info(f"--- Training {training_count} complete, performance: {performance:.4f} ---")

    async def run(self):
        """
        Main execution flow for unified node
        """
        logging.info("=" * 60)
        logging.info(f"🚀 STARTING UNIFIED NODE: {self.node_name}")
        logging.info("=" * 60)
        
        try:
            # Step 1: Register with DB
            random_value = await self.register_with_db()
            
            # Step 2: Wait for threshold
            await self.wait_for_threshold()
            
            # Step 3: Determine role
            role_assigned = await self.determine_role()
            
            if not role_assigned:
                logging.error("--- Failed to assign role ---")
                return
            
            # Step 4: Execute based on role
            if self.role == 'aggregator':
                await self.run_as_aggregator()
            elif self.role == 'agent':
                await self.run_as_agent()
            else:
                logging.error(f"--- Unknown role: {self.role} ---")
                
        except KeyboardInterrupt:
            logging.info("--- Node stopped by user ---")
        except Exception as e:
            logging.error(f"--- Node error: {e} ---")
            import traceback
            traceback.print_exc()


def main():
    """
    Main entry point for unified node
    """
    if len(sys.argv) < 3:
        print("Usage: python -m fl_main.unified_node <node_name> <port> [threshold]")
        print("Example: python -m fl_main.unified_node raspberry1 50001 4")
        sys.exit(1)
    
    node_name = sys.argv[1]
    node_port = sys.argv[2]
    threshold = int(sys.argv[3]) if len(sys.argv) > 3 else 4
    
    # Create and run node
    node = UnifiedNode(node_name, node_port, threshold)
    
    # Run async main loop
    asyncio.run(node.run())


if __name__ == "__main__":
    main()
