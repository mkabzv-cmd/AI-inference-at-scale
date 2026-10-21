# Lesson 35 solution notes

The CPU reference should end at exactly the same weight and loss whether it
runs continuously or resumes at optimizer step five. Four microbatches feed
each update, the initial updates are clipped, and the warmup/linear-decay
schedule is indexed by optimizer steps rather than microbatches.

The incompatible-resume drill must fail because changing accumulation changes
both examples per optimizer update and scheduler interpretation. A robust
training system fingerprints the complete effective configuration and dataset
manifest instead of loading a checkpoint merely because its tensor shapes fit.

For the real model, the assistant-only mask begins after
`apply_chat_template(..., add_generation_prompt=True)` for the system and user
messages. Prompt tokens remain visible through attention, but their labels are
`-100`. The response and template terminator are supervised. If the prompt
serialization is not an exact prefix of the complete serialization, the script
stops instead of guessing a mask.
