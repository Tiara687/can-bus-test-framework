# can-bus-test-framework

**基于 Python + pytest 的车载 CAN 总线自动化测试框架**

在没有真实 ECU 和 CAN 硬件的条件下，用虚拟总线搭建出一套可运行的总线测试环境：
自己实现一个车身控制器（BCM）节点周期发送报文，再对其**报文周期、信号取值、丢帧率、UDS 诊断服务**
进行自动化验证。全部 18 条用例均可一键运行。

> 为什么做虚拟总线：它绕开了硬件调试这个最大的时间成本，且结果可复现，
> 同样的用例将来换真实通道（如 candleLight / USB-CAN）即可直接复用。

## 技术栈

| 库 | 用途 |
|---|---|
| python-can | CAN 总线收发、虚拟总线（virtual interface） |
| cantools | 加载 DBC、报文编解码、信号范围校验 |
| udsoncan + can-isotp | UDS 诊断服务与 ISO-TP 传输层 |
| pytest | 测试框架：fixture 资源管理、参数化、异常断言 |

## 快速开始

```bash
pip install -r requirements.txt
pytest                      # 在项目根目录下运行
```

手动观察总线数据可用这两个调试脚本（排障时最有用）：

```bash
python simulator/debug_receive.py   # 打印 BCM 发出的报文与相邻间隔
python simulator/debug_uds.py       # 打印每一次 UDS 请求 / 响应的原始字节
```

## 目录结构

```
can-bus-test-framework/
├── conftest.py              # 共享 fixture：虚拟总线、DBC、BCM 模拟器、UDS 服务端/客户端
├── pytest.ini
├── requirements.txt
├── dbc/
│   └── body_control.dbc     # 自制车身控制器 DBC（车速/电压/车门/灯光，含周期属性）
├── simulator/
│   ├── bcm_simulator.py     # BCM 模拟节点：后台线程按 100ms 周期发报文
│   ├── uds_server.py        # UDS 服务端：手动构造各服务的响应字节
│   ├── debug_receive.py     # 调试脚本：观察总线报文
│   └── debug_uds.py         # 调试脚本：观察 UDS 收发
└── tests/                   # 18 条用例（见下表）
```

## 测试用例清单

| 测试文件 | 用例 | 验证内容 |
|---|---|---|
| `test_body_status.py` | `test_bus_can_deliver_message` | 总线链路：发出 0x100，对端 1 秒内应收到的 ID 一致 |
| | `test_encode_and_decode_speed` | DBC 编解码往返：车速 60.0 编码后解码，值不变 |
| | `test_door_signal_choices`（参数化 2 条） | 枚举信号：`decode_choices=False` 时车门值应为 0/1 而非字符串 |
| `test_signal_decode.py` | `test_decode_vehicle_speed` | 信号链路：车速 60.0 编码上总线后解码回仍为 60.0 |
| `test_cycle_time.py` | `test_body_status_cycle_time` | **周期抖动**：收 10 帧，相邻间隔须落在 90~110ms（100ms ±10%） |
| `test_frame_loss.py` | `test_frame_loss` | **丢帧统计**：2 秒窗内应收 20 帧，实测丢帧率须 ≤ 10% |
| `test_signal_boundary.py` | 有效值 0 / 200 / 400 | 等价类 + 边界值：编码解码往返后值不变 |
| | 无效值 -1 / 401 / 400.1 | 越界必须抛 `EncodeError` |
| | `test_out_of_range_value_leaks_when_strict_disabled` | 反证：关闭严格校验时越界值会泄漏到总线，用一条用例将该风险固化 |
| `test_uds_diagnostic.py` | `test_change_session_should_succeed` | 0x10 会话控制：`10 03` → `50 03 ...` |
| | `test_read_vin_should_return_vin` | 0x22 读 DID：读 0xF190，断言返回的 VIN |
| | `test_read_dtc_should_return_one_fault` | 0x19 读 DTC：解析可用性掩码与故障码、故障状态字节 |
| | `test_unsupported_did_should_be_rejected` | 否定响应：`7F 22 31`（RequestOutOfRange） |

## 测试用例设计方法

用例不是随手写的，按下面这套方法设计：

| 设计方法 | 在本项目中的落地 |
|---|---|
| 等价类划分 | 车速信号：有效等价类取 0 / 200 / 400，无效等价类取 -1 / 401 / 400.1 |
| 边界值分析 | 覆盖区间端点 0 与 400，以及边界外紧邻值 -1 / 400.1 / 401 |
| 参数化（数据驱动） | 用 `@pytest.mark.parametrize` 一次覆盖多组取值，避免复制粘贴用例 |
| 错误推测法 | 针对易错点专项设计：周期抖动、报文丢失、越界值、不支持的服务 |

车载总线特有的测试维度（通用软件测试通常不涉及）：

已覆盖：

- **周期抖动**：报文标称 100ms，实测相邻间隔须落在 90~110ms（±10%）
- **丢帧统计**：固定时间窗内应收与实际收到的报文数对比
- **UDS 诊断**：0x10 会话控制、0x22 读 DID、0x19 读 DTC，以及否定响应验证

未覆盖（列入后续方向）：总线负载率、网络管理休眠唤醒、错误帧 / BusOff 注入。

## 两条工程约定

**1. 每条用例都做过反面验证。** 要证明用例真的在测东西，而不是"永远绿"的空壳——
例如把模拟器周期改成 0.15 秒后周期用例必须变红，改回 0.1 才恢复。
（过程中确实抓到过两类假通过：函数未加 `test_` 前缀被 pytest 静默跳过；encode 少传信号导致因"缺信号"而非"越界"报错。）

**2. `encode()` 统一显式传 `strict=True`。** cantools 在 `strict=False` 时不校验 DBC 中定义的信号范围，
车速 401 会被直接编码发到总线。该风险已由 `test_out_of_range_value_leaks_when_strict_disabled` 固化，
防止有人误关这个开关。

## 已知边界（后续可扩展方向）

- 未覆盖：BusOff / 错误帧注入、网络管理休眠唤醒、CAN FD、LIN 总线
- 日志分析方向：曾尝试扩展 candump / ASC 日志解析工具，因工期取舍暂未并入本仓库
- 当前运行在虚拟总线上，未接入真实收发器（如 CANable + candleLight）
