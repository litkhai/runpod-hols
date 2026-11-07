#!/usr/bin/env bash
# One method for every storage tier (#69). Runs inside a Pod.
# 모든 스토리지 층을 같은 방법으로 잰다 (#69). Pod 안에서 실행.
#
#   bash bench.sh <label> <dir> [size]      e.g. bash bench.sh network /workspace 2G
#
# fio, direct I/O where the filesystem allows it (FUSE mounts may refuse O_DIRECT,
# then buffered + end_fsync), one job, so tiers compare on the same terms:
#   seq write 1M · seq read 1M (after dropping the file from the page cache) ·
#   rand read 4K and rand write 4K (iodepth 16, 30 s) · 1,000 small files (4 KiB) create+fsync.
# Output: one JSON line per test on stdout, plus the mount line for <dir>.
set -u
LABEL=${1:?label}; DIR=${2:?dir}; SIZE=${3:-2G}
command -v fio >/dev/null || { apt-get update -qq >/dev/null && DEBIAN_FRONTEND=noninteractive apt-get install -y -qq fio >/dev/null; }
F="$DIR/.fio.$LABEL"; mkdir -p "$DIR"
MNT=$(df -T "$DIR" | awk 'NR==2{print $1" "$2" "$3}')
DIRECT=1
fio --name=probe --filename="$F" --size=4M --rw=write --bs=1M --direct=1 --output=/dev/null 2>/dev/null || DIRECT=0
emit() { python3 -c "
import json,sys
d=json.load(open('$1'))['jobs'][0]; rw='$2'
x=d['write' if 'write' in rw else 'read']
print(json.dumps({'label':'$LABEL','dir':'$DIR','mount':'$MNT','direct':$DIRECT,'test':'$3',
  'MiBps':round(x['bw']/1024,1),'iops':round(x['iops']),'clat_p99_ms':round(x.get('clat_ns',{}).get('percentile',{}).get('99.000000',0)/1e6,2)}))"; }
run() { # name rw bs extra...
  local n=$1 rw=$2 bs=$3; shift 3
  fio --name="$n" --filename="$F" --size="$SIZE" --rw="$rw" --bs="$bs" --direct=$DIRECT --ioengine=libaio \
      --numjobs=1 --group_reporting --output-format=json --output=/tmp/fio.$n.json "$@" >/dev/null 2>&1 \
  || fio --name="$n" --filename="$F" --size="$SIZE" --rw="$rw" --bs="$bs" --direct=$DIRECT --ioengine=psync \
      --numjobs=1 --group_reporting --output-format=json --output=/tmp/fio.$n.json "$@" >/dev/null 2>&1
  emit /tmp/fio.$n.json "$rw" "$n"
}
run seq_write write 1M --end_fsync=1
sync; ( echo 3 > /proc/sys/vm/drop_caches ) 2>/dev/null
run seq_read read 1M
run rand_read randread 4k --iodepth=16 --time_based --runtime=30
run rand_write randwrite 4k --iodepth=16 --time_based --runtime=30 --end_fsync=1
D="$DIR/.small.$LABEL"; rm -rf "$D"; mkdir -p "$D"
s=$(date +%s.%N); for i in $(seq 1 1000); do head -c 4096 /dev/zero > "$D/f$i"; done; sync; e=$(date +%s.%N)
python3 -c "print(__import__('json').dumps({'label':'$LABEL','dir':'$DIR','mount':'$MNT','test':'small_files_1000','seconds':round($e-$s,2),'files_per_s':round(1000/($e-$s))}))"
rm -rf "$D" "$F"
