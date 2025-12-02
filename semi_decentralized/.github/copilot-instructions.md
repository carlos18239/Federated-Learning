<!-- Copilot instructions for the semi_decentralized simple-fl project -->
# Copilot instructions — simple-fl (semi_decentralized)

Purpose
- Help an AI coding assistant be productive quickly in this repository: the code implements a small federated learning in semi descentralized model taht means is that we have rotative aggregator and use the db for that have information about the ips and sockets and comunication platform with Agent (client), Aggregator (server), util helpers and a simple pseudo-DB.

Quick architecture summary
- **Agent (client)**: `simple-fl/fl_main/agent/client.py` — registers with aggregator, sends local models, and receives global models. Uses `fl_main.lib.util.helpers` to load/save models and `communication_handler` for websockets.
- **Aggregator (server)**: `simple-fl/fl_main/aggregator/server_th.py` (instantiates `Server`) and `simple-fl/fl_main/aggregator/aggregation.py` — receives participation and model uploads, forms cluster/global models and pushes to DB.
- **State & orchestration**: `simple-fl/fl_main/aggregator/state_manager.py` keeps runtime state (agents, buffers, rounds, model names); aggregation threshold and round timing are configured in JSON.
- **Utilities & messaging**: `simple-fl/fl_main/lib/util/communication_handler.py` (websockets + pickle), `messengers.py`, `states.py`, and `helpers.py` define message formats, enums, model file I/O and state file conventions.
- **Persistence**: `simple-fl/fl_main/pseudodb/sqlite_db.py` — the aggregator pushes models to a SQLite DB; DB path and ports are in `setups/config_db.json`.

Important patterns & conventions (project-specific)
- Message transport: websockets carrying Python-pickled lists/objects. Always use the `messengers` helpers and the `states` enums for indices — messages are parsed by index, not by dict keys.
- Model files: models are saved/loaded with `helpers.save_model_file` / `helpers.load_model_file`. Models live under directories configured by `model_path` and filenames from the JSON configs (e.g., `local_model_file_name`, `global_model_file_name`).
- Agent state machine: agent state is a plain file (name from `state_file_name` in config). Use `helpers.read_state` / `helpers.write_state` and the `ClientState` enum when changing or reading state.
- Aggregation trigger: `StateManager.ready_for_local_aggregation()` controls when the aggregator runs aggregation (threshold is `aggregation_threshold` in `config_aggregator.json`). Modify that logic with care.
- Initialization: the first agent to register may determine model shapes — see `_initialize_fl` in `server_th.py`. Changes that affect model shapes must be backwards-compatible.

Dev workflows / run commands
- Check JSON configs before running: `simple-fl/setups/config_agent.json`, `simple-fl/setups/config_aggregator.json`, `simple-fl/setups/config_db.json`.
- Install runtime deps (simple example):
```
pip install websockets numpy
```
- Start the aggregator (run from repo root):
```
python3 simple-fl/fl_main/aggregator/server_th.py
```
- Start an agent (normal run):
```
python3 simple-fl/fl_main/agent/client.py
```
- Start an agent in simulation mode (pass flags used by code):
```
python3 simple-fl/fl_main/agent/client.py 1 9001 agent_name
```
  - meaning: `1` enables simulation; `9001` is the exchange socket; `agent_name` is used for local model path.

Key files to consult when changing behavior
- Message layout & constants: `simple-fl/fl_main/lib/util/states.py` and `simple-fl/fl_main/lib/util/messengers.py` — always update both when changing indices/fields.
- Model I/O & state helpers: `simple-fl/fl_main/lib/util/helpers.py` — use these functions instead of ad hoc pickle I/O.
- Communication primitives: `simple-fl/fl_main/lib/util/communication_handler.py` — holds websocket server/client helpers and `send/receive` semantics.
- DB contract: `simple-fl/fl_main/pseudodb/sqlite_db.py` + `simple-fl/fl_main/aggregator/server_th.py` `_push_models` usage — aggregator assumes DB accepts pickled messages on a websocket-like interface.

Safety notes for AI edits (important)
- Maintain pickle compatibility: messages are pickled lists/objects; refactoring to dicts or JSON requires coordinated changes in `messengers.py`, `communication_handler.py`, and all send/receive call sites.
- Do not change numeric message-index constants without updating all call sites and tests — message parsing is index-based.
- Preserve model shape compatibility: changing NN tensor shapes requires a clear migration path (first-agent initialization behavior is sensitive).

If you modify or add features
- Update `setups/*.json` with new ports/paths and document any new keys in `simple-fl/fl_main/README.md`.
- Add a short example script under `simple-fl/examples/` demonstrating the new flow (agent <-> aggregator) and updating `README.md`.

Questions for the maintainer
- Do you want migration helpers for changing model shapes? (e.g., auto-convert old model arrays)
- Should we replace pickle/websockets with JSON/HTTP for cross-language compatibility?

If anything above is unclear or you want this shortened/expanded, tell me which sections to iterate on.
