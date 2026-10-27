import glob
import os
import re
import sys
import time

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from solver.a_star import Level, astar, run_astar
    from solver.ucs import CostModel, UNIFORM
except ImportError:
    from a_star import Level, astar, run_astar
    from ucs import CostModel, UNIFORM

SO_LAN_CHAY = 20


def lay_so_level(duong_dan):
    m = re.search(r"(\d+)", os.path.basename(duong_dan))
    return int(m.group(1)) if m else 9999


def do_thoi_gian(duong_dan, heur_type="bloxorz_admissible", weight=1.0):
    level = Level(duong_dan)
    tong = 0.0
    for _ in range(SO_LAN_CHAY):
        t0 = time.perf_counter()
        astar(level, heur_type=heur_type, weight=weight, cost_model=UNIFORM)
        tong += (time.perf_counter() - t0)
    return (tong / SO_LAN_CHAY) * 1000.0


def main():
    level_dir = os.path.join(PROJECT_ROOT, "level")
    cac_file = sorted(glob.glob(os.path.join(level_dir, "*.json")), key=lay_so_level)

    print("=" * 105)
    print("                      ⚡ BENCHMARK THUẬT TOÁN A* SEARCH TRÊN CÁC LEVEL ⚡")
    print("=" * 105)
    print("%-18s | %-16s |  len  expanded  time(ms)  mem(KB) | actions" % ("Level", "Heuristic/Weight"))
    print("-" * 105)

    configs = [
        ("A* (Admissible)", "bloxorz_admissible", 1.0),
        ("A* (Manhattan)",  "manhattan",           1.0),
        ("Weighted A*(1.5)", "bloxorz_admissible", 1.5),
    ]

    dong_csv = ["level,config,heuristic,weight,length,expanded,time_ms,peak_mem_kb,actions"]

    for f in cac_file:
        lvl_name = os.path.splitext(os.path.basename(f))[0]
        for label, heur, w in configs:
            ket_qua = run_astar(f, heur_type=heur, weight=w, cost_model=UNIFORM)
            if not ket_qua["solved"]:
                print("%-18s | %-16s | Không có lời giải" % (lvl_name, label))
                continue
            thoi_gian = do_thoi_gian(f, heur, w)

            print("%-18s | %-16s | %4d %9d %9.2f %8.1f | %s" % (
                lvl_name, label, ket_qua["length"], ket_qua["expanded"],
                thoi_gian, ket_qua["peak_mem_kb"], ket_qua["actions"]))
            dong_csv.append("%s,%s,%s,%.1f,%d,%d,%.3f,%.1f,%s" % (
                lvl_name, label, heur, w, ket_qua["length"], ket_qua["expanded"],
                thoi_gian, ket_qua["peak_mem_kb"], ket_qua["actions"]))

    csv_path = os.path.join(PROJECT_ROOT, "astar_results.csv")
    with open(csv_path, "w", encoding="utf-8") as out_f:
        out_f.write("\n".join(dong_csv) + "\n")
    print("=" * 105)
    print(f"Đã lưu kết quả vào: {csv_path}")


if __name__ == "__main__":
    main()

