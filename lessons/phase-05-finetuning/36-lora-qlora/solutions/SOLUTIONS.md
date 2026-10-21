# Lesson 36 solution notes

With the conventional zero initialization for matrix `B`, the first adapter
delta is zero. The first gradient for `A` is also zero because backpropagation
passes through `B`, while `B` receives a nonzero gradient through `A x`.
After `B` moves, both matrices can receive gradients. The base matrix remains
frozen.

The merge identity is
`(W + (alpha/r) B A) x == W x + (alpha/r) B(Ax)` up to floating-point
rounding. Merge equivalence does not mean every runtime can safely merge into
the in-memory storage of a quantized base. For the checked QLoRA path, save the
adapter, reload the exact base revision at the intended nonquantized serving
precision, attach the adapter, merge there, evaluate again, and then package.

Target module names are implementation-specific. A plausible name that matches
a paper diagram is not enough; inspect `model.named_modules()`, freeze the
result with the experiment, and fail if any configured target resolves to zero
modules.
