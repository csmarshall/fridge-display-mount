# Prompt to start the new session

Paste everything below the line into a fresh Claude Code session run from
`~/work/claude/fridge-strut-mount`.

---

I'm designing a floor-standing mount that carries a Waveshare 23.8" touch monitor on the side
panel of my fridge, for a household chore board. Read `CLAUDE.md` for the invariants, `BRIEF.md`
for the design and the numbers behind it, and `reference/README.md` for what evidence exists.

This supersedes a completed hook design. That project is tagged `hook-final` in
`csmarshall/fridge-magnet-mount` and its working directory is
`~/work/claude/chore-tracker-mount`. It is finished and validated — read from it freely, but do
not assume anything in it still applies. The load path is different now.

**Before writing code, tell me what you think is wrong or unresolved in the brief.** The previous
project's worst failures all came from an invariant that was written down once and then quietly
outlived its reasoning. I would rather argue about it now.

Then the work, roughly in this order:

1. **The bent foot** is the real design problem and the only part being manufactured. It ties both
   strut bases, slides under the fridge, and gets wedged. It needs a parametric generator that
   validates before it writes, in the shape of the previous project's — `audit_dxf.py` and
   `bracket_common.py` are already here for that.

2. **The magnet resize.** The previous magnets are over-specified by about 49x and cost $191.
   `reference/inherited-magnet_primer.pdf` already works out why vendor ratings mislead; don't
   redo that, use it. Keeping a 5/16"-18 male stud would let the whole fastener analysis carry
   over unchanged.

3. **Check the plate can be reused unmodified** before assuming it. Its four Ø8.5 holes at 246 mm
   centres look like they land exactly on the struts, but they were sized for a magnet stud, not a
   channel bolt, and the loads have changed.

4. **The five open questions in BRIEF.md §3** all need the actual appliance. Tell me exactly what
   to measure and how, in one list, early — don't discover them one at a time.

Two things about how I work: show me pictures rather than describing them, and if you're unsure
between options, build a sweep and let me pick by eye. And when something is an estimate, say so —
I would much rather have "derived, assumes a 6 mm lip" than a confident number.
