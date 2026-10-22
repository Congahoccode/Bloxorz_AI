import glob
import os
import re
import sys
import time

# Đảm bảo đường dẫn thư mục gốc dự án luôn được nhận diện
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

try:
    from solver.ucs import Level, ucs, run_ucs, CostModel, UNIFORM
except ImportError:
    from ucs import Level, ucs, run_ucs, CostModel, UNIFORM

SO_LAN_CHAY = 20    # Số lần chạy để lấy thời gian trung bình


def lay_so_level(duong_dan):
    m = re.search(r"(\d+)", os.path.basename(duong_dan))
    return int(m.group(1)) if m else 9999


def do_thoi_gian(duong_dan, mo_hinh):
    # Thời gian tìm kiếm trung bình 
    level = Level(duong_dan)
    tong = 0.0
    for i in range(SO_LAN_CHAY):
        t0 = time.perf_counter()
        ucs(level, mo_hinh)
        tong = tong + (time.perf_counter() - t0)
    return tong / SO_LAN_CHAY * 1000


def main():
    level_dir = os.path.join(PROJECT_ROOT, "level")
    cac_file = sorted(glob.glob(os.path.join(level_dir, "*.json")), key=lay_so_level)

    print("%-18s | %-8s |  len  cost  expanded  time(ms)  mem(KB) | actions" % ("level", "model"))
    dong_csv = ["level,model,length,cost,expanded,time_ms,peak_mem_kb,actions"]

    for f in cac_file:
        lvl_name = os.path.splitext(os.path.basename(f))[0]
        for ten, mo_hinh in [("weighted", CostModel()), ("uniform", UNIFORM)]:
            ket_qua = run_ucs(f, mo_hinh)     
            if not ket_qua["solved"]:
                print("%-18s | %-8s | Không có lời giải" % (lvl_name, ten))
                continue
            thoi_gian = do_thoi_gian(f, mo_hinh)   

            print("%-18s | %-8s | %4d %5d %9d %9.2f %8.1f | %s" % (
                lvl_name, ten, ket_qua["length"], ket_qua["cost"], ket_qua["expanded"],
                thoi_gian, ket_qua["peak_mem_kb"], ket_qua["actions"]))
            dong_csv.append("%s,%s,%d,%d,%d,%.3f,%.1f,%s" % (
                lvl_name, ten, ket_qua["length"], ket_qua["cost"], ket_qua["expanded"],
                thoi_gian, ket_qua["peak_mem_kb"], ket_qua["actions"]))

    csv_path = os.path.join(PROJECT_ROOT, "ucs_results.csv")
    with open(csv_path, "w", encoding="utf-8") as f:
        f.write("\n".join(dong_csv) + "\n")
    print(f"\nDa luu {csv_path}")


if __name__ == "__main__":
    main()

    main()