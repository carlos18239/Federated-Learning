import time
import json
import os
import random
import logging
import asyncio

from typing import Dict
import numpy as np

from .conversion import Converter
from .cnn import Net

from fl_main.lib.util.helpers import generate_id, read_config, set_config_file
from fl_main.lib.util.communication_handler import init_db_server, send_websocket, receive


def init_models() -> Dict[str, np.ndarray]:
    net = Net()
    return Converter.cvtr().convert_nn_to_dict_nparray(net)


class InitServer:
    """
    InitServer:
    - Ventana de registro: 30s (configurable)
    - Registra nodos (sin modelos)
    - Guarda participantes en JSON
    - Selecciona un agregador automáticamente al terminar la ventana
    - Mantiene el WebSocket abierto para múltiples mensajes (register, get_role_and_model, etc.)
    """

    def __init__(self):

        # ID del componente
        self.id = generate_id()
        self.global_model = init_models()

        # Leer archivo config init_config.json
        config_file = set_config_file("init")
        self.config = read_config(config_file)

        # Tiempo de ventana de registro
        self.reg_window = self.config.get("registration_window", 30)

        # JSON donde se guardará la información
        self.state_json_path = self.config.get("state_json_path", "init_state.json")

        # Crear archivo si no existe
        if not os.path.exists(self.state_json_path):
            with open(self.state_json_path, "w") as f:
                json.dump({"participants": [], "aggregator": None}, f, indent=2)

        # Cargar estado
        self.state = self._load_state()

        # Tiempo inicial
        self.start_time = time.time()

        # IP/PUERTO del servidor
        self.ip = self.config["init_ip"]
        self.port = self.config["init_socket"]

        logging.info(f"[InitServer] ID = {self.id}")
        logging.info(f"[InitServer] Ventana de registro = {self.reg_window} segundos")
        logging.info(f"[InitServer] JSON = {self.state_json_path}")

        # ============================================================
        # Crear tarea background que elegirá agregador automáticamente
        # ============================================================
        asyncio.get_event_loop().create_task(self.auto_select_aggregator())

    # ===============================================================
    # Métodos internos
    # ===============================================================

    def _load_state(self):
        """ Lee el JSON de estado """
        with open(self.state_json_path, "r") as f:
            return json.load(f)

    def _save_state(self):
        """ Guarda el JSON de estado """
        with open(self.state_json_path, "w") as f:
            json.dump(self.state, f, indent=2)

    # ===============================================================
    # TAREA AUTOMÁTICA: Elegir agregador después del tiempo límite
    # ===============================================================
    async def auto_select_aggregator(self):
        await asyncio.sleep(self.reg_window)

        if len(self.state["participants"]) > 0 and self.state["aggregator"] is None:
            agg = random.choice(self.state["participants"])
            self.state["aggregator"] = agg
            self._save_state()

            logging.info(
                f"[InitServer] >>> Ventana terminada. "
                f"Agregador elegido automáticamente: {agg}"
            )
        else:
            logging.info("[InitServer] >>> Ventana terminada, pero no hay participantes.")

    # ===============================================================
    # Handler principal (procesa mensajes, conexión persistente)
    # ===============================================================
    async def handler(self, websocket, path):
        while True:
            try:
                # Esperar un mensaje del cliente (pickle)
                msg = await receive(websocket)
            except Exception:
                # El cliente cerró la conexión → salimos del loop
                break

            msg_type = msg.get("msg_type", "")
            reply = {}

            # -----------------------------
            # 1) Registrar nodos
            # -----------------------------
            if msg_type == "register":

                elapsed = time.time() - self.start_time

                if elapsed <= self.reg_window:

                    participant = {
                        "component_id": msg.get("component_id"),
                        "ip": msg.get("ip"),
                        "port": msg.get("port"),
                    }

                    if participant not in self.state["participants"]:
                        self.state["participants"].append(participant)
                        self._save_state()

                    reply = {"status": "ok", "info": "registered"}

                else:
                    # La ventana de registro se cerró, ya no se aceptan nuevos
                    reply = {"status": "closed", "info": "registration_window_ended"}

            elif msg_type == "get_features_db":
                # Obtener las características de la base de datos desde el config
                db_features = self.config.get("database_features", {})
                reply = {
                    "status": "ok",
                    "database_features": db_features,
                }

            # -----------------------------
            # 2) Obtener el agregador elegido
            # -----------------------------
            elif msg_type == "get_aggregator":
                reply = {
                    "status": "ok",
                    "aggregator": self.state["aggregator"],
                }

            elif msg_type == "get_role_and_model":
                component_id = msg.get("component_id", None)
                agg = self.state["aggregator"]

                if agg is None:
                    # Aún no se ha elegido agregador (la tarea auto_select_aggregator no ha terminado)
                    reply = {
                        "status": "pending",
                        "info": "aggregator_not_selected_yet",
                    }
                else:
                    # Determinar si este nodo es el agregador o un cliente
                    agg_id = agg.get("component_id")
                    role = "aggregator" if component_id == agg_id else "client"

                    reply = {
                        "status": "ok",
                        "role": role,
                        "aggregator": agg,          # info del agregador (ip, port, id)
                        "model": self.global_model,  # dict[str, np.ndarray]
                    }

            else:
                reply = {"status": "error", "info": "unknown_msg_type"}

            # Enviar respuesta al cliente
            try:
                await send_websocket(reply, websocket)
            except Exception as e:
                logging.warning(f"[InitServer] Error enviando respuesta: {e}")
                break


# ===============================================================
# INICIAR SERVIDOR
# ===============================================================
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info("--- InitServer Started ---")

    init_server = InitServer()
    init_db_server(init_server.handler, init_server.ip, init_server.port)
