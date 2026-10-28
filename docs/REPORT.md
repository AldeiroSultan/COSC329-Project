# Bayesian Study Planner — Project Report

**COSC 329 · 2-person option** · Sultan, John

> Each section names the branch that fills it in. Delete these notes before submitting.

## 1. Overview
_(TI-00005)_ Problem, what the system does, how to run it.

## 2. Network structure & hand-crafted CPTs
_(MF-00001)_ Diagram (`docs/figures/network.png`), node table, every CPT with a
one-line justification of its numbers.

## 3. Data source / simulation
_(MF-00002)_ Why simulated, the generating functions, N, seed, parent-configuration
counts showing > 10 rows per learned parameter.

## 4. Learning CPTs with Laplace smoothing
_(MF-00003)_ The 4+ learned variables, the estimator formula, hand-crafted vs learned
comparison table (`docs/figures/cpt_comparison.png`), cross-check with pgmpy K2.

## 5. Inference task
_(MF-00004)_ Evidence variables, query variables, algorithm (Variable Elimination),
example posteriors.

## 6. Actions, utility & decision
_(MF-00004)_ The 4 actions and their effect model, utility table, EU formula,
any tuning and why.

## 7. Calendar integration
_(MF-00005)_ Google Calendar API flow, .ics fallback, safety rule for deleting events.

## 8. Results: different students → different actions
_(MF-00006)_ Scenario table (evidence, posteriors, EU per action, chosen action),
`docs/figures/expected_utility.png`, 14-day simulation for struggling vs advanced,
calendar screenshots.

## 9. Limitations & future work
_(TI-00005)_ e.g. mastery marginals treated as independent in the action model,
simulated rather than real data, action effects hand-set.
