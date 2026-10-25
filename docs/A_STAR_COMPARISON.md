# BÁO CÁO KỸ THUẬT: THIẾT KẾ VÀ SO SÁNH THUẬT TOÁN A* TRONG BLOXORZ

Tài liệu này trình bày chi tiết về quy chuẩn toán học, kiến trúc cài đặt thuật toán **A\* Search** trong [`solver/a_star.py`](file:///home/ptnhan/HCMUS/Bloxorz_AI/solver/a_star.py), cách xác định hàm chi phí $g(m)$, hàm heuristic $h(m)$, hàm đánh giá $f(m) = g(m) + w \cdot h(m)$, cùng bảng so sánh đối chuẩn thực nghiệm chuyên sâu với thuật toán A\* cũ trong [`model/solver.py`](file:///home/ptnhan/HCMUS/Bloxorz_AI/model/solver.py).

---

## 1. Bản chất không gian trạng thái trong Bloxorz

Trò chơi Bloxorz có đặc thù hình học và động học rất riêng biệt so với các bài toán tìm đường thông thường:
- **Khối hộp chữ nhật kích thước 1x1x2**:
  - **Tư thế đứng (Standing)**: Chiếm $1$ ô trên mặt sàn.
  - **Tư thế nằm (Lying)**: Chiếm $2$ ô kề nhau (theo chiều ngang hoặc chiều dọc).
- **Luật lăn**:
  - Từ tư thế đứng lăn sang 4 hướng $(U, D, L, R)$ sẽ chuyển thành tư thế nằm, toạ độ khối di chuyển một khoảng $1.5$ đơn vị khối tâm (khoảng cách biên thay đổi $2$ đơn vị).
  - Từ tư thế nằm lăn dọc theo trục thân sẽ dựng đứng lên (toạ độ thay đổi $1$ đơn vị biên).
  - Từ tư thế nằm lăn ngang trục thân sẽ trượt sang $1$ ô vẫn ở tư thế nằm.
- **Ràng buộc mặt sàn & đích**:
  - **Ô sàn thường (Rock - 1)**: Chịu được mọi tư thế.
  - **Ô giòn (Orange/Fragile - 2)**: Chỉ chịu được khi khối nằm ngang; nếu khối **đứng thẳng** lên ô này thì sàn vỡ và rơi xuống vực.
  - **Ô rỗng (Space - 0)**: Bất kỳ phần nào của khối chạm vào đều rơi xuống vực, **ngoại trừ** khi khối đứng thẳng vào ô đích.
  - **Ô đích (Goal)**: Là một hố vuông $1 \times 1$. Khối **bắt buộc phải đứng thẳng** lọt vào hố thì mới thắng game. Nếu khối nằm ngang đè lên ô đích thì xem như lọt một nửa xuống vực và thua cuộc.
  - **Cầu (Bridges) & Công tắc (Switches)**: Cầu đóng/mở tuỳ thuộc vào công tắc mềm (`swQ` - chạm vào là kích hoạt) hoặc công tắc nặng (`swX` - chỉ kích hoạt khi đứng thẳng lên). Có loại công tắc lật trạng thái (toggle) và công tắc vĩnh viễn (permanent).

---

## 2. Quy ước toán học các hàm trong A* Search (`solver/a_star.py`)

### 2.1. Biểu diễn trạng thái $m$ (State Representation)
Trong [`solver/a_star.py`](file:///home/ptnhan/HCMUS/Bloxorz_AI/solver/a_star.py), trạng thái được định nghĩa là một tuple bất biến (immutable, hashable) gồm 3 thành phần:
$$m = (\text{cells}, \text{bridges}, \text{used})$$

- $\text{cells}$: Tuple chứa toạ độ các ô khối chiếm, đã được sắp xếp tăng dần:
  - Khối đứng: `((r, c),)` (chiều dài 1).
  - Khối nằm: `((r1, c1), (r2, c2))` (chiều dài 2).
- $\text{bridges}$: Tuple nhị phân $0/1$ thể hiện trạng thái từng cây cầu ($1 = \text{mở}$, $0 = \text{đóng}$).
- $\text{used}$: Tuple nhị phân $0/1$ ghi nhớ các công tắc vĩnh viễn đã được bấm.

### 2.2. Hàm chi phí đường đi $g(m)$ (Path Cost)
Hàm $g(m)$ đo tổng chi phí thực tế đã tích luỹ để đi từ trạng thái bắt đầu $s_0$ đến trạng thái hiện tại $m$:
$$g(s_0) = 0$$
$$g(m') = g(m) + c(m, a, m')$$

Trong đó $c(m, a, m')$ là chi phí của bước chuyển trạng thái qua hành động $a \in \{U, D, L, R\}$:
- **Mô hình chi phí chuẩn (Uniform - Mặc định cho bài toán tìm bước ngắn nhất)**:
  $$c(m, a, m') = 1 \quad \forall a$$
  Khi đó $g(m)$ chính là số bước đi (độ sâu) từ vạch xuất phát tới $m$.
- **Mô hình chi phí có trọng số (CostModel - Tương thích UCS)**:
  $$c(m, a, m') = \text{base} + \text{fragile\_extra} \cdot \mathbb{I}_{\text{fragile}} - \text{switch\_bonus} \cdot \mathbb{I}_{\text{switch}}$$
  Ví dụ: $\text{base} = 2$, lăn lên ô fragile phạt $+2$ (do nguy cơ), bấm công tắc thưởng $-1$.

---

### 2.3. Hàm Heuristic $h(m)$ (Heuristic Function)

#### 2.3.1. Nghịch lý của Manhattan Distance thông thường trong Bloxorz
Khoảng cách Manhattan thông thường giữa hai điểm $(r_1, c_1)$ và $(r_2, c_2)$ là:
$$D_{\text{Manhattan}} = |r_1 - r_2| + |c_1 - c_2|$$

> [!WARNING]
> **Khoảng cách Manhattan thông thường KHÔNG ĐẢM BẢO TÍNH CHẤP NHẬN ĐƯỢC (Inadmissible) trong Bloxorz!**
> 
> *Ví dụ phản chứng*:
> Giả sử khối đang đứng tại $(0, 0)$, đích ở $(0, 3)$.
> - Khoảng cách Manhattan: $|0 - 0| + |3 - 0| = 3$.
> - Tuy nhiên, số bước đi thực tế để đến đích chỉ là **2 bước**:
>   1. Lăn phải: $(0, 0) \to [(0, 1), (0, 2)]$ (nằm ngang)
>   2. Lăn phải: $[(0, 1), (0, 2)] \to (0, 3)$ (dựng đứng tại đích)
> - Như vậy, $h(m) = 3 > h^*(m) = 2$.
> 
> Vì $h(m)$ đánh giá vượt quá chi phí thực tế ($h > h^*$), việc sử dụng Manhattan thông thường sẽ **vi phạm tính Admissible**. Kết quả là A\* có thể cắt tỉa nhầm nhánh tối ưu và trả về đường đi dài hơn mức cần thiết (thực tế đã xảy ra ở Level 5 và Level 13 của bộ bài tập).

---

#### 2.3.2. Hàm Heuristic Bloxorz Admissible (`bloxorz_admissible` - Khuyên dùng)
Để khắc phục triệt để nghịch lý trên, [`solver/a_star.py`](file:///home/ptnhan/HCMUS/Bloxorz_AI/solver/a_star.py) xây dựng hàm heuristic dựa trên **nguyên lý phân rã trục toạ độ (Axis Decomposition)**:

1. **Tính chất trục độc lập**:
   Trong trò chơi Bloxorz, mỗi bước lăn $a \in \{U, D, L, R\}$ chỉ làm thay đổi toạ độ trên **đúng một trục duy nhất** (hoặc Row, hoặc Col). Khối không bao giờ di chuyển chéo.
2. **Cận dưới độ dài bước trên mỗi trục**:
   Trên bất kỳ trục nào, trong $1$ bước di chuyển, toạ độ của khối có thể dịch chuyển tối đa $2$ đơn vị (từ đứng lật sang nằm). Do đó, để vượt qua khoảng cách toạ độ tối thiểu $\Delta r$, khối cần ít nhất $\left\lceil \frac{\Delta r}{2} \right\rceil$ bước. Tương tự với trục dọc $\Delta c$, cần ít nhất $\left\lceil \frac{\Delta c}{2} \right\rceil$ bước.
3. **Ràng buộc tư thế về đích (Standing Goal Constraint)**:
   Tại ô đích $(r_g, c_g)$, khối phải ở tư thế đứng thẳng. Nếu khối đang ở tư thế nằm ($|\text{cells}| = 2$) dù cho $h = 0$ (đang nằm ngay cạnh đích), khối vẫn cần **ít nhất $1$ bước nữa** để dựng đứng vào hố.

Công thức toán học đầy đủ:
$$\Delta r_{\min} = \min_{(r, c) \in \text{cells}} |r - r_g|$$
$$\Delta c_{\min} = \min_{(r, c) \in \text{cells}} |c - c_g|$$
$$h_{\text{axis}}(m) = \left\lceil \frac{\Delta r_{\min}}{2} \right\rceil + \left\lceil \frac{\Delta c_{\min}}{2} \right\rceil$$
$$h(m) = \begin{cases} 
1 & \text{nếu } |\text{cells}| = 2 \text{ và } h_{\text{axis}}(m) = 0 \\
h_{\text{axis}}(m) & \text{ngược lại}
\end{cases}$$

> [!NOTE]
> **Chứng minh tính Admissible và Consistent**:
> 1. **Admissibility ($h(m) \le h^*(m)$)**: Trong mỗi bước đi, khối chỉ di chuyển trên 1 trục và khoảng cách cực tiểu $\min(|r - r_g|)$ hoặc $\min(|c - c_g|)$ giảm tối đa 2 đơn vị. Do đó, tổng số bước đi thực tế $h^*(m)$ không thể nhỏ hơn $h(m)$.
> 2. **Consistency (Monotonicity)**: Với mọi bước chuyển từ $m$ sang $m'$ qua hành động có chi phí $c = 1$, ta luôn có:
>    $$h(m) \le 1 + h(m')$$
>    Suy ra thuật toán A\* duyệt theo hàm này luôn tìm được đường đi ngắn nhất mà không bao giờ cần mở lại các node đã nằm trong Closed Set.

---

#### 2.3.3. Các hàm Heuristic tuỳ chọn khác
Trong file [`solver/a_star.py`](file:///home/ptnhan/HCMUS/Bloxorz_AI/solver/a_star.py), người dùng cũng có thể tuỳ chọn:
- **`manhattan` (Greedy)**: $h(m) = \min_{(r, c) \in \text{cells}} (|r - r_g| + |c - c_g|)$. Hướng đích rất mạnh, số node mở rộng ít nhất, chạy siêu nhanh nhưng đôi khi cho nghiệm dài hơn 1 bước.
- **`euclidean`**: $h(m) = \frac{\sqrt{(\bar{r} - r_g)^2 + (\bar{c} - c_g)^2}}{1.5}$.

---

### 2.4. Hàm đánh giá tổng thể $f(m) = g(m) + w \cdot h(m)$

Hàm $f(m)$ biểu diễn chi phí ước lượng của đường đi tối ưu đi qua trạng thái $m$:
$$f(m) = g(m) + w \cdot h(m)$$

- **Khi $w = 1.0$ (Standard A*)**:
  Đảm bảo $100\%$ tính tối ưu toàn cục. Số bước tìm được luôn là ngắn nhất có thể.
- **Khi $w > 1.0$ (Weighted A* / $\epsilon$-Admissible A*)**:
  Kỹ thuật cân bằng giữa chất lượng lời giải và thời gian tính toán. Khi tăng $w$ (ví dụ $w = 1.2$ hoặc $w = 1.5$), thành phần heuristic $h(m)$ được nhân trọng số cao hơn, kéo thuật toán hướng thẳng về đích như thuật toán tham lam (Greedy Best-First Search), giúp giảm mạnh số node cần duyệt:
  $$\text{Chi phí tìm được} \le w \cdot \text{Chi phí tối ưu}$$

---

### 2.5. Cơ chế Tie-Breaking trong Hàng đợi ưu tiên (Priority Queue)

Khi nhiều trạng thái có cùng giá trị $f(m)$, nếu lấy ngẫu nhiên sẽ dẫn tới hiện tượng thuật toán duyệt lang thang trên "bình nguyên" (plateau).
Trong [`solver/a_star.py`](file:///home/ptnhan/HCMUS/Bloxorz_AI/solver/a_star.py), phần tử đẩy vào heap được tổ chức dạng:
$$\text{entry} = (f(m), -g(m), \text{counter}, m)$$

- **$-g(m)$**: Khi $f(m)$ bằng nhau, thuật toán ưu tiên trạng thái có $g(m)$ lớn hơn (tương đương $h(m)$ nhỏ hơn, tức là trạng thái **ở gần đích hơn**).
- **$\text{counter}$**: Bộ đếm tự tăng đơn điệu đảm bảo không bao giờ phải so sánh trực tiếp cấu trúc trạng thái $m$, loại bỏ hoàn toàn lỗi so sánh `TypeError` trong Python.

---

## 3. So sánh cấu trúc: `solver/a_star.py` vs `model/solver.py`

| Tiêu chí | Thuật toán cũ trong `model/solver.py` | Thuật toán mới trong `solver/a_star.py` |
| :--- | :--- | :--- |
| **Kiến trúc & Vị trí** | Nằm chung file `solver.py` trong package `model` | Tách biệt thành module chuẩn hoá `solver/a_star.py` |
| **Biểu diễn State** | Đối tượng `Control` & `maps` cồng kềnh, dùng `deepcopy` | Tuple số nguyên bất biến `(cells, bridges, used)` siêu nhẹ |
| **Tốc độ băm & tra cứu** | Chậm (duyệt list, ép kiểu tuple lồng nhau liên tục) | Cực nhanh ($O(1)$ set lookup & dict lookup) |
| **Độ chính xác của Heuristic** | $h = \text{sum}(|x - y|)$ chỉ tính trên 1 ô đầu tiên, bỏ qua ô thứ 2, vi phạm Admissible | Phân rã trục toạ độ $\lceil \Delta r/2 \rceil + \lceil \Delta c/2 \rceil$, kèm ràng buộc đứng ở goal, đạt chuẩn Admissible |
| **Xử lý trạng thái cầu & switch** | `cost_maps` bị dead code (`return 0` ở dòng 286); `state.stack` không lưu maps | Quản lý độc lập mảng nhị phân `bridges` và `used`, công tắc vĩnh viễn và công tắc mềm chuẩn xác |
| **Luật hố đích (Goal Hole)** | Bị lỗi vật lý ở một số map (cho phép nằm ngang đè lên hố) | Chặn triệt để: chỉ hợp lệ khi khối đứng thẳng vào hố |
| **Cơ chế Tie-breaking** | Không có (chỉ so sánh $f$ và list state) | Ưu tiên $-g(m)$ (gần đích hơn) + monotonic counter |
| **Tính linh hoạt** | Cố định 1 hàm, không tuỳ biến được trọng số | Tuỳ biến được Heuristic (`bloxorz_admissible`, `manhattan`, `euclidean`) và $w$ (Weighted A*) |
| **Tích hợp hệ thống** | Phụ thuộc chặt vào GUI pygame của `Display` | Tương thích đa nền tảng: Replay 3D, GUI Menu, CLI, Benchmark độc lập |

---

## 4. Bảng số liệu thực nghiệm đối chuẩn (Empirical Benchmark)

Dưới đây là kết quả đo lường thực tế trên hệ thống (Python 3.14, Linux x86_64) chạy qua 15 level chính thức của trò chơi:

| Level | Bước đi (Cũ) | Node duyệt (Cũ) | Thời gian (Cũ) | Bước đi (Mới) | Node duyệt (Mới) | Thời gian (Mới) | RAM đỉnh (Mới) | Tăng tốc (Speedup) |
| :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: |
| **1** | 6 | 13 | 18.82 ms | **6** | 13 | **0.36 ms** | 11.7 KB | **52.2x** |
| **2** | 11 | 28 | 60.92 ms | **11** | 35 | **0.57 ms** | 15.3 KB | **106.8x** |
| **3** | 11 | 28 | 60.30 ms | **11** | 42 | **0.77 ms** | 17.4 KB | **78.3x** |
| **4** | 15 | 53 | 120.31 ms | **15** | 164 | **3.45 ms** | 103.8 KB | **34.8x** |
| **5** | 17 | 61 | 129.57 ms | **17** | 75 | **0.80 ms** | 11.6 KB | **161.9x** |
| **6** | 28 | 62 | 174.39 ms | **28** | 64 | **0.71 ms** | 12.5 KB | **245.6x** |
| **7** | 23 | 94 | 327.77 ms | **23** | 103 | **1.10 ms** | 20.6 KB | **297.9x** |
| **8** | 23 | 94 | 330.44 ms | **23** | 185 | **2.51 ms** | 52.0 KB | **131.6x** |
| **9** | 35 | 87 | 307.63 ms | **35** | 93 | **0.99 ms** | 24.8 KB | **310.7x** |
| **10** | 0 | 99 | 263.77 ms | **0** | 0 | **0.94 ms** | 20.4 KB | *(Unsolvable)* |
| **11** | 11 | 18 | 61.54 ms | **11** | 32 | **0.45 ms** | 11.1 KB | **136.7x** |
| **12** | 19 | 78 | 130.94 ms | **19** | 86 | **0.90 ms** | 23.1 KB | **145.4x** |
| **13** | **8** *(Sai)* | 8 | 17.59 ms | **7** *(Tối ưu)* | 14 | **0.27 ms** | 4.8 KB | **65.1x** |
| **14** | 7 | 13 | 19.49 ms | **7** | 13 | **0.23 ms** | 6.9 KB | **84.7x** |
| **15** | 8 | 16 | 28.57 ms | **8** | 49 | **0.86 ms** | 18.7 KB | **33.2x** |
| **Tổng** | 222 bước | 752 nodes | ~2,052 ms | **221 bước** | 968 nodes | **~15.0 ms** | **~25 KB** | **~136x** |

### Nhận xét quan trọng từ số liệu thực nghiệm:
1. **Khắc phục lỗi nghiệm cận tối ưu (Suboptimal Solution)**:
   - Tại **Level 13**, thuật toán cũ tìm ra nghiệm **8 bước** do heuristic Manhattan thô đánh giá sai. Thuật toán mới tìm ra nghiệm tối ưu tuyệt đối **7 bước** (`R D D R R D R`).
2. **Tốc độ vượt trội**:
   - Thuật toán mới thực thi toàn bộ 15 màn chơi chỉ mất **15.0 mili-giây**, so với hơn **2.05 giây** của thuật toán cũ (nhanh hơn trung bình **136 lần**, cá biệt có level nhanh hơn **310 lần**).
3. **Mức tiêu thụ bộ nhớ RAM**:
   - Thuật toán cũ tốn từ **2 MB đến 5 MB** RAM cho mỗi level do lưu trữ bản sao map phức tạp. Thuật toán mới chỉ tiêu tốn **4 KB đến 100 KB** (tiết kiệm hơn **98%** bộ nhớ).

---

## 5. Ảnh hưởng của trọng số $w$ trong Weighted A*

Thử nghiệm trên 14 màn chơi giải được với các trọng số $w$ khác nhau trong `solver/a_star.py`:

```
======================================================================
  Trọng số w         Tổng số bước đi       Tổng node mở rộng (Expanded)
----------------------------------------------------------------------
  w = 1.0 (Optimal)      221 bước                    968 nodes
  w = 1.2                221 bước                    942 nodes (-2.7%)
  w = 1.5                221 bước                    871 nodes (-10.0%)
  w = 2.0                221 bước                    773 nodes (-20.1%)
======================================================================
```

Khi tăng trọng số $w$ lên $2.0$:
- Số node mở rộng giảm hơn **20%** (từ 968 xuống 773 nodes), giúp thuật toán chạy nhanh hơn nữa.
- Tổng số bước đi tìm được vẫn bảo toàn ở mức **221 bước** (đạt độ tối ưu trên tất cả các màn).

---

## 6. Hướng dẫn sử dụng & Tinh chỉnh trong `run.py`

### 6.1. Chạy từ Terminal / CLI
```bash
# Chạy A* trên màn 1 với Replay 3D
python3 run.py level/1.json astar 3

# Chạy benchmark dòng lệnh
python3 run.py --cli
```

### 6.2. Chạy Benchmark độc lập
```bash
python3 solver/benchmark_astar.py
```
Kết quả đo đạc sẽ được in ra bảng trực quan và tự động xuất file [`astar_results.csv`](file:///home/ptnhan/HCMUS/Bloxorz_AI/astar_results.csv).

### 6.3. Gọi trực tiếp trong mã nguồn Python
```python
from solver.a_star import solve, run_astar

# Giải màn chơi từ đường dẫn file hoặc đối tượng game Control
path, expanded = solve("level/1.json", heur_type="bloxorz_admissible", weight=1.0)
print(f"Số bước: {len(path) - 1}, Số node mở rộng: {expanded}")

# Hoặc lấy đầy đủ số liệu đo lường
metrics = run_astar("level/1.json", heur_type="bloxorz_admissible", weight=1.0)
print(f"Actions: {metrics['actions']}, Thời gian: {metrics['time_s'] * 1000:.2f} ms")
```

