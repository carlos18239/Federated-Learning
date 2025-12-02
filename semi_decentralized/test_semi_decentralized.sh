#!/bin/bash

# Quick Test Script for Semi-Decentralized FL
# ============================================
# This script helps test the semi-decentralized system locally
# by launching multiple nodes in the background

echo "=========================================="
echo "Semi-Decentralized FL - Quick Test"
echo "=========================================="
echo ""

# Check if we're in the right directory
if [ ! -f "fl_main/unified_node.py" ]; then
    echo "❌ Error: Please run this script from the repository root"
    exit 1
fi

# Step 1: Initialize database
echo "Step 1: Initializing database..."
python -m fl_main.init_db
if [ $? -ne 0 ]; then
    echo "❌ Database initialization failed"
    exit 1
fi
echo "✅ Database initialized"
echo ""

# Step 2: Start nodes
echo "Step 2: Starting 3 test nodes..."
echo "   (They will run in background, check logs in test_logs/)"
echo ""

# Create logs directory
mkdir -p test_logs

# Start nodes with threshold=3
echo "Starting node1 on port 50001..."
python -m fl_main.unified_node node1 50001 3 > test_logs/node1.log 2>&1 &
NODE1_PID=$!

sleep 2

echo "Starting node2 on port 50002..."
python -m fl_main.unified_node node2 50002 3 > test_logs/node2.log 2>&1 &
NODE2_PID=$!

sleep 2

echo "Starting node3 on port 50003..."
python -m fl_main.unified_node node3 50003 3 > test_logs/node3.log 2>&1 &
NODE3_PID=$!

echo ""
echo "✅ All nodes started!"
echo ""
echo "Node PIDs:"
echo "  node1: $NODE1_PID"
echo "  node2: $NODE2_PID"
echo "  node3: $NODE3_PID"
echo ""
echo "Logs are being written to test_logs/"
echo ""
echo "To monitor logs:"
echo "  tail -f test_logs/node1.log"
echo "  tail -f test_logs/node2.log"
echo "  tail -f test_logs/node3.log"
echo ""
echo "To stop all nodes:"
echo "  kill $NODE1_PID $NODE2_PID $NODE3_PID"
echo ""
echo "Or press Ctrl+C and run:"
echo "  pkill -f unified_node"
echo ""

# Wait for user interrupt
echo "Press Ctrl+C to stop all nodes..."
wait
