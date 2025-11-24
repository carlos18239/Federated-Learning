import asyncio
import websockets
import pickle
import time

from fl_main.lib.util.helpers import generate_id
from .conversion import Converter  
from .cnn import Net                       

async def register_client(port, ip="127.0.0.1"):
    uri = "ws://localhost:8888"

    async with websockets.connect(uri) as ws:

        # Generar ID único
        cid = generate_id()

        # ===============================
        # 1. Registrar nodo
        # ===============================
        msg = {
            "msg_type": "register",
            "component_id": cid,
            "ip": ip,
            "port": port
        }

        await ws.send(pickle.dumps(msg))
        reply = pickle.loads(await ws.recv())
        print(f"[CLIENT] Registro → {reply}")

        # Si la ventana de registro ya cerró
        if reply.get("status") != "ok":
            return

        print("[CLIENT] Registro exitoso. Esperando asignación de rol y modelo...")

        # ===============================
        # 2. Polling hasta obtener rol + modelo
        # ===============================
        role = None
        model = None
        aggregator_info = None

        while True:

            poll_msg = {
                "msg_type": "get_role_and_model",
                "component_id": cid
            }

            await ws.send(pickle.dumps(poll_msg))
            poll_reply = pickle.loads(await ws.recv())

            status = poll_reply.get("status", "")

            if status == "pending":
                print("[CLIENT] Esperando agregador... (polling)")
                time.sleep(2)
                continue

            elif status == "ok":
                role = poll_reply["role"]
                model = poll_reply["model"]
                aggregator_info = poll_reply["aggregator"]
                break

            else:
                print(f"[CLIENT] Error inesperado → {poll_reply}")
                return

        # ===============================
        # 3. Reconstruir red desde el modelo recibido
        # ===============================
        print(f"[CLIENT] Rol asignado = {role}")
        print(f"[CLIENT] Agregador: {aggregator_info}")
        
        print("[DEBUG] type(model) =", type(model))
        print("[DEBUG] len(model)  =", len(model))
        print("[DEBUG] keys (primeros 10) =", list(model.keys())[:10])

        # Convertir dict[numpy] → Net
        net = Converter.cvtr().convert_dict_nparray_to_nn(model)


        print("[CLIENT] Modelo inicial recibido y reconstruido.")

        return role, net, aggregator_info



if __name__ == "__main__":
    asyncio.run(register_client(port=9001))
