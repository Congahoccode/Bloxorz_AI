import glob
import os
import re
import time

from model.ucs import Level, ucs, run_ucs, CostModel, UNIFORM

SO_LAN_CHAY = 20    # Số lần chạy để lấy thời gian trung bình


def lay_so_level(duong_dan):
    return int(re.search(r"(\d+)\.json", duong_dan).group(1))


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
    cac_file = sorted(glob.glob(os.path.join("level", "*.json")), key=lay_so_level)

    print("level | mo_hinh  |  len  cost  expanded  time(ms)  mem(KB) | actions")
    dong_csv = ["level,model,length,cost,expanded,time_ms,peak_mem_kb,actions"]

    for f in cac_file:
        so = lay_so_level(f)
        for ten, mo_hinh in [("weighted", CostModel()), ("uniform", UNIFORM)]:
            ket_qua = run_ucs(f, mo_hinh)     
            if not ket_qua["solved"]:
                print(so, ten, "Không có lời giải")
                continue
            thoi_gian = do_thoi_gian(f, mo_hinh)   

            print("%5d | %-8s | %4d %5d %9d %9.2f %8.1f | %s" % (
                so, ten, ket_qua["length"], ket_qua["cost"], ket_qua["expanded"],
                thoi_gian, ket_qua["peak_mem_kb"], ket_qua["actions"]))
            dong_csv.append("%d,%s,%d,%d,%d,%.3f,%.1f,%s" % (
                so, ten, ket_qua["length"], ket_qua["cost"], ket_qua["expanded"],
                thoi_gian, ket_qua["peak_mem_kb"], ket_qua["actions"]))

    f = open("ucs_results.csv", "w", encoding="utf-8")
    f.write("\n".join(dong_csv) + "\n")
    f.close()
    print("\nDa luu ucs_results.csv")


if __name__ == "__main__":
    main()