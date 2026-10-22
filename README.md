# NARQUE Quantum World — QW-PERIODIC-02 v0.1.0

**状态：IMPLEMENTED + LOCAL SOFTWARE TESTED；NO NEW PHYSICAL CALCULATION.**

## 一、继承基线与严格边界

基线仓库 `flyoung588/narque-qw-foundation02`，分支 `qw-periodic01r`，本次只读核实的基线 HEAD `b0d8d8109b229cf0291120301772b1ab16503aa2`。已验收的周期执行为 [39622273751](https://github.com/flyoung588/narque-qw-foundation02/actions/runs/39622273751)，已证实的 P1/P2 只对应受限 FCC Ne / Γ 点 RKS/PBE/cc-pVDZ/GDF 能量。W1、W3、Core01–03 均继承而不修改；W2（独立引擎验证）仍未完成。

总锚点：`NARQUE Quantum Physical World — Master Target & World Architecture v0.1.0` / `NARQUE_Quantum_Physical_World_Architecture_Manifest_v0.1.0_STAGE.json`。核心目标是 AI 自主物理探索，不能把局部计算器、验证或资源分配流程当作世界本身。

**这次新增的是真实可执行的软件能力，不是新材料科学结果：**

- 通用 Bravais 晶胞及分数坐标基底构造器（FCC、BCC、简单立方），**无材料专用求解分支**；
- B-Chat AI 在本轮构造了两种物理类型不同的候选：两原子金刚石型 C 晶胞，及两原子岩盐型 MgO 晶胞。详细的计算前理由、预测和反证见 `decisions/PREOBSERVATION_FROZEN.json`；
- 继承原有 WorldSpec 的受限域，按物质类型路由到 `PySCF` 分子或 `PySCF-PBC` 周期计算。ASE 是构造工具；**二者同属 PySCF 代码家族，不能声称 W2 通过**；
- 物理合法性和代价预检拒绝不支持的自旋、元素、k 网格、观测和实验模式；代价仅按规模粗筛，**不是内存／时间实际估计，也不是科研价值排名**；
- 事前选择冻结、原始观测哈希绑定的事后反馈决策接口；二次实验只在取得真实观测后才可生成；
- 物理结果语义检查、不同组成的绝对能量比较禁止、精度未认证状态保留；
- 独立求解器 `science_worker.py` 对接既有 `recovery02r.isolated_router` 和 `qw_next.periodic_world`；本地只使用明确标记为 synthetic 的替身进行子进程接口检查。

## 二、候选（不是科学发现）

| 候选 | 周期结构 | 组成 | 每原胞电子数 | 初始几何最近邻（有限镜像预检） | 当前状态 |
|---|---|---|---:|---:|---|
| `QW_P02_C_DIAMOND_2ATOM` | FCC 原胞 + 2 点金刚石型基底；常规立方 a=3.57 Å | 2C | 12 | ~1.546 Å | **AI_PRECOMPUTE_FROZEN / NOT_RUN** |
| `QW_P02_MGO_ROCKSALT_2ATOM` | FCC 原胞 + 2 点岩盐型基底；常规立方 a=4.21 Å | MgO | 20 | ~2.105 Å | **AI_PRECOMPUTE_FROZEN / NOT_RUN** |

二者是人工授权工作流中由本轮 AI 明确提出的 *计算前对象*；**不是容器内部能自主调用模型的 unattended Agent**。数值晶格参数是建议初始结构，不是本轮测得的平衡晶格常数。有限镜像距离检查仅作早期筛查，真实计算必须由 ASE 周期距离和原有 `validate_cell` 复核。不同材料不可用直接相减的总能量进行排名。

## 三、在本地运行的内容

本增量包离线准备只需要 Python 标准库：

```bash
PYTHONPATH=. python -m unittest discover -s tests -v
PYTHONPATH=. python -m periodic02.cli admit decisions/WorldSpec_QW_P02_C_DIAMOND_2ATOM.json
PYTHONPATH=. python -m periodic02.cli admit decisions/WorldSpec_QW_P02_MGO_ROCKSALT_2ATOM.json
```

首次事前冻结已实际执行，记录位于 `decisions/PREOBSERVATION_FROZEN.json`。`freeze_json` 使用排它创建；不得覆盖已有冻结版本。注意：**重复 prepare 命令写同一目标路径会被拒绝（预期行为）**。

在已有真实周期输出后，可通过 `periodic02.quality.quality_from_observation()` 检查其记录语义；`periodic_energy_comparison()` 只允许同组成、同数值方法和同能量零点的结果进入模型内部比较。它们不是独立物理精度认证。

## 四、接入真实仓库与执行端

这是仅含新增 `periodic02/` 等文件的 **overlay**，不是旧仓库的完整替换版。应用到基线分支后，`periodic02.science_worker` 会在独立子进程里懒加载：

- `qw_next.periodic_world.route_world` （周期真实 PySCF-PBC）；
- `foundation01.runner.run_world` （非周期已有 PySCF）；
- `recovery02r.isolated_router.run_isolated`（故障隔离／原始回执）。

本地 Python 环境**没有 ASE 或 PySCF**，没有运行电子结构计算，也没有声称验证上述运行时链接在云端当前状态的兼容性。真实科学运行仍需要原来的隔离 Linux cgroup（1 CPU/单线程、1GiB、0 swap、科学容器无网络），并执行 PySCF-PBC 自己的资源预检。

`periodic02.run_once.execute_once()` 是一层额外的**未授权拒绝与只运行一次保护**，只有新的真实批准范围绑定后才允许实际调用；这个代码条件本身并不能替代人的 GitHub 权限授权。**本次未创建远程分支、未推送、未触发 Actions**。

## 五、独立的科学资格，不提前升级

| 项目 | 当前本轮状态 |
|---|---|
| 计算前 AI 构造两个不同周期物质候选 | **DONE / FROZEN** |
| 通用晶胞生成及能力路由 | **IMPLEMENTED / LOCAL TESTED** |
| 故障隔离子进程接口（替身） | **SYNTHETIC SOFTWARE TEST ONLY** |
| 两个新候选真实 ASE/PySCF-PBC 计算 | **NOT STARTED** |
| 材料力、应力、声子等 | **NOT IMPLEMENTED** |
| k 点、积分网格、基组独立敏感度验证 | **NOT TESTED** |
| 基于周期材料真实观测的下一次 AI 自适应实验 | **NOT STARTED** |
| W2 独立引擎互证 | **INCOMPLETE** |
| 新材料稳定性、原始新物理、M1 应用结果 | **NOT PROVEN** |

后续应优先允许**一个**新增周期物质通过通用结构接口作有限资源实跑；只有真实观测返回后，才应决定是否设计后续探索。另一个候选仅是有不同物理类型的候选备份，不构成已授权的第二个计算任务。

## 六、原始证据

- `decisions/AI_PRECOMPUTE_CHOICES.json`：AI 选择理由与反证；
- `decisions/PREOBSERVATION_FROZEN.json`：已冻结的实际物质构造、WorldSpec SHA、适用域、成本风险标签；
- `evidence/LOCAL_SOFTWARE_TESTS.txt`：离线测试运行原始输出；
- `evidence/LOCAL_RECEIPT.json`：工程状态及其物理 claim ceiling；
- `evidence/SHA256_MANIFEST.json`：增量包原始文件哈希；
- `evidence/PROPOSED_EXTERNAL_SCOPE.json`：**尚未授予**的未来单 Job 范围提案。

旧原始证据与所有科学裁决都保持不变，未修改 XREM Canonical，也没有假设另一套程序已经具备独立量子精度认证能力。
