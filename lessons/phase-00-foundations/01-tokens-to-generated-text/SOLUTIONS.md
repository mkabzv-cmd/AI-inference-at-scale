# Lesson 01 solutions

## Predictions

For `B=1`, `S=7`, `H=2`, and `V=50257`:

- `input_ids`: `[1, 7]`
- hidden states: `[1, 7, 2]`
- logits: `[1, 7, 50257]`
- next-token scores: `logits[:, -1, :]`, shape `[1, 50257]`
- first cached decode input: one new token, shape `[1, 1]`
- temperature changes selection probabilities, not learned knowledge.

## Exercises

1. IDs/mask `[4,128]`; hidden states `[4,128,4096]`; logits
   `[4,128,32000]`; final-position logits `[4,32000]`; selected IDs `[4,1]`.
2. Validate the ID is within the vocabulary, then stop after appending it:

   ```python
   if args.stop_token_id is not None and token_id == args.stop_token_id:
       stopped_reason = "requested_stop_token"
       break
   ```

3. Lower temperature usually concentrates probability among leading
   candidates. Higher temperature spreads mass. Compare probabilities, not
   merely one random output.
4. Without cache, concatenate the selected token to all IDs and forward the
   entire `[1,S+t]` sequence. Input length grows each iteration and old K/V
   projections are recomputed.
5. Each sequence has a different cache length and may finish at a different
   time. An engine must place caches, form compatible batches, avoid padding
   waste, admit new work, and reclaim blocks as requests finish.
