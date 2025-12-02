import sqlite3
import datetime
import logging
import random
import time

# Message type between aggregators and DB
from fl_main.lib.util.states import ModelType

class SQLiteDBHandler:
    """
        SQLiteDB Handler class that creates and initialize SQLite DB,
        and inserts models to the SQLiteDB.
        Extended to support semi-decentralized FL with rotating aggregator.
    """

    def __init__(self, db_file):
        self.db_file = db_file

    def initialize_DB(self):
        conn = sqlite3.connect(f'{self.db_file}')
        c = conn.cursor()

        # create table for each model types
        # local
        c.execute('''CREATE TABLE IF NOT EXISTS local_models(model_id, generation_time, agent_id, round, performance, num_samples)''')

        # cluster
        c.execute('''CREATE TABLE IF NOT EXISTS cluster_models(model_id, generation_time, aggregator_id, round, num_samples)''')

        # registered agents (for semi-decentralized mode)
        c.execute('''CREATE TABLE IF NOT EXISTS registered_agents(
            agent_id TEXT PRIMARY KEY,
            agent_name TEXT,
            agent_ip TEXT,
            agent_port TEXT,
            random_value INTEGER,
            registration_time TEXT,
            is_active INTEGER DEFAULT 1
        )''')

        # current aggregator info (for semi-decentralized mode)
        c.execute('''CREATE TABLE IF NOT EXISTS current_aggregator(
            round INTEGER PRIMARY KEY,
            aggregator_id TEXT,
            aggregator_ip TEXT,
            aggregator_port TEXT,
            selection_time TEXT,
            status TEXT DEFAULT 'active'
        )''')

        # round control (for tracking FL rounds in semi-decentralized)
        c.execute('''CREATE TABLE IF NOT EXISTS round_control(
            id INTEGER PRIMARY KEY,
            current_round INTEGER DEFAULT 0,
            agents_registered INTEGER DEFAULT 0,
            aggregation_complete INTEGER DEFAULT 0,
            last_update TEXT
        )''')

        # Initialize round control with a single row
        c.execute('''INSERT OR IGNORE INTO round_control (id, current_round) VALUES (1, 0)''')

        conn.commit()
        conn.close()

    def insert_an_entry(self,
                         component_id: str,
                         r: int,
                         mt: ModelType,
                         model_id: str,
                         gtime: float,
                         local_prfmc: float,
                         num_samples: int
                        ):

        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()

        t = datetime.datetime.fromtimestamp(gtime)
        gene_time = t.strftime('%m/%d/%Y %H:%M:%S')

        if mt == ModelType.local:
            c.execute('''INSERT INTO local_models VALUES (?, ?, ?, ?, ?, ?);''', (model_id, gene_time, component_id, r, local_prfmc, num_samples))
            logging.info(f"--- Local Models are saved ---")

        elif mt == ModelType.cluster:
            c.execute('''INSERT INTO cluster_models VALUES (?, ?, ?, ?, ?);''', (model_id, gene_time, component_id, r, num_samples))
            logging.info(f"--- Cluster Models are saved ---")

        else:
            logging.info(f"--- Nothing saved ---")

        conn.commit()
        conn.close()

    def register_agent(self, agent_id: str, agent_name: str, agent_ip: str, agent_port: str) -> int:
        """
        Register an agent in the semi-decentralized system and assign random value (1-100)
        Returns the random value assigned to the agent
        """
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()

        random_value = random.randint(1, 100)
        registration_time = datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S')

        # Check if agent already exists
        c.execute('''SELECT agent_id FROM registered_agents WHERE agent_id = ?''', (agent_id,))
        existing = c.fetchone()

        if existing:
            # Update existing agent
            c.execute('''UPDATE registered_agents 
                        SET agent_name=?, agent_ip=?, agent_port=?, random_value=?, 
                            registration_time=?, is_active=1
                        WHERE agent_id=?''',
                     (agent_name, agent_ip, agent_port, random_value, registration_time, agent_id))
        else:
            # Insert new agent
            c.execute('''INSERT INTO registered_agents 
                        (agent_id, agent_name, agent_ip, agent_port, random_value, registration_time, is_active)
                        VALUES (?, ?, ?, ?, ?, ?, 1)''',
                     (agent_id, agent_name, agent_ip, agent_port, random_value, registration_time))

        # Update agents_registered count
        c.execute('''UPDATE round_control SET agents_registered = agents_registered + 1 WHERE id = 1''')

        conn.commit()
        conn.close()

        logging.info(f"--- Agent {agent_name} registered with random value: {random_value} ---")
        return random_value

    def get_registered_agents_count(self) -> int:
        """
        Get the count of active registered agents
        """
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        c.execute('''SELECT COUNT(*) FROM registered_agents WHERE is_active = 1''')
        count = c.fetchone()[0]
        
        conn.close()
        return count

    def select_aggregator(self, current_round: int) -> dict:
        """
        Select the aggregator based on highest random value among registered agents
        Returns dict with aggregator info: {agent_id, agent_ip, agent_port, random_value}
        """
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()

        # Select agent with highest random value
        c.execute('''SELECT agent_id, agent_name, agent_ip, agent_port, random_value 
                    FROM registered_agents 
                    WHERE is_active = 1 
                    ORDER BY random_value DESC 
                    LIMIT 1''')
        
        result = c.fetchone()
        
        if result:
            aggregator_info = {
                'agent_id': result[0],
                'agent_name': result[1],
                'agent_ip': result[2],
                'agent_port': result[3],
                'random_value': result[4]
            }

            # Save to current_aggregator table
            selection_time = datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S')
            c.execute('''INSERT OR REPLACE INTO current_aggregator 
                        (round, aggregator_id, aggregator_ip, aggregator_port, selection_time, status)
                        VALUES (?, ?, ?, ?, ?, 'active')''',
                     (current_round, result[0], result[2], result[3], selection_time))
            
            conn.commit()
            logging.info(f"--- Aggregator selected: {result[1]} (ID: {result[0]}) with value {result[4]} ---")
        else:
            aggregator_info = None
            logging.error("--- No agents registered to select aggregator ---")

        conn.close()
        return aggregator_info

    def get_current_aggregator(self) -> dict:
        """
        Get the current active aggregator information
        Returns dict with aggregator info or None if no aggregator is set
        """
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()

        c.execute('''SELECT round, aggregator_id, aggregator_ip, aggregator_port 
                    FROM current_aggregator 
                    WHERE status = 'active' 
                    ORDER BY round DESC 
                    LIMIT 1''')
        
        result = c.fetchone()
        conn.close()

        if result:
            return {
                'round': result[0],
                'aggregator_id': result[1],
                'aggregator_ip': result[2],
                'aggregator_port': result[3]
            }
        return None

    def increment_round(self) -> int:
        """
        Increment the FL round counter and reset agent registrations for new round
        Returns the new round number
        """
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()

        # Increment round
        c.execute('''UPDATE round_control 
                    SET current_round = current_round + 1,
                        agents_registered = 0,
                        aggregation_complete = 0,
                        last_update = ?
                    WHERE id = 1''', (datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S'),))

        # Get new round number
        c.execute('''SELECT current_round FROM round_control WHERE id = 1''')
        new_round = c.fetchone()[0]

        # Reset random values for all agents for next round
        c.execute('''UPDATE registered_agents SET is_active = 1''')

        conn.commit()
        conn.close()

        logging.info(f"--- Round incremented to: {new_round} ---")
        return new_round

    def get_current_round(self) -> int:
        """
        Get the current FL round number
        """
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        c.execute('''SELECT current_round FROM round_control WHERE id = 1''')
        result = c.fetchone()
        
        conn.close()
        return result[0] if result else 0

    def mark_aggregation_complete(self):
        """
        Mark that aggregation has been completed for current round
        """
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        c.execute('''UPDATE round_control 
                    SET aggregation_complete = 1,
                        last_update = ?
                    WHERE id = 1''', (datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S'),))
        
        conn.commit()
        conn.close()
        logging.info("--- Aggregation marked as complete ---")

    def is_aggregation_complete(self) -> bool:
        """
        Check if aggregation has been completed for current round
        """
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()
        
        c.execute('''SELECT aggregation_complete FROM round_control WHERE id = 1''')
        result = c.fetchone()
        
        conn.close()
        return bool(result[0]) if result else False

    def reset_for_new_round(self):
        """
        Reset the database state for a new aggregator selection round
        Reassigns new random values to all agents
        """
        conn = sqlite3.connect(self.db_file)
        c = conn.cursor()

        # Assign new random values to all active agents
        c.execute('''SELECT agent_id FROM registered_agents WHERE is_active = 1''')
        agents = c.fetchall()
        
        for (agent_id,) in agents:
            new_random = random.randint(1, 100)
            c.execute('''UPDATE registered_agents SET random_value = ? WHERE agent_id = ?''',
                     (new_random, agent_id))
        
        # Mark previous aggregator as inactive
        c.execute('''UPDATE current_aggregator SET status = 'inactive' WHERE status = 'active' ''')

        conn.commit()
        conn.close()
        logging.info("--- Database reset for new round, new random values assigned ---")
