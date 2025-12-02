#!/bin/bash

# Script para obtener la IP de tu PC y configurar automáticamente

echo "========================================"
echo "  Configuración Automática de IP"
echo "========================================"
echo ""

# Detectar IP
echo "Detectando la IP de tu PC..."
IP=$(ip -4 addr show | grep -oP '(?<=inet\s)\d+(\.\d+){3}' | grep -v '127.0.0.1' | head -n 1)

if [ -z "$IP" ]; then
    echo "❌ No se pudo detectar la IP automáticamente"
    echo ""
    echo "Para encontrar tu IP manualmente:"
    echo "  Linux: ip addr | grep inet"
    echo "  Mac: ifconfig | grep inet"
    echo "  Windows: ipconfig"
    exit 1
fi

echo "✅ IP detectada: $IP"
echo ""

# Preguntar si quiere usar esta IP
read -p "¿Usar esta IP para la base de datos? (s/n): " respuesta

if [[ $respuesta != "s" && $respuesta != "S" ]]; then
    echo ""
    read -p "Ingresa la IP manualmente: " IP
fi

echo ""
echo "Configurando archivos JSON con IP: $IP"
echo ""

# Actualizar config_db.json
if [ -f "setups/config_db.json" ]; then
    sed -i "s/\"db_ip\": \".*\"/\"db_ip\": \"$IP\"/" setups/config_db.json
    echo "✅ config_db.json actualizado"
else
    echo "⚠️  No se encontró setups/config_db.json"
fi

# Actualizar config_aggregator.json
if [ -f "setups/config_aggregator.json" ]; then
    sed -i "s/\"db_ip\": \".*\"/\"db_ip\": \"$IP\"/" setups/config_aggregator.json
    echo "✅ config_aggregator.json actualizado"
else
    echo "⚠️  No se encontró setups/config_aggregator.json"
fi

echo ""
echo "=========================================="
echo "  Configuración completada!"
echo "=========================================="
echo ""
echo "Tu PC tendrá la base de datos en: $IP:9017"
echo ""
echo "Siguiente paso:"
echo "  1. Inicializar DB: python3 -m fl_main.init_db"
echo "  2. Copiar proyecto a Raspberry Pis"
echo "  3. Iniciar nodos en cada Raspberry Pi"
echo ""
