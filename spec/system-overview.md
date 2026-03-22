# System Overview — Generative Morphology & Evolution System

## 0. 系統定位

本系統是一個：

> 無限制形體（Unbounded Morphology）  
> × 遺傳系統（Genetic System）  
> × 語義對應（Semantic Correspondence）  
> 的生成生命架構

目標：
- 生成可演化的形體
- 支援無限拓樸結構
- 保持可重現、可主張（ownership-grade）

---

## 1. 系統分層

### Layer 0 — Genome（基因層）
定義生成規則，而非形體本身

### Layer 1 — Development Engine（發育層）
將 Genome 轉換為 BodyGraph

### Layer 2 — BodyGraph（形體層）
所有形體的統一表示（節點 + 邊）

### Layer 3 — Trait System（特徵層）
定義可遺傳、可變異的特徵

### Layer 4 — Part Correspondence Engine（對應層）
在不同形體之間建立語義對應

### Layer 5 — Evolution Loop（演化層）
負責繁殖、突變、生成下一代

---

## 2. 核心流程


Genome
↓
Development Engine
↓
BodyGraph
↓
Trait Expression
↓
PCE Mapping
↓
Mutation
↓
Next Generation


---

## 3. 設計原則

### 3.1 無限制形體
- 不限制節點數量
- 不限制拓樸結構
- 不依賴固定骨架

### 3.2 語義優先
- 不用「手/腳」名稱
- 使用 semantic tags + role

### 3.3 可重現性
- 所有生成基於 seed
- 所有結果可 hash

### 3.4 AI 作為補完層
AI 僅用於：
- 語義標註
- fallback 生成
- trait 轉譯

---

## 4. 模組依賴關係


Genome → Development → BodyGraph
↓
Trait
↓
PCE
↓
Evolution


---

## 5. 系統目標

- 可演化生命系統
- 可用於遊戲 / 藝術 / 研究
- 可作為生成型 IP 資產
