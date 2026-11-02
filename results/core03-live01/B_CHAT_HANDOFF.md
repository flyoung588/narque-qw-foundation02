# QW-LIVE-CORE03-01｜真实执行回执

**本轮未证明新增可运行的 live 双通道物理能力。终态：ENGINE_INTEGRATED_NOT_LIVE_PROVEN / FIRST_JOB_FAILED_BEFORE_PROPAGATION。**

已按用户本次批准发布18个增量文件及清单，提交 `1f7211913e6b51b2aeba5fb5457f8c15e3ca484d`，分支 `qw-live-core03-01`。固定首轮科学输入未改变；数值内核、旧收据、W2/W4/W5及main未修改。原准备包保留。

## 实际运行

- [GitHub Run 41404890543](https://github.com/flyoung588/narque-qw-foundation02/actions/runs/41404890543)，Job 125144578905。
- 首次尝试，failure；2026-11-02 07:13:26—07:14:08 UTC（北京时间15:13:26—15:14:08），42秒。
- 使用公开仓库标准ubuntu-24.04、15分钟Job时限；现有workflow无artifact/cache收费服务，结果走日志。启动前依据GitHub官方计费规则及当前仓库/工作流确认该范围零新增费用，未购买任何资源。
- 仅1次dispatch、1个Job；第二任务没有启动、没有重跑、没有新增外部模型调用。

## 失败断点

原始科学容器日志报：

`world01.contracts.WorldError: COUPLED_MODEL_ARRAY_MISMATCH`

位置为`core03_live/model.py:validate_arrays`：加载的R/Vg/Vu/mu_gu/K之一没有通过与云端从固定曲线重建值的dtype及逐元素严格相等检查。该检查发生在`worker.execute`调用`transition`之前。因此没有完成新TDSE传播、没有产生新末态、没有应用新电场，也没有新的Pg/Pu/功—能量结果可报告。历史恢复的Pu不被当成本轮新结果。

日志未记录失败的具体键或差值。跨平台/依赖版本下的数组重建差异与过严逐位等值是合理怀疑，**尚未证实为根因，也没有证据证明差异只是无害舍入**。本轮没有放宽阈值、改源码重跑或消耗第二任务槽修复首轮。

父状态和派发请求已从本地真实dispatch记录解码，逐文件回读与冻结输入相同；父State仍为`866cf1616101f1c17cc93bbb8ecdd525f760b264b5c201affa266bd4df99ef45`。统一封装数组SHA `802a7e40efe75d1642420619d2975fa2aa6f57b650f8234076542e1f728abace`。原历史checkpoint压缩包与统一封装是不同容器格式；不混称同一NPZ字节。

本地上层最终异常`ORIGINAL_RUN_NOT_VERIFIED_SUCCESS`是共享transport尝试只读回收后拒绝失败Job的结果，不是原始科学错误。这里以容器原始trace为失败归因。没有将失败引擎解释成物理异常。

## 资源与证据限度

冻结源码先检查Docker inspect的1CPU/1GiB/禁网/零额外Swap，Worker又检查实际cgroup后才到达上述断点。执行轨迹支持这些准入检查已通过；但可取得日志未出现`QWLF_PACKAGE`标记，故本轮**没有回收原始cgroup读数文件、环境版本JSON或容器inspect JSON**。不编造峰值内存、CPU用量或完整资源原始读数。实际版本安装及原生启动可从完整Job构建/运行日志查阅，不以“依赖安装成功”作物理资格。

完整官方Run/Jobs元数据、原始日志、请求与输入SHA、Grant、冻结代码、18文件清单、只读费用核查及失败日志均保留。原始日志SHA为`2a3ca3deea9917c914cba7d2e945bebef15cf78ee0e480e0621052625baa4a91`（gh run view文本格式）；不将其冒称原始HTTP日志响应字节SHA。

## 能力变化与处置

本轮已把此前完成的typed双通道状态、历史恢复、场控制合同、持久化/比较/Explorer和Worker增量发布到指定分支，且实际走到新Worker的输入验证。但没有得到新物理演化、控制差异或写盘恢复后续传的live证据，A—E实质验收不能整体通过。既有8项离线检查及历史回放顺序敏感失败继续独立保留，不用其替代本轮结果。

首轮失败后B-Work实际选择STOP；这不是观测到新物理后的科学方向选择，更不是新增外部模型自治试验。W2仍INCOMPLETE；W4/W5、历史Core资格与Canonical不变。

唯一已定位的下一技术问题是：**明确哪一份跨平台重建数组不同、差多少及为何不同，再判断应如何绑定固定Hamiltonian输入。** 本轮未授权修复重跑，因此不自行实施、不追加诊断Job、不提出新的科学结果。原始数组差异没有被当作物理反证。

完成后交B-Chat审议并停止。未消费的第二任务槽不转换成修复或重跑授权。
