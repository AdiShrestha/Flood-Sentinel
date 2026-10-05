# Domain review prompts

## Any empirical ML study
What is the observation and independent unit? Do labels precede modeling? Are group/entity/time splits disjoint? Was threshold selection validation-only? Are all seeds, failed runs, precision targets, intervals, effect sizes, multiplicity, calibration, and failures reported?

## Graph/topology
Are source edge directions, timestamps, labels, and candidate IDs traceable? Does the complex preserve boundary conventions and `B_k B_{k+1}=0`? Are 1-skeleton and filled complexes intentionally distinct? Do batching, pooling, normalization, and isolated nodes preserve the intended operator? Are topology-specific controls meaningful, and are baselines capacity/compute matched rather than merely named?

## Systems/efficiency
What exact device, software versions, driver, synchronization, input shape, warmup, batch, percentile, sustained interval, memory profiler, power sensor, and thermal state produced each number? Are claims bounded to this stack and workload? Is a fanless device tested after thermal steady state?

## Statistics and claims
Which test follows from pairing, clusters, distribution and sample size? Is the estimand compatible with the reported unit? Is a null result distinguished from equivalence? Does every claim have a figure/table and every result have a claim or limitation? Does an OOD shift represent deployment, and are subgroups and failure ceilings visible?

This checklist is a review aid; the gate does not pretend to infer mathematical semantics from words.

### Scientific sufficiency floors

Research requires at least 30 independent test groups and 10 observations per class, plus a prospectively justified stopping policy. A prose justification cannot override a numeric gate. Domain-specific designs outside this profile require a reviewed adapter and explicit limits.
