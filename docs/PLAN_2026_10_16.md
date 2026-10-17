# FoodPath · EGPR: Evidence-Grounded Plan Revision

## 完整版实验计划｜FoodPath｜10 天执行窗口

> **状态：研究计划，尚未实现 EGPR 算法，尚未运行本计划实验。**
> 编写日期：2026-10-16。执行窗口按 2026-10-17 至 2026-10-26 安排；这是项目工作计划，不是已核实的会议截止日期。
> 本仓库计划实现**完整版 EGPR**，不是简化版，也不改做 Uncertainty-Conditioned Plan Recovery（UCPR）。
> 当前主线是既有 `shiiiikw/foodpath-mas-uq` 仓库内的完整版 EGPR；不新建仓库。实验计划不是已实现算法或已完成实验的声明。


<!-- EGPR_ROUTE:2026-10-16:v2 -->
## 当前研究决策：用完整版 EGPR 替换旧 FoodPath 路线

用户已明确选择在**原仓库 `shiiiikw/foodpath-mas-uq`** 内推进完整版 EGPR。FoodPath 继续作为食物援助应用系统和主要验证场景；此前 estimator-only 探索、泛化的 clarification/conditional-response 路线和 UCPR **不再是当前研究任务**。不创建 `egpr-foodpath` 新仓库，不自动切换新方向。

当前执行依据依次为 [研究指令](docs/egpr/RESEARCH_DIRECTIVE.md)、本 README 和 [实验配置](configs/egpr/experiment_plan.yaml)。旧实验、负结果和来源记录保留，不能包装成 EGPR 结果。切换前的活动说明由迁移工具逐文件备份至 `archive/pre-egpr/<旧提交>/`。

**当前状态仍为计划阶段。** 新方法的实现状态须在原仓库中核验；本次只迁移研究方向与计划，不运行付费调用、不宣称发现新 gap。旧 `paper/food-assistant-proposal/main.tex`、`main.pdf` 及其源码 ZIP 保留为历史 proposal，不再代表 EGPR 当前方案。

**一句话研究目标：** 在正常、完整的 LLM 多智能体服务规划系统中，利用带来源的约束状态、可检查的信息价值界限和增量方案更新，减少不必要的反事实规划计算；检验能否在不降低证据支持的完整方案质量、不增加用户未解决判断事项的前提下，优于强 Full-Plan VOI + Checker + Dependency Cache。

**核心证伪标准：** 如果强 VOI + 检查器 + 依赖缓存能够解释全部收益，或建立界限的成本抵消了节省的计算，就不主张 EGPR 具有独立方法优势。规范的系统与评估贡献仍可保留；不据此保证会议录用或评分。

---

## 1. 范围、当前资产与明确不做的事情

### 1.1 完整版必须包含的五个模块

| 模块 | 必须实现的能力 | 必须记录的证据 |
|---|---|---|
| M1：Evidence-grounded plan state | 完整候选方案、跨服务约束、来源、条件状态、belief 与证据义务 | 结构化状态、抽取失败、来源和约束版本 |
| M2：Decision-critical screening | 使用有明确假设的界限排除不可能优于当前候选行动的信息获取；不能证明时不剪枝 | 每次证书、适用范围、错误剪枝审计 |
| M3：Incremental plan revision | 用户或工具返回信息后，更新受影响的方案、失效的证书和缓存 | 更新集合、失效集合、与完整重算的一致性 |
| M4：Budgeted information acquisition | 在 Ask、Verify、Search/Revise 与不同终止输出之间分配有限推理和交互预算 | 候选行动、反事实结果、估计收益、实际开销 |
| M5：Full MAS integration | Planner、Reviewer、Coordinator 及原有必要工具；保留检查、修订、恢复与完整上下文 | 每个角色的输入输出、最终检查回退、全轨迹 |

三值状态、VOI、依赖图、优势剪枝、缓存、角色分工和条件答案均**不单独作为创新**。待验证贡献是这些组件在所定义任务与预算下是否形成可归因的额外能力。

### 1.2 可继承的资产：先核对，再使用

以下内容来自既有 FoodPath 项目对话中的 Round25–28 记录，**生成本替换文件时没有读取原私有仓库，也没有重新验证这些文件或数值**：

| 历史资产或状态 | 继承信息 | Day 1 必须核对 |
|---|---|---|
| 原项目 | `shiiiikw/foodpath-mas-uq` | 仓库可访问性、commit、许可证与可复用代码 |
| 主案例池 | 59 个食物相关生成案例，按共享资源归为 45 组；其中 44 个包含多项服务需求 | 文件哈希、分组、实际需求覆盖与候选完整方案 |
| 原始来源 | HoosierHelp / Indiana211 相关静态目录与任务生成器 | 具体版本、源字段、授权、原文与简化标签冲突 |
| 现有 MAS | Planner–Reviewer–Coordinator 与工具、检查、恢复流程 | 接口是否仍可用，检查器是否实际阻止无依据提交 |
| 已知编码问题 | 旧工具曾把 `none`、`unknown`、空列表合并为空过滤条件 | 独立用户状态与三值适配器，不把修复本身当贡献 |
| 原试运行 | 部分初始运行因最终检查未强制回退而失去比较效力 | 保留并标记，不混入新实验 |
| API 状态 | 历史出现额度耗尽，恢复状态未知 | 本地合法访问与新运行预算；不自动探测或重试 |
| 历史预算 | 记录曾报告原 $20 上限、$4.237484 保守占用 | 仅用于对账，不视为本仓库的新授权或可直接沿用余额 |

主案例池并不自动具备 EGPR 所需的共享条件、多候选完整方案或有效效用标签。**59 个案例不是 59 个独立样本，45 个资源组也只是暂定统计分组，不是现实人群样本。**

### 1.3 保留 FoodPath 的需求侧和供给侧

保留 nutrition QA、food knowledge QA、食物服务检索、个人获取规划、机构供给信息与规划接口。不转去开发网站，不删除已有系统能力来制造性能差异。

第一阶段只对来源实际支持的约束评分。营养数据库不能当作 pantry 实时库存；服务目录不能证明今天仍有食物或某人必然符合资格；没有数量与容量标签就不评价动态分配收益。供给侧功能保留，但其未被数据支持的动态效果不写成实验结论。

### 1.4 十天内不引入的工作

不训练新的 uncertainty estimator，不新增人类或领域数据采集，不重新训练所有基线，不为追求显著性扩充同源合成案例，不临时切换到 UCPR，不把真实生活中的食物获得或健康收益当作离线终点。现有公开数据的重新整理与有明确标注的受控算法实例可以使用，但必须与原始任务结果分开。

---

## 2. 研究问题、假设与审稿意见对应

| RQ / 假设 | 可检验的问题 | 主要比较或反例 | 对应审稿问题 |
|---|---|---|---|
| RQ1 / H1：计算效率 | 相同任务、belief、候选方案和证据下，筛选是否减少完整反事实评估及端到端成本？ | EGPR vs Full-Plan VOI + Dependency Cache | 是否只是 VOI 或缓存 |
| RQ2 / H2：决策保留 | 被剪掉的行动是否仍可能是最佳行动，或是满足最终证据义务所必需的行动？ | 小规模精确枚举、同状态反事实审计 | 证书是否真正有效 |
| RQ3 / H3：增量更新 | 新证据后的状态是否等价于同一规则下完整重算，是否产生实际净节省？ | EGPR vs screening-only；普通依赖缓存对照 | 是否只是常规增量计算 |
| RQ4 / H4：端到端价值 | 相同推理和交互预算下，能否维持或提高证据支持的完整方案完成率？ | 完整 MAS 与强结构化 VOI | 是否只在理想图上有效 |
| RQ5 / H5：适用边界 | 方案数、共享条件、相关性和抽取误差如何影响收益与失效？ | 预设分层及所有失败 | 是否只在挑选的简单案例上成立 |

**主张边界：** EGPR 不是更优的决策理论，不要求也不声称击败相同模型、目标与资源条件下的精确最优策略。研究对象是有限计算预算下的可实现策略。普通缓存足够、界限过松、结构成本过高、候选图错误或无可靠优势，都是允许出现的结果。

---

## 3. 方法规格：状态、效用、证书和更新

### 3.1 状态与证据义务

令：

$$
S_t=(h_t,\mathcal P_t,\mathcal E_t,\mathcal C_t,b_t,\mathcal D_t,v_t,B_t).
$$

- $h_t$：完整公开对话及工具历史；$\mathcal P_t$：候选完整方案。
- $\mathcal E_t$：带来源、时间或快照、作用范围的证据；$\mathcal C_t$：条件及组合约束。
- $b_t$：与公开信息一致的共同 belief；$\mathcal D_t$：数据和概率依赖关系。
- $v_t$：来源、状态、候选方案、效用及 belief 的版本；$B_t$：剩余预算向量。

每个条件使用 `supported / refuted / unknown`；冲突是额外的 `conflict` 标记，不能靠平均置信度消除。未知不是否定，否定也不等于检索过滤器的空值。

区分三层：**现实条件是否成立、当前系统是否有证据支持、是否允许无条件交付方案**。隐藏任务真值可供评分器判定事实正确性，但不得传给 planner、工具代理、belief 更新器或证书计算器。没有公开证据而“猜对”不算 supported completion。

最小数据契约如下；这些是待实现的接口，不是已存在的软件类：

```text
Condition: condition_id, subject_scope, predicate, value_domain,
           evidence_status, conflict, supporting_evidence_ids,
           refuting_evidence_ids, source_dependencies, version
Evidence:  evidence_id, source_id, source_version, source_span,
           retrieved_at, valid_time_scope, subject_scope, observed_value
Plan:      plan_id, components, covered_needs, hard_constraints,
           cross_component_constraints, unresolved_obligations,
           utility_spec_version, candidate_pool_version
Query:     query_id, type, field_ids, observation_domain,
           observation_model_id, estimated_cost, required_source_scope
Certificate: query_id, lower_bound, upper_bound, comparator,
             assumptions, dependency_versions, proof_mode, expiry_rule
```

硬约束至少包括数据支持的资格、地点、时间、需求覆盖、交通衔接与用户限制。组合方案必须检查跨资源关系；分别找到服务和公交并不等于时间上能够衔接。

### 3.2 决策目标：约束合格优先，成本单独报告

对公开历史 $h$，定义合法终止输出集合 $\mathcal A_{\mathrm{term}}(h)$。其中包含有证据支持的完整推荐、明确保留条件的答案、以及无法解决的终止；只有第一类计入 supported completion。

$$
V(h)=\max_{a\in\mathcal A_{\mathrm{term}}(h)}
\mathbb E_{z\sim b_h}[U(a,z;h)].
$$

一阶信息价值比较为：

$$
Q(q\mid h)=\mathbb E_{o\sim p(o\mid q,h)}[V(h\oplus(q,o))]-V(h)-C(q).
$$

这是既有 VOI 的任务实例化，不是新公式。无可支持完整方案时，终止输出仍可为 conditional / unresolved；不得为了生成成功率而放宽证据要求。

主评估不依赖一个随意加权的“大一统效用分数”：先报告完整方案满足情况，再报告询问信息项、轮次、留给用户的条件及推理成本。策略内部需要的效用、用户信息项成本与工具成本必须在开发集冻结，并做预设敏感性分析；这些参数是建模假设，不是真实用户负担的测量。

**重要反例：** 所有可能世界中“最佳方案 ID 相同”，不代表无需再查证。如果该方案仍缺必要证据，查询可能改变合法交付资格。筛选必须考虑证据义务，不能只比较方案排名。

### 3.3 共同 uncertainty / belief 提供器

所有 VOI 系列方法共享相同的候选状态分布、观测模型和更新规则。在受控环境使用已知联合分布；在 FoodPath 上仅从公开信息、允许的开发数据或共同模型形成估计。不能用隐藏标签构建更准确的 EGPR belief。

用户作答和工具响应不能被假定必然提供完美信息：观测域允许具体取值、`unresolved`、来源冲突和普通工具错误。无可信概率时使用区间或保守可达集合；不捏造精确概率。条件相关时不能仅凭直接依赖索引剪枝：查询一个条件可能通过相关性改变另一条件的 belief。

Uncertainty 的作用通过固定 belief 的策略比较，以及预设的共同 belief 敏感性实验区分。**无需新的 estimator，也不把“必须有新 estimator”设为项目门槛。**

### 3.4 Decision-critical screening：只剪掉能够证明的行动

对每个信息获取行动 $q$ 构造有效界限：

$$L_t(q)\le Q(q\mid h_t)\le U_t(q).$$

将直接终止视为可比较行动，净信息收益为 0。存在另一行动 $r$ 时，只在

$$U_t(q)<L_t(r)$$

成立且证书所有前提有效时，排除 $q$。相等情况保留；主正确性模式不使用人为放宽的 epsilon。近似容差实验必须独立标记。

**第一版可实施方案：** 使用有限观测分支及共享约束图的区间传播，界定每个后继公开状态的终止效用；已精确计算的分支保留精确值，未展开分支使用保守范围，再按已知概率或概率可行集计算 $L/U$。在界限重叠时按共同规则增加展开或进行与基线相同的反事实评估。不能省略生成证书所需的 solver、LLM 或 token 成本。

| 证书模式 | 允许的结论 | 处理规则 |
|---|---|---|
| `exact_modeled` | 在固定候选、正确模型、完整状态域与所定义一阶目标内的判定 | 枚举或可信规则/求解器；保存 witness 与版本 |
| `statistical` | 指定假设和误差概率下的统计判定 | 预设置信方法、重复筛选校正与累计错误风险；单独报告 |
| `heuristic` | 仅为启发式排序，无正确性保证 | 不计入 certified pruning；默认不启用硬剪枝 |
| `unavailable` | 无有效界限 | 保留行动并回退到普通 VOI |

LLM 自报 confidence、自由生成的效用区间或未核验的条件抽取，均不能直接充当严格证书。结构不可靠时必须扩大界限或禁用该处证书。

**序贯边界：** 一步 VOI 为零不意味着多步信息组合无用。相关或互补问题可能只有联合查询才有价值。一阶证书只适用于所声明的一阶目标；不能宣传为不遗漏最优多轮策略。受控层必须加入互补查询反例与小规模多步 oracle。

**动态候选边界：** 主机制实验在固定候选池上比较；端到端允许所有方法搜索和生成新方案。候选池扩张、更改偏好、来源快照变化、效用定义变化或新证据到达时，所有相关证书重新失效检查。不会把“当前检索集合中最优”写成全局最优。

### 3.5 Incremental plan revision：增量计算不得变成过期缓存

维护双层依赖：数据依赖（来源→条件→方案→行动价值）与 belief 依赖（可能相关的条件及观测模型）。新证据只在依赖完整且版本一致时局部传播；无法确定影响范围时完整重算。

缓存键至少包含 `source_snapshot + subject_scope + condition_version + belief_version + candidate_pool_version + utility_version`。同一家庭的烹饪条件可跨方案复用，但不同领取人的资格不能只因字段同名就合并。

每次更新必须返回：受影响条件、受影响方案、失效证书、复用条目、重算条目、未解决条件。关键单元测试要求：在相同确定性规则、相同证据与候选池下，增量结果等于完整重算结果。

对随机 LLM 输出不要求逐字等价；已保存模型响应仅可按模型快照、完整消息、工具定义、生成参数等构成的**完整请求哈希**复用。不能把语义上“差不多”的旧回答当作新调用的等价结果。

### 3.6 Budgeted controller 与完整 MAS

行动空间统一为 `ASK_USER / VERIFY_SOURCE / SEARCH_OR_REVISE / RECOMMEND_SUPPORTED / RESPOND_CONDITIONALLY / REPORT_UNRESOLVED`。搜索不是免费动作，方案构造和反事实评估也计入预算。终止前使用所有方法共享的最终检查器；无依据的提交返回明确原因，允许继续检查、询问或修订。

保留原有 Planner–Reviewer–Coordinator 拓扑。Nutrition、Resource、Mobility 等能力可以通过现有专家或工具提供；不为“完整版”机械增加六个常驻 agent。所有核心对照拥有相同角色、上下文、工具与恢复机会。单 agent 实验是额外架构诊断，不用于取代这些强 MAS 对照。

```text
repeat within the shared budget:
    observe public user/tool evidence; keep the full necessary history
    update the common belief and versioned constraint/plan state
    invalidate affected certificates and caches
    generate the same class of candidate queries and plan alternatives
    build conservative action-value bounds where justified
    retain every action whose dominance is not certified
    spend remaining counterfactual-evaluation budget on retained actions
    choose ask / verify / search-revise / an admissible terminal response
    apply the common checker; return rejected commitments for revision
    log all work, including failed calls, graph repair and final output
```

预算耗尽时输出已知信息和未解决条件，不假装完成。任何上下文压缩必须是各组共同、可审计的规则，不能只让基线丢失必要信息。

---

## 4. 数据资格、拆分与防泄漏

### 4.1 Day 1 先做一次有限的资格检查

对既有 59 个案例及所有可检索候选，输出 `data_manifest`、`qualification_report` 与来源到任务的依赖记录。检查：

1. 是否存在至少两个在初始信息下尚未被排除的**完整**方案，而非两个孤立资源。
2. 是否有会影响候选竞争或证据义务的未知条件，以及真实存在的条件共享。
3. 替代方案的资格、服务覆盖与跨资源约束是否有数据支撑；能否接受多个正确方案。
4. 用户可回答事实和外部可查证事实是否分开；任何答案是否来自既有字段而非临时编造。
5. 原文和生成标签冲突时，能否按预设口径评分；不能解决的项记录为不支持该终点。

保留全部合格的原始任务作为系统评估；将“多方案 + 共享条件”标记为预设机制子集，而不是看完结果后剔除不利任务。子集小也要报告，不用复制同源资源增加独立样本数。

数据资格门槛是判断**现有数据是否能识别机制**，不是发明新 gap 的必要条件。不合格意味着当前终点无法评价，不意味着方法一定无效。

### 4.2 分组和拆分

沿用并复核资源共享图；同一资源、同一服务机构的重复记录或同源文档可产生依赖。将可导致重复信息泄漏的任务连通后再拆分，必要时合并历史的 45 组；记录合并规则和实际有效组数。

建议比例为 20% development / 80% test。若复核后仍为 45 组，则为 9 / 36 组；这只是按当前资产计算的预期数量。固定排序与 seed=13，整组分配，保留组内全部案例，不按模型表现挑选代表案例。

开发集用于结构适配、提示词、共同参数与成本预估。测试集划分后保持隐藏；数据处理人员可做不依赖模型效果的资格检查，但测试结果不能用来修复候选策略。必要修复同时应用全部对照、另开版本并说明其探索性。

### 4.3 模拟用户和外部信息

用户适配器只披露任务中存在的被问信息；未存储的信息返回 `unresolved`。重复询问保持一致，不随机制造“用户不耐烦”。一次问题包含三个字段，按三个 information items 计费。需要新的人类作答或不在数据中的食物数量时，不伪造标签。

工具返回来源快照及原文跨度。真实时效不足的信息保持 unknown；主对比使用固定来源快照，防止运行顺序导致资源变化。主实验不加入人为低级工具错误。噪声与相关性仅用于独立的受控鲁棒性实验。

### 4.4 补充公开数据的界限

ConditionalQA 可辅助测试答案与适用条件；InSCIt 可辅助检查多种合法回应；它们不能直接证明澄清的因果收益或真实用户负担。[R6–R7]

Ask-before-Plan 是预先指定的跨领域扩展候选。[R5] 只在其现有环境、标签与许可证通过适配检查时执行固定子集；不开展无目的数据集搜集。不把该扩展列为 FoodPath 主机制成立的替代证据。

---

## 5. 分层实验：完整方法，分阶段识别贡献

### E0：零模型调用的正确性与集成测试

必须先通过以下测试，才允许运行模型 pilot：

| 测试组 | 必须覆盖的反例或不变量 |
|---|---|
| 状态语义 | unknown≠refuted；空列表不代表否定；同字段不同主体不混合 |
| 最终检查 | 猜中资源但缺证据不能提交；检查失败必须回退；完整支持时能通过 |
| 信息隔离 | 工具只使用公开状态；模型看不到 target resource、隐藏真值、未来回答 |
| 证书正确性 | 界限覆盖精确 Q；平局不误删；无可信区间不剪枝 |
| 证据义务 | 方案 ID 不变但需要查证才能交付时不能错误停止 |
| 相关/组合信息 | 间接 belief 更新；互补查询；一阶与多步最优的差异明确 |
| 动态失效 | 新候选、来源冲突、偏好变化后旧证书不能复用 |
| 增量一致性 | 同一确定性状态下等于完整重算；依赖不明时回退 |
| 账本与恢复 | 全请求哈希、重复请求复用、失败/中断记录、预算与恢复检查 |

这里的反例是算法单元测试，不是给主 MAS 人为注入错误来证明“现实失败”。

### E1：受控离线机制实验

使用独立标记的结构化约束实例，检验算法性质与规模边界，不声称代表真实人群。

- 候选完整方案数：8、32、128。
- 未知条件数：4、8、12。
- 方案条件共享比例：0、0.25、0.50、0.75。
- 5 个固定生成 seeds：13、37、73、101、137。
- 全交叉为 180 个结构实例；分别评估相关条件、冲突和 unresolved 观测的预设附加测试，不与主表混成现实样本。

状态不超过 $2^{12}$ 时可以枚举二值世界；若变量域扩大，报告实际状态数。仅在更小的子集（未知条件≤8、可询问字段≤8、信息 horizon≤3）计算多步最优策略。设置求解器上限，超时单独报告；不能称未解实例的启发式值为 oracle。

比较精确一阶 VOI、精确小规模多步策略、普通结构化 branch-and-bound、VOI + 依赖缓存、screening-only 与完整 EGPR。记录：行动 regret、错误筛选数、bound coverage、状态展开数、重算数、CPU 时间与内存；不是只报告 pruning ratio。

### E2：同状态决策回放（隔离策略与轨迹差异）

从预先固定的公共采集策略产生公开状态银行；采集和结构构建成本独立披露。状态银行只含当时公开证据、共同候选池与共同 belief，不含未来信息。

对完全相同的状态运行各策略，比较选择、界限、反事实评估次数和成本；在可枚举子集审计被剪掉的查询。所有方法拿到相同的结构表示，因此只能归因于筛选/更新策略，不能归因于 EGPR 多看了信息。

回放不等于在线交互收益：实际策略会到达不同状态。该实验仅用于机制识别，E3 才评价完整轨迹。

### E3：完整 FoodPath MAS 主实验

在冻结的全部测试任务上运行各组，允许自行生成、检查、修订和搜索替代方案；不锁死为一个预选目标资源。

- 共享环境、用户适配器、快照、角色、模型、原始上下文和公共检查器。
- 所有结构构建、修复和最终回答成本都计入；不能给 EGPR 免费预计算图。
- 每个比较单位为相同任务 × 相同 seed × 相同模型 × 相同预算；组内运行顺序随机化。
- 主预算建议 100,000 个总模型输入+输出 tokens，敏感性预算 50,000 / 200,000；是执行配置草案，不是当前价格或经 pilot 证明足够的值。
- 用户信息项上限 8、用户轮次上限 8、外部行动上限 16；信息项敏感性 4 / 12。各上限与终止输出预留在 Day 3 对所有方法统一冻结。
- 相同 token 总量不等于相同价格或延迟；分别报告 prompt/output/reasoning/cached tokens、实际美元成本和 wall time。

不足以覆盖正常三角色循环的预算必须在开发集阶段共同修正。不得在主测试后为 EGPR 单独提高预算或缩短基线上下文。

### E4：机制消融、计算收益边界与架构诊断

完成第 7 节 2×2 消融。分层报告候选数、条件共享、初始 unknown 数、belief 相关性和结构抽取质量。错误条件抽取与界限失效来自自然模型输出或单独标记的受控测试，不与主任务混用。

增加 single-agent + 相同工具/检查/上下文的架构诊断。其目的是判断 MAS 的额外作用，不强求它必然较差，也不删除其自检和恢复能力。

### E5：第二模型与跨领域验证

完整版目标包含两个可用的模型快照。优先沿用现有项目可访问的模型，不为了本计划购买新服务；在运行前冻结精确 model ID、参数、上下文窗口和本地/托管方式。

第二模型先覆盖完整 EGPR 与最强 B2，再覆盖其余主对照。额外的 Ask-before-Plan 扩展使用预先哈希选择的最多 30 个独立来源组、固定一个模型、三个预定方法（B2、B3、EGPR）。如果数据不能形成有效映射或成本预算不足，标记未执行，不临时更换容易取得正结果的领域。

---

## 6. 强基线与实现公平性

| ID | 方法 | 具体实现与必须保留的能力 | 地位 |
|---|---|---|---|
| B0 | Full-context Adaptive MAS | 完整角色、公开证据、检索/检查/修订/条件输出，由 LLM 自行决策 | 主对照 |
| B1 | Full-Plan VOI + Checker | 相同候选、belief、合法输出与收益；对候选查询进行全量或同预算 MC 后继方案评估 | 主对照及 2×2 基点 |
| B2 | Full-Plan VOI + Checker + Dependency Cache | B1 加准确的依赖失效、未变条件/方案/请求复用；允许正常重新规划 | **最关键主对照** |
| B3 | Structured VOI / generic branch-and-bound | 使用同一约束表示、常规分支定界或结构化 VOI；同样预算与合法终止条件 | 方法新颖性强对照 |
| B4 | Parameter-level EVPI / SAGE-style | 复用公开方法的问题价值与冗余建模；接同一 MAS 后端及世界核查能力 | 相关方法对照 |
| P | Full EGPR | M1–M5 全部实现，保守证书、增量更新及回退 | 候选方法 |
| D0 | Single-agent + same tools | 同等信息、工具、检查、修订能力；不是删减功能的基线 | 架构诊断 |
| O1/OH | Exact one-step / small-horizon oracle | 只在可精确计算的受控任务上运行 | 参照，不作为必须击败对象 |

B3 不能只写一个名字。Day 2 必须把实际算法、搜索顺序、停止条件和结构适配写进配置及来源审计；GPS 的 DAG 澄清与 B3 的具体实现不自动等价。重用作者代码时固定 commit；改写任务后标为 `adaptation`，没有复现原设置就不能写 `reproduction`。

REVOIR 已包含完整计划收益评估及增量 belief 更新相关设计；不能把“完整方案”或“incremental”说成与其天然不同。[R2] B1/B2 应据其公开方法及通用 VOI 原则核对，而非人为做一个弱版本。

如果 EGPR 的筛选与 B3 在相同状态下数学上等价，直接报告等价；不通过换名或弱化 B3 制造算法差异。若 B4 无法忠实适配，保留适配说明与未完成状态，不假冒 SAGE 官方成绩。

**全部方法的共用项：** 数据、来源快照、用户回答、完整上下文、候选生成能力、belief 提供器、工具、最终检查、条件输出、失败恢复、模型快照、预算和日志。共同能力不因“消融”而移除。

---

## 7. 消融与归因

### 7.1 必做 2×2：固定其他所有信息和工具

| 版本 | Certified screening | Incremental revision | 对应配置 |
|---|---:|---:|---|
| Neither | 否 | 否 | B1 |
| Revision only | 否 | 是 | B2 |
| Screening only | 是 | 否 | A1 |
| Full EGPR | 是 | 是 | P |

报告 P−B2（筛选的增量贡献）、P−A1（增量修订的贡献）以及交互项：

$$I=(Y_P-Y_{B2})-(Y_{A1}-Y_{B1}).$$

对成功率和成本分别计算，不根据交互项显著与否挑选故事。B2 是正确的依赖缓存，不是故意不失效的缓存。

### 7.2 补充诊断，不替代 2×2

| 诊断 | 操作 | 能支持的结论 |
|---|---|---|
| 证书来源 | exact-modeled / statistical / heuristic 分开 | 是否把启发式误写成保证 |
| Uncertainty 提供器 | 所有方法共同改用预设先验/估计器，受控层再用 oracle belief | 收益来自估计还是策略 |
| 结构信息 | 同状态回放 vs 自由构图端到端 | 结构构造的效果与成本 |
| 依赖相关性 | 相同建模条件下比较独立与已知相关情形 | 不完整依赖的风险 |
| 问题价值尺度 | MC 分支数预设 4 / 8 / 16 | 增加采样是否足以获得相同效果 |
| 条件输出 | 所有组同样允许，统计剩余判断事项 | 少问是否只是把任务交回用户 |

不通过禁用最终检查、删除世界工具或阻止 baseline 修订来做有利消融。

---

## 8. 实验矩阵、规模与预算

### 8.1 优先完成的矩阵

主实验设测试案例数为 $N$（实际值由整组拆分确定），六个主方法 B0–B4、P，两个模型、两个环境 seeds（13、37）、一个主预算，总计：

$$N\times6\times2\times2=24N\ \text{个完整工作流。}$$

若实际有 40 个测试案例，则为 960 个工作流；40 只是算例，不是已经确认的数据规模。模型随机 seed 不一定被 API 严格实现；记录服务支持情况，不把重复运行当作新的独立任务。

补充运行：A1 在主模型两个 seeds 上覆盖全部 $N$；B2/P 的两个附加预算在主模型上做配对敏感性；D0 在主模型上做架构诊断；E5 跨领域另列。重合配置可复用完全相同的已有运行，不能重复付费后当作独立证据。

十天内优先级：**E0 → E1 → E2 → E3 的 B2/P 与 2×2 → 其余主对照 → 第二模型 → 跨领域**。这是执行顺序，不是根据结果选择保留方法。最终缺少任何关键对照都要明确标注，不把未完成矩阵称为完整实证。

### 8.2 执行预算与账本

配置默认 `allow_paid_calls: false`、`max_new_paid_usd: 0`。本次要求授权更新既有仓库中的研究方向和实验计划，**不触发模型调用，也不新建仓库**。实际运行必须在本地明确可用的总预算与访问方式，更新配置并记录恢复/启动决定。

通过开发集 pilot 估计每个方法的输入、输出、反事实调用及最终输出成本：

$$\widehat{\mathrm{USD}}=\sum_j(n_{j,in}p_{in}+n_{j,out}p_{out}+c_{j,tools}),$$

其中价格由执行当天的官方资料或账单记录，不能沿用历史价格。预算预估加统一余量；超预算前停止配对队列，不偷偷增加上限。历史已花费、当前实付、预留中断成本与正常运行估价分开列示。

保留 `logical_uncached_cost` 与 `actual_billed_cost`：复用旧响应节约了实际账单，但不能把重复实验前缀免费复用当成算法本身更省钱。所有建图、证书、验证器、修复、重试、角色调度与最终回答均计入端到端账本。

额度不足/权限失败立即停止，不循环重试。普通瞬时故障采用所有组相同的有界重试规则。已经完成的成功请求只在完整哈希一致时复用。

---

## 9. 评价指标及精确定义

### 9.1 主质量终点

`Supported Plan Success (SPS)`：最终输出覆盖全部被评价的用户需求，满足所有可评价的硬/组合约束，关键条件有系统当时可见的来源支持，无未解决的必要证据义务，并通过共用最终检查。

只覆盖部分需求、附带未解决必要条件、猜对隐藏目标但无证据、或超预算未完成，SPS 均为 0。无可行方案任务单独报告 `correct unresolved / abstention`，不靠大量拒答提高“成功率”。不要求命中唯一 target resource；所有满足相同判据的替代完整方案均应接受。

若一个约束没有标签，不以 LLM 判断代替真值。明确列出该任务可评价范围；“来源支持的约束成功”不等于现实领取成功。

### 9.2 成本与交互

| 指标 | 定义与解释 |
|---|---|
| Total requested items | 每次实际请求的原子信息项总数，重复询问也计入 |
| Distinct requested items | 不同主体/范围下的独立信息项数量 |
| User rounds | 用户实际需要回应的轮次；多字段一次问也只是一轮 |
| External checks | 实际外部查询、来源读取和验证次数 |
| Unresolved obligations | 终止输出仍交给用户判断的必要事项，按主体去重 |
| Conditional branches / output length | 条件分支数、输出 tokens/字符数，防止用长 if-clause 规避问句计数 |
| Counterfactual evaluations | 实际展开的观测分支、完整方案评估与模型调用数 |
| End-to-end cost | 建图、抽取、证书、重算、工具、所有模型和最终输出的总成本 |
| Latency / memory | 同硬件与并发条件下的延迟和内存；不从 token 数推断 |

不把这些代理指标线性相加后声称测得真实“认知负担”。`cost per successful task` 仅可补充报告，成功数为零时标记 undefined；主成本统计包含失败，不能只看两种方法都成功的幸存者子集。

### 9.3 正确性和失效诊断

记录 false-pruning rate、错误剪枝导致的行动 regret、界限覆盖、fallback rate、增量/完整重算分歧、结构抽取错误、缓存失效错误、无依据提交尝试及检查器退回。

共用强制 guard 正常工作时，各方法“最终交付的无依据推荐”可能都为零；这是共用环境提供的保障，不能作为 EGPR 独有优势。比较检查前的无依据尝试、修订成本和最终 SPS。

受控层记录逐状态最优差距；端到端层不能在没有完整 oracle 时宣称最终方案全局最优。

---

## 10. 统计协议与继续/停止标准

### 10.1 配对与聚类

首先对同一任务的模型/seed/预算配置做配对；每个模型单独报告主结果。先对组内案例与重复求平均，再在独立来源组之间等权汇总；案例加权结果作为补充。两个模型和重复 seed 不能扩充独立样本量。

使用 10,000 次来源组级 paired bootstrap 给出 95% 区间，报告每个组的原始差值。二值结果可补充适合该分组设计的配对置换分析。开发集不混入最终置信区间。

在接口已通过验证且任务确实执行后，预算耗尽、普通运行失败和模型错误保留在 intention-to-run 主表；外部额度耗尽导致未启动的工作流列为未测量，不能记作模型失败。没有凑齐成对队列时不发布完整配对比较。

### 10.2 预设主比较

主比较为 **P vs B2，主模型、主 token 预算与用户信息项上限**。关键新颖性比较为 P vs B3。其余比较为辅助结果；多重检验用预设的 Holm 校正或以区间和效应量为主，不挑选有利的模型/seed/预算。

工作计划中的实用成功目标如下，必须在 Day 3 主测试前冻结：

- SPS 非劣效界值为 −0.03（3 个百分点）；需要差值区间下界高于该界值，不能用“差异不显著”代替非劣效证据。
- 主模型端到端未缓存等价成本的组均值比 $\mathrm{Cost}_P/\mathrm{Cost}_{B2}$ 目标≤0.80，且成本比区间支持真实节省。
- 用户未解决义务和请求信息项不得仅靠条件文本转移而恶化；完整报告效应量和区间。
- exact-modeled 模式不允许出现未解释的错误证书；发现错误先修复共用版本并重新冻结，不保留错误保证的宣传。

20% 成本目标和 3pp 非劣界是**预设工程目标，不是已验证效果或统计功效保证**。当前独立组数可能无法排除 3pp 损失；区间过宽就报告 inconclusive。规划阶段做最小可检出效果/功效敏感性分析，不通过反复生成同源案例解决独立样本不足。

### 10.3 明确允许的结论

| 观察 | 可以写什么 | 不可以写什么 |
|---|---|---|
| P 与 B2 等价或收益全由缓存解释 | 常规复用足够；EGPR 额外机制未得到支持 | 已证明新算法优势 |
| 离线正确、端到端无净节省 | 理想结构中可行，但抽取/维护成本抵消收益 | 完整 MAS 更高效 |
| SPS 区间过宽 | 对质量保留的证据不足 | 质量不下降 |
| P 只在少数高共享结构有效 | 明确报告适用范围和 break-even 区域 | 一般性优于 VOI |
| P 稳定优于 B2/B3，消融成立 | 有限预算下具有可归因的实证优势 | 打败最优 VOI 或保证 ACL Main |
| 数据或接口资格失败 | 当前材料无法检验所设机制 | 已发现真实用户/MAS 的研究 gap |

Day 3 的 gate 是检查实现、数据和预算是否足以解释比较，不是观察测试显著性后决定是否继续。

---

## 11. 十天执行安排与逐日验收

> 全部日期按 America/Chicago 的项目工作日安排。计划不代表自动执行，也不承诺固定时长内必然获得正结果。

| 时间 | 任务 | 当日必须留下的产物 | 验收条件 |
|---|---|---|---|
| Day 0 · 10/16 | 在原 FoodPath 仓库切换为完整版 EGPR | 本 README、配置草案、来源记录 | 状态明确为计划，无伪造结果 |
| Day 1 · 10/17 | 读取当前仓库、核对历史资产、完成有限数据资格与分组 | source/data manifests、资格报告、split 文件 | 来源可追踪；unknown/否定分开；隐藏标签不泄漏 |
| Day 2 · 10/18 | 实现共同状态、评分器、B1/B2、EGPR 界限与更新；核对 B3 | 最小可执行核心、E0 单元测试、基线映射 | 完整重算一致；必要证据不误剪；final guard 能回退 |
| Day 3 · 10/19 | 跑 E1；在开发集验证完整 MAS；估价并冻结主协议 | offline report、development gate、models/prices、frozen config | 界限来源可解释；完整流程可运行；预算合法可用 |
| Day 4 · 10/20 | 运行 E2 和主模型 B2/P 成对主实验 | 冻结状态银行、成对轨迹、账本 | 同状态公平；主队列不调参 |
| Day 5 · 10/21 | 完成主模型其余 B0–B4 及 2×2 | 主表原始结果、消融结果 | 核心强基线全部保留，失败不删除 |
| Day 6 · 10/22 | 第二模型核心配对，预设预算敏感性 | 第二模型结果、质量–成本曲线数据 | 同一任务/预算规则；不得挑模型结果 |
| Day 7 · 10/23 | 第二模型剩余对照、架构诊断、预先限定跨领域扩展 | 完成状态表、扩展报告或未执行原因 | 不临时替换数据；普通解释受到检查 |
| Day 8 · 10/24 | 冻结数据分析，做分组 CI、错误和 break-even 分析 | summary、CI、逐组表、失败分类 | 原始轨迹到主表可追踪，统计口径一致 |
| Day 9 · 10/25 | 围绕实际证据写方法、实验、边界和复现附录 | 正文草稿、图表、方法伪代码、主张矩阵 | 每个贡献都有对应结果或降级说明 |
| Day 10 · 10/26 | 可复现检查、引用、匿名化、最终打包 | 最终报告、可编辑源码/代码包、复现命令 | 无泄密、无未实现命令冒充可运行、无未测量结果 |

若时间不足，停止扩展新领域和额外参数 sweep，优先完成 B2/P、B3 与 2×2 的解释性证据。**不削减 EGPR 方法模块，不删除强基线后仍声称完整版验证。** 实际未执行项在完成状态表中公开标注。

---

## 12. 实现工作包、目录与可复现产物

### 12.1 原仓库中的目标入口

下列是迁移后的目标路径，不表示已验证 GitHub 上的当前内容：

```text
foodpath-mas-uq/
├── README.md                              # 完整版 EGPR 实验计划
├── AGENTS.md                              # 保留既有规则，更新研究方向指令
├── configs/egpr/experiment_plan.yaml       # 计划配置；付费调用关闭
├── docs/egpr/
│   ├── RESEARCH_DIRECTIVE.md               # 当前研究任务，不再执行旧路线
│   ├── CITATION_PROVENANCE.md              # 继承来源及核查边界
│   └── MIGRATION.md                        # 替换范围及历史记录位置
├── experiments/RESEARCH_STATE.md           # 当前状态指向 EGPR
├── paper/food-assistant-proposal/          # 保留旧 proposal，入口明确标为历史
└── archive/pre-egpr/<旧提交>/              # 被替换的活动文档原件
```

不复制独立仓库的 `publish_github.py`，不覆盖应用源码、数据、`.env`、依赖文件或历史实验结果。先读取既有代码，再将下列工作包映射到实际模块，不为了目录整齐重构正常系统。

`src/egpr`、实验 runner、solver、dataset adapter 与结果表**尚未创建或实现**。下面是未来开发工作包，不是已完成的代码：

| 工作包 | 目标模块 | 输入→输出与必须测试的内容 |
|---|---|---|
| WP1 数据适配 | `data_adapter / schema / split` | 原来源→带作用域的任务、来源图与冻结分组 |
| WP2 共同环境 | `environment / user_adapter / guard / scorer` | 公开行动→合法反馈；隐藏世界仅用于模拟器/评分 |
| WP3 共用决策 | `belief / utility / candidate_builder / voi` | 同状态→候选与相同目标下的 VOI |
| WP4 EGPR | `bounds / certificates / dependency_update / controller` | 界限、版本依赖、回退与完整策略 |
| WP5 对照 | `baselines / ablations` | B0–B4、D0、A1 与 exact oracle |
| WP6 执行 | `gateway / ledger / scheduler / replay` | 哈希复用、成对队列、预算停止、全轨迹 |
| WP7 分析 | `metrics / grouped_bootstrap / reports` | 原始日志→主表、区间与失败归因 |

冻结后每次运行保存 `code_commit / config_hash / dataset_hash / source_snapshot_hash / model_snapshot / seed / policy / budget / provider_request_id`。运行产物使用有版本的目录，不能覆盖旧结果。

最小交付包括：`data_qualification`、`test_results`、`baseline_mapping`、`frozen_manifest`、`raw_runs`、`request_ledger`、`paired_results`、`grouped_ci`、`failure_cases`、`completion_status`。大文件与受限数据可保存在用户原有存储；原仓库只提交有许可的必要脚本、索引、脱敏摘要和复现说明。

### 12.2 执行与迁移边界

本 README 不提供尚未实现的 EGPR runner 命令。执行者应先读取仓库中的 `AGENTS.md`、研究指令、实际代码和测试，再给出真实可运行的命令及开发 gate。

迁移只更新当前研究入口与实验计划。GitHub 更新成功必须以真实提交和远程 `HEAD` 核验为准；仅拥有本地替换文件不表示已经提交。旧 proposal 的正文/PDF/源码包保留为历史快照；在开始写 EGPR 论文时另行依据实测结果更新，不把原文中的旧候选或旧效果照搬为 EGPR 贡献。


---

## 13. 相关工作与引用边界

下列来源表继承自上一版实验计划；本次路线迁移没有重新核查网页或作者代码。完整核查范围见 [docs/egpr/CITATION_PROVENANCE.md](docs/egpr/CITATION_PROVENANCE.md)。定位原文不等于复现作者代码或确认不存在其他相近工作。

| 编号 | 来源 | 对本项目的约束 |
|---|---|---|
| R1 | [SAGE-Agent: Structured Uncertainty guided Clarification for LLM Agents](https://arxiv.org/html/2511.08798v2) | 参数级结构不确定性、EVPI 与问题冗余已有直接先例 |
| R2 | [REVOIR: Rational Clarification by Assistive Agents via Value-of-Information Reasoning](https://arxiv.org/html/2609.37588v1) | 完整计划收益、澄清成本和增量 belief 更新不能当作天然区别 |
| R3 | [Value of Information: A Framework for Human–Agent Communication](https://aclanthology.org/2026.acl-long.1987/) | 任务收益与交互成本的权衡不是新的决策原则 |
| R4 | [GPS: Graph-guided Proactive Information Seeking in Large Language Models](https://proceedings.iclr.cc/paper_files/paper/2026/hash/1f49b7fbd7c7afc52c1db0d4ed1a338d-Abstract-Conference.html) | 条件结构和澄清剪枝已有先例；需核对实际算法而非仅名称 |
| R5 | [Ask-before-Plan: Proactive Language Agents for Real-World Planning](https://aclanthology.org/2024.findings-emnlp.636/) | 澄清、工具交互与完整规划的连接已有任务和方法 |
| R6 | [ConditionalQA](https://aclanthology.org/2022.acl-long.253/) | 答案与适用条件可以评价，但不自动识别交互收益 |
| R7 | [InSCIt](https://aclanthology.org/2023.tacl-1.27/) | 多种合法回应及参考标签不等于行动因果价值 |
| R8 | [Optimal Value of Information in Graphical Models — author record](https://las.inf.ethz.ch/bibtexbrowser.php?bib=laspub.bib&key=krause09optimal) | 结构化 VOI 的计算和复杂性有成熟研究；不能重命名为新理论 |
| R9 | [MAC: A Multi-Agent Framework for Interactive User Clarification](https://aclanthology.org/2026.iwsds-1.1/) | 多 agent 协调澄清已有直接相关工作；MAC 与电商 MACS 不混为一篇 |
| R10 | [Clarify the User or Verify the World?](https://arxiv.org/abs/2609.32255) | 用户澄清和世界验证路由不单独作为创新 |

本次只使用既有 Git 仓库的常规提交与非强制推送，不再使用新建仓库 API。

本项目的 SAGE 相关引用指上述 **SAGE-Agent**，不要与用户另一研究项目的 SAGE entropy estimator 混淆。之前讨论过但本次没有核验的额外论文不用于支撑新颖性结论。

---

## 14. 最终完成检查表

- [ ] 旧资产与来源版本核对；案例、分组及预算状态不是沿用未核实的历史数字。
- [ ] 完整版 M1–M5 实现，普通 baseline 同样拥有检查、修订与恢复。
- [ ] 证据义务、unknown/否定、冲突、相关性和动态候选失效测试通过。
- [ ] B2、B3 和 2×2 消融完成，已有技术贡献与 EGPR 额外收益被区分。
- [ ] 同状态回放与完整端到端评估分开；构图和证书成本全部计入。
- [ ] 按独立来源组报告区间、失败、缺测、成本与未解决条件。
- [ ] 第二模型与扩展实验按预定顺序执行，未完成项如实标记。
- [ ] 没有把非显著差异当作非劣效，没有把离线标签当作实际获得食物。
- [ ] 所有主张标为未验证、有限支持、被否定或得到支持；没有预设正结论。
- [ ] 私有仓库和匿名提交材料分开，无密钥、个人数据、未授权源码或第三方全文。

**最终目标不是让一个更复杂的系统看起来更好，而是明确：完整版 EGPR 的筛选和更新机制，在什么条件下比最强普通实现更有价值，以及在什么条件下没有价值。**
