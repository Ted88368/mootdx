# Changelog

## [Unreleased]

## [1.0.3]

### Fixed

- **ETF 复权日期列兼容**: `etf_reversion()` 现在兼容多种日期格式（`year/month/day`、`datetime` 列、DatetimeIndex），不再因为缺失列而报 KeyError。
- **空数据保护**: `etf_reversion()` 和 `_reversion()` 增加空 DataFrame 检查，避免 IndexError。
- **索引恢复**: ETF 复权后索引名统一为 `datetime`。

### Changed

- **复权优先使用 TDX XDXR 本地计算**，Sina 财经因子降级为回退方案。`reversion()` 现在先尝试 `_reversion()`（基于 XDXR 除权除息数据本地计算），失败后再回退到 `factor_reversion()`（Sina 财经因子）。
- XDXR 本地计算同时调整 `volume`、`high_limit`、`low_limit`，数据源完全在 TDX 体系内，不再强依赖外部 Sina 服务。

## [1.0.2]

_待补充发布说明_

## [1.0.1]

_待补充发布说明_

## [1.0.0]

_待补充发布说明_

## [0.11.8]

_待补充发布说明_
