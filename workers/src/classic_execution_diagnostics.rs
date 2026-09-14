//! Separate-build allocation and execution observations of the facade call.
#[path = "allocation_meter.rs"]
mod allocation_meter;
#[cfg(feature = "classic-execution-diagnostics")]
use emuella_j2k_codestream::observe_lossless_encode;
use serde_json::{Value, json};

#[cfg(feature = "classic-execution-diagnostics")]
pub fn encode<T>(call: impl FnOnce() -> T) -> (T, Value, u64) {
    let baseline = allocation_meter::reset();
    let start = std::time::Instant::now();
    let (result, d) = observe_lossless_encode(call);
    let facade_ns = start.elapsed().as_nanos() as u64;
    let allocation_peak = allocation_meter::peak_since(baseline);
    macro_rules! distribution {
        ($x:expr) => { json!({"log2_ns_bins":$x.bins.as_slice(), "count":$x.count,
            "sum_ns":$x.sum_ns as u64,"min_ns":$x.min_ns as u64,"max_ns":$x.max_ns as u64}) };
    }
    let t = &d.timings;
    (
        result,
        json!({
            "boundary":"facade_encode_with_separate_build_instrumentation",
            "allocation_peak_additional_requested_bytes":allocation_peak,
            "allocation_includes_output_and_reallocation_overlap":true,
            "blocks":distribution!(d.blocks),"batch_tails":distribution!(d.batch_tails),
            "batches":d.batches,"peak_active_blocks":d.peak_active_blocks,
            "active_block_ns":d.active_block_ns as u64,"any_block_active_ns":d.any_block_active_ns as u64,
            "dispatch_to_first_start_ns":d.dispatch_to_first_start_ns as u64,
            "last_finish_to_join_ns":d.last_finish_to_join_ns as u64,
            "batch_dispatch_join_ns":d.batch_dispatch_join_ns as u64,
            "ordered_append_ns":d.ordered_append_ns as u64,"aggregation_ns":d.aggregation_ns as u64,
            "retained_scratch_bytes":d.retained_scratch_bytes,
            "retained_result_capacity_bytes":d.retained_result_capacity_bytes,
            "retained_collector_capacity_bytes":d.retained_collector_capacity_bytes,
            "slot_metadata_bytes":d.slot_metadata_bytes,"endpoint_capacity_bytes":d.endpoint_capacity_bytes,
            "blocks_with_retained_packed_storage":d.blocks_with_retained_packed_storage,
            "blocks_without_packed_storage":d.blocks_without_packed_storage,
            "effective_workers":d.execution.effective_workers,
            "participating_workers":d.execution.participating_workers,
            "max_batch_blocks":d.execution.max_batch_blocks,
            "stages_ns":{"total":t.total_ns as u64,"conversion_level_shift_rct":t.conversion_level_shift_rct_ns as u64,
                "forward_dwt":t.forward_dwt_ns as u64,"block_preparation":t.block_preparation_ns as u64,
                "tier1_invocation":t.tier1_ns as u64,"packet_headers":t.packet_headers_ns as u64,
                "assembly":t.assembly_ns as u64},
            "stage_boundary_note":"Serial bypass tier1_invocation includes preparation and appends. Block durations include the existing Tier-1 call and internal preparation, with histogram aggregation afterwards. Parallel duration brackets include geometry; invocation/join is not pure kernel time.",
            "overhead_note":"Clock reads, post-join endpoint aggregation, profiled bookkeeping and atomic allocation metering perturb execution. No headline samples. Retained capacities exclude transient growth, which the separate allocation peak conservatively includes."
        }),
        facade_ns,
    )
}

#[cfg(feature = "classic-allocation-diagnostics")]
pub fn allocation<T>(call: impl FnOnce() -> T) -> (T, Value, u64) {
    let baseline = allocation_meter::reset();
    let start = std::time::Instant::now();
    let result = call();
    let ns = start.elapsed().as_nanos() as u64;
    let peak = allocation_meter::peak_since(baseline);
    (
        result,
        json!({"allocation_peak_additional_requested_bytes":peak,
        "includes_output_and_reallocation_overlap":true,
        "boundary":"facade_encode_allocation_only_no_block_observer",
        "overhead_note":"Atomic allocation metering perturbs this separate resource process; samples_ns remains empty. Peak is requested allocation, not RSS."}),
        ns,
    )
}
