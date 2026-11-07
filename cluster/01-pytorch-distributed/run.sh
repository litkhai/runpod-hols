#!/usr/bin/env bash
# Runs inside a Pod or on every node of an Instant Cluster: topology, NCCL sweep, DDP scaling.
# Pod 안에서, 또는 Instant Cluster 의 모든 노드에서 실행: 토폴로지, NCCL 측정, DDP 확장성.
#
#   bash run.sh <tag>        # results land in results/<tag>/
#
# On a cluster, NUM_NODES, NUM_TRAINERS, NODE_RANK, PRIMARY_ADDR and PRIMARY_PORT
# are set by Runpod; on a single Pod they are absent and the script uses 1 node.
# 클러스터에서는 Runpod 이 NUM_NODES 등을 넣어 준다. 단일 Pod 에서는 없으므로 노드 1개로 돈다.
set -euo pipefail
cd "$(dirname "$0")"
TAG=${1:?tag}
OUT=results/$TAG
mkdir -p "$OUT"

NNODES=${NUM_NODES:-1}
NPROC=${NUM_TRAINERS:-$(nvidia-smi -L | wc -l)}
RANK_=${NODE_RANK:-0}
ADDR=${PRIMARY_ADDR:-127.0.0.1}
PORT=${PRIMARY_PORT:-29500}
export NNODES
if [ "$NNODES" -gt 1 ]; then
  # Inter-node traffic must use the cluster interfaces, not eth0 (172.x, internet only).
  # 노드 간 통신은 eth0(172.x, 인터넷용)가 아니라 클러스터 인터페이스를 써야 한다.
  export NCCL_SOCKET_IFNAME=${NCCL_SOCKET_IFNAME:-ens1}
fi
export NCCL_DEBUG=${NCCL_DEBUG:-INFO}
export NCCL_DEBUG_SUBSYS=${NCCL_DEBUG_SUBSYS:-INIT,NET}

R="torchrun --nnodes $NNODES --nproc_per_node $NPROC --node_rank $RANK_ --master_addr $ADDR --master_port $PORT"

{
  echo "## node $RANK_ of $NNODES, $NPROC GPUs"
  nvidia-smi --query-gpu=index,name,memory.total,pcie.link.gen.current,pcie.link.width.current --format=csv
  echo; nvidia-smi topo -m
  echo; ip -brief addr
  echo; env | grep -E '^(NUM_NODES|NUM_TRAINERS|NODE_RANK|NODE_ADDR|PRIMARY_ADDR|PRIMARY_PORT|WORLD_SIZE|HOST_NODE_ADDR)=' | sort || true
} > "$OUT/node$RANK_-topology.txt" 2>&1
cat "$OUT/node$RANK_-topology.txt"

echo "== NCCL all-reduce, $((NNODES * NPROC)) GPUs"
$R nccl_bench.py --out "$OUT/nccl.json" 2> "$OUT/node$RANK_-nccl.log"
grep -E "NCCL INFO (Using network|Channel 00|comm .* nRanks|NET/)" "$OUT/node$RANK_-nccl.log" | sort -u | head -20 || true

echo "== DDP, 1 GPU baseline (node 0 only)"
if [ "$RANK_" = 0 ]; then
  torchrun --standalone --nproc_per_node 1 ddp_train.py --out "$OUT/ddp_1gpu.json" 2>>"$OUT/node$RANK_-ddp.log"
fi
echo "== DDP, $((NNODES * NPROC)) GPUs"
$R ddp_train.py --out "$OUT/ddp_all.json" 2>>"$OUT/node$RANK_-ddp.log"
