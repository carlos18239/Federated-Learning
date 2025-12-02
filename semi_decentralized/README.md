# Sistema Semi-Descentralizado de Federated Learning

Sistema de aprendizaje federado semi-descentralizado con agregador rotativo para 4 Raspberry Pis.

## 📖 Documentación

**Ver [`INSTRUCCIONES.txt`](INSTRUCCIONES.txt)** para la guía completa.

## 🚀 Inicio Rápido

### 1. Configurar

Editar `setups/config_db.json` y `setups/config_aggregator.json` con la IP de tu Raspberry Pi 1.

### 2. Inicializar DB (solo en Pi 1)

```bash
python3 -m fl_main.init_db
```

### 3. Iniciar Nodos (en cada Pi)

```bash
# Pi 1
python3 -m fl_main.unified_node pi1 50001 4

# Pi 2
python3 -m fl_main.unified_node pi2 50002 4

# Pi 3
python3 -m fl_main.unified_node pi3 50003 4

# Pi 4
python3 -m fl_main.unified_node pi4 50004 4
```

## ✅ Verificar Config

```bash
python3 check_config.py
```

## 🎯 Características

- Agregador rotativo automático
- Sin punto único de fallo
- Selección aleatoria justa (random 1-100)
- Todos los nodos inician iguales

## 📦 Dependencias

```bash
pip install websockets numpy torch torchvision
```

Ver [`INSTRUCCIONES.txt`](INSTRUCCIONES.txt) para más detalles.




