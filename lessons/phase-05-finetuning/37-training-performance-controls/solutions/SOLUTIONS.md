# Lesson 37 solution notes

The four checked candidates all expose 4,096 token slots to each optimizer
update: `microbatch × accumulation × sequence length`. That equality does not
prove equal useful tokens because padding can differ, nor does it prove equal
examples when packing is introduced. Real evidence must report nonpadding
tokens and supervised tokens in addition to slot capacity.

The labeled analyzer fixture has multiple Pareto-efficient choices. The
larger-microbatch treatment trades memory for throughput; checkpointing trades
throughput for memory. The dominated fixture is worse on all three declared
axes. A single weighted winner is intentionally absent because weights should
come from a capacity or cost constraint declared before results are inspected.

The deliberate failure changes the dataset fingerprint, optimizer-step budget,
and token slots. Its attractive throughput cannot be compared with the
baseline. The correction is to restore the frozen invariants or create a
separately named study whose question explicitly includes the changed
optimization problem.
