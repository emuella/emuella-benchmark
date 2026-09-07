# Factual multi-run series

<code>points</code> extracts completed stored runs into JSON, while
<code>series</code> creates a standalone HTML report with SVG scatterplots. Both
commands first apply <code>compare::validate_run</code>; an invalid stored run or
unsupported schema is rejected.

    emuella-benchmark points run-a run-b factual-points.json
    emuella-benchmark series factual-series.html run-a run-b

The extract records the exact run, implementation/source/build, input digest and
provenance, configuration, protocol, machine and harness identities alongside
each successful point. Timing is the mean of independent batch means. For encode
cases, actual bpp is mean output bytes times 8 divided by input width times
height. It also records aggregate MSE, PSNR, observed peak RSS and its
observation count. A null PSNR means an exact output with infinite PSNR; bpp is
null for decode.

Every case/run remains in coverage, including unsupported, unattainable-rate,
failed, timed-out and invalid batches. A metric point exists only when all
batches for that case succeeded. Diagnostic runs are retained as coverage but
excluded from plotted timing points.

Rate/distortion grouping is intentionally strict. It requires the input and
reference identities, image and operation, output semantics, thread budget,
protocol, environment tags, machine and harness to match. It retains every
semantic setting, including a codec coding family. It removes only the exact
top-level setting names <code>target_bpp</code>, <code>compression_ratio</code>
and <code>qstep</code>, so rate requests can appear as points in one group. A
changed setting such as <code>coding_family</code>,
<code>progression_order</code> or <code>tile_size</code> creates a different
group.

Progress groups additionally keep the complete setting map and implementation.
They list source identity against measured time only for that exact grouped
workload. Neither JSON nor HTML interpolates rate/distortion curves, matches
quality points, ranks implementations across a population, or makes unlike
machines or settings comparable.
