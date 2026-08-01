# 多服务器测速与自动切换 设计文档

> 状态: 已实现 · 模块: `mootdx2/server.py` (ServerManager), `mootdx2/quotes.py` (AutoSwitchClient)
> 适用范围: 标准市场 (HQ) 与扩展市场 (EX), 不含财务线路 (GP)

## 1. 背景与目标

通达信行情服务器有数十台分布在全国各地, 延迟和可用性差异大, 且单台服务器随时可能宕机或变慢。客户端需要:

1. **测速**: 从候选服务器中选出最快、最可用的服务器
2. **自动切换**: 服务器不可用时, 不中断服务地切换到下一台

### 目标

- 启动时: 配置的服务器连不上, 自动尝试下一台 (启动期 failover)
- 运行中: 请求连续失败, 自动切换到下一台并重试该请求 (运行期切换)
- 线程安全, 支持 `multithread=True` 场景
- 不改变对外 API 与现有调用方行为

## 2. 现状分析 (改动前)

| 能力 | 状态 | 说明 |
|---|---|---|
| 测速 | ✅ 已有 | `server.py` 的 `server()` 用 asyncio 并发测全部主机, `bestip()` 把最快的写入 `config.json` 的 `BESTIP` |
| 启动 failover | ❌ 没有 | `StdQuotes.__init__` 只连一次 `BESTIP.HQ`, 连不上也不检查返回值, 直接静默失败 |
| 运行期切换 | ❌ 没有 | `reconnect()` 是死代码 (引用未赋值的 `self.bestip`), `check_empty()` 里重连逻辑被注释 |
| 同服务器重试 | ✅ 有 (tdxpy) | `TdxHq_API(auto_retry=True)` 只在同一台服务器上重试 |

## 3. 关键发现: tdxpy 底层行为

这些事实直接决定了设计形态, 实现前必须理解:

1. **`connect()` 失败返回 `False`, 不抛异常** (`raise_exception=False` 时)。原代码没检查返回值 → 死连接上后续请求全部返回 None
2. **所有 `get_*` 请求被 `last_ack_time` 装饰器包裹**:
   - 异常时若 `auto_retry=True`, 会 `disconnect` + `connect` **同一台**服务器重试 (间隔 0.1/0.5/1/2s)
   - `raise_exception=False` (默认) 时最终**吞掉异常, 返回 None**
3. **运行期失败信号是 None, 不是异常**。`[]`/空列表是合法空数据 (如停牌、无 K 线), 与 None 必须区分
4. `connect()` 内的 `setup()` (协议握手) 在 try/except **外面**, TCP 通但协议失败时会抛异常, failover 循环必须兜住

## 4. 总体架构

```
┌───────────────────────────── Quotes (StdQuotes / ExtQuotes) ─────────────────────────────┐
│                                                                                          │
│  __init__                                                                                │
│    ├─ ServerManager(index, candidates, threshold)   ← 有序候选池 + 失败计数 + 游标       │
│    ├─ _connect()            ← 层1: 启动期 failover, 逐个尝试候选直到连上                 │
│    └─ AutoSwitchClient(api, manager)                ← 层2: 运行期请求级切换代理         │
│                                                                                          │
│  业务方法 (bars/quotes/...)                                                              │
│    └─ self.client.get_xxx(...)   → AutoSwitchClient 拦截 → ServerManager 计数/切换      │
└──────────────────────────────────────────────────────────────────────────────────────────┘
```

### 组件职责

| 组件 | 位置 | 职责 |
|---|---|---|
| `ServerManager` | `server.py` | 纯状态机: 候选列表、游标、连续失败计数、线程锁。**不做任何 IO** |
| `AutoSwitchClient` | `quotes.py` | 代理包装 tdxpy API, 拦截请求结果, 驱动 ServerManager, 执行重连 |
| `BaseQuotes._connect` | `quotes.py` | 层1: 启动连接 failover |
| `bestip()` / `server()` | `server.py` | 测速入口, 不变, 写入 `config.json` 供 ServerManager 读取 |

## 5. 详细设计

### 5.1 ServerManager (server.py)

```python
class ServerManager:
    def __init__(self, index='HQ', candidates=None, threshold=3):
        self.index = index
        self.threshold = max(1, int(threshold))
        self.lock = threading.RLock()
        self._candidates = candidates or self._default_candidates(index)
        self._cursor = 0
        self._failures = 0
        self.current = self._candidates[0] if self._candidates else None
```

**候选列表生成** (`_default_candidates`, 静态方法内延迟 import 避免循环依赖):

```
BESTIP[index] (测速结果, 如果有) → 其余按配置 SERVER[index] 顺序 → 去重
```

- `BESTIP` 是 `bestip` 命令/`bestip=True` 测速写入 config.json 的最快服务器, 排首位
- 配置 `SERVER` 列表本身是人工维护的"已知可用"服务器
- 去重防止同一地址重复出现

**核心状态机方法**:

| 方法 | 行为 |
|---|---|
| `current_server()` | 返回 `candidates[cursor % len]`, 游标自动环绕 |
| `mark_connected(addr, port)` | 层1 连成功后同步游标到实际连接的服务器 |
| `report_success()` | 清零 `_failures` |
| `report_failure()` | `_failures += 1`; 达到 `threshold` → 清零 + 游标前进 + 返回 `True`; 否则 `False` |

### 5.2 层1: 启动期 failover (`BaseQuotes._connect`)

```python
def _connect(self):
    for addr, port in manager.candidates:
        try:
            if self.client.connect(addr, int(port), time_out=self.timeout):
                self.server = (addr, int(port))
                manager.mark_connected(addr, port)
                return True
        except Exception:          # TCP 或 setup 协议握手失败
            self.client.disconnect()   # 清理半连接 socket
    return False                    # 全部失败, 记录日志, 不抛异常 (维持旧行为)
```

- **候选顺序即优先级**: BESTIP → 配置列表, 越快/越稳的越靠前
- 全部失败**不抛异常**, 保持旧行为 (请求返回 None), 但运行期层2仍可恢复
- 用户显式传 `server=...` 时候选池只有该服务器, 尊重显式选择

### 5.3 层2: 运行期请求级切换 (AutoSwitchClient)

**代理机制**: `__getattr__` 拦截 `get_*` 方法, 其余属性/方法直通。

```python
_PASSTHROUGH = {'connect', 'disconnect', 'close', 'setup', 'to_df', 'get_traffic_stats'}
```

直通白名单: 控制面方法 (connect/disconnect/close/setup) 与不触网络或不能作为失败信号的方法。

**失败判定**: 只有 `None` 结果或抛异常算失败; `[]` 等空结果算成功 (合法空数据)。

**切换流程** (`_call`):

```
for attempt in range(len(candidates)):        # 最多完整遍历一轮
    result = api.method(*args)                # tdxpy 内部可能已同服务器重试
    if result is not None:
        report_success()                      # 成功 → 清零计数
        return result
    if not report_failure():                  # 失败 → 计数; 未达阈值
        return result                         #   直接返回 None, 计数累积
    _reconnect()                              # 达阈值 → 游标前进 → 断开重连到新服务器
                                              #   → continue 重试本次请求
return result
```

**重连** (`_reconnect`): 取 `current_server()`, `disconnect()` 后 `connect(addr, port, time_out)`, 失败也吞掉——下次 `report_failure` 会继续推进游标, 天然级联切换。

## 6. 关键设计决策与权衡

| 决策 | 选择 | 理由 |
|---|---|---|
| 失败信号 | None/异常, 不含 `[]` | tdxpy 吞异常返回 None; `[]` 是合法空数据, 误判会导致无效切换 |
| 切换阈值 | 3 次连续失败, 成功即清零 | 过滤单次抖动; 合法空数据需连续 3 次无成功才触发, 误伤可控 |
| 层1 永远开启 | `auto_switch=False` 只关层2 | 启动时"配置服务器挂了换个能连的"是纯改进, 不该被关闭 |
| 用户显式 `server=` | 单候选, 不参与 failover | 尊重显式选择 |
| tdxpy `auto_retry` | 保留不动 | 它管同服务器瞬时重试 (0.1/0.5/1/2s), 我们管跨服务器, 各司其职 |
| 层2 封装方式 | 代理对象而非装饰每个方法 | 只改 `__init__`, 不动 20+ 个业务方法, diff 最小 |
| 候选顺序来源 | 配置 BESTIP + SERVER, 非每次全量测速 | 全量测速 ~0.7s, 只应在 `bestip=True` 时执行 |
| `bestip=True` 后配置同步 | 重调 `config.setup()` 重载 | `check_server()` 只写盘不更新内存, 否则读到旧 BESTIP |

## 7. 边界情况

| 场景 | 行为 |
|---|---|
| 全部候选启动时连不上 | 层1 返回 False, 不抛异常; 后续请求层2 会轮询完整候选池, 服务器恢复后自动恢复 |
| 切换后新服务器也挂了 | 失败计数不清零地继续累积, 每次请求推进一个游标, 直到绕回原服务器 |
| 单候选 (用户显式 server) | `max_attempts=1`, 切换环绕回同一台, 行为等同于关闭切换 |
| 心跳 (heartbeat=True) | 切换走 disconnect→connect, 与 tdxpy 自身 auto_retry 同路径, 心跳线程安全 |
| 并发请求 (multithread=True) | ServerManager 内部 RLock 保证计数/游标原子; 切换期间其他请求看到短暂断开, 与旧 auto_retry 一致 |

## 8. 测试策略

`tests/test_server_manager.py`, 10 个用例, 全部**不联网、不写 config.json**:

- 候选排序: BESTIP 优先 + 去重
- 阈值状态机: 3 次失败切换、成功清零、threshold=1 立即切换、mark_connected 同步游标
- 代理行为: 切换后重试成功、成功清零后再次切换、异常计为失败、阈值内失败直接透传

关键技巧: `FakeApi` 模拟 tdxpy (返回预设结果序列 + 记录 connect/disconnect), `patch('mootdx2.config.settings')` 注入配置, 不触发 `config.setup()`。

## 9. 后续演进方向 (未实现)

1. **测速结果 TTL 缓存**: 当前 `bestip=True` 每次构造全量测速 (~0.7s); 可加 24h 缓存 + 服务器列表变更失效
2. **多次采样取中位数**: 单次握手抖动大, 测 2~3 次取 p50, 并发下总耗时≈最慢服务器
3. **评分加权**: 延迟 × 权重 + 连通性惩罚, 防止"最快但总断"的服务器被反复选中
4. **财务线路 (GP)**: 走 HTTP 下载, 机制不同, 当前明确不做
5. **主动健康探测**: 空闲时后台线程周期性 ping 当前服务器, 提前发现劣化而非等请求失败

## 10. 涉及文件

| 文件 | 改动 |
|---|---|
| `mootdx2/server.py` | 新增 `ServerManager` (+83 行); `bestip`/`server`/`check_server` 不变 |
| `mootdx2/quotes.py` | 新增 `AutoSwitchClient`; `BaseQuotes` 增加 `_connect`/`manager`/修复 `reconnect`; `StdQuotes`/`ExtQuotes` 初始化重构 (+135/-28) |
| `tests/test_server_manager.py` | 新增 10 个单元测试 |

顺带修复的存量 bug:
- `reconnect()` 引用未赋值的 `self.bestip`, 调用必崩 → 改为从 manager 取当前服务器
- `ExtQuotes` 默认服务器取 `SERVER.EX[0]` (site, addr, port 三元组) 直接 `connect(*server)` 传错位 → 改为走 manager 候选 (addr, port)
