use std::alloc::{GlobalAlloc, Layout, System};
use std::sync::atomic::{AtomicUsize, Ordering::SeqCst};
struct Meter;
static LIVE: AtomicUsize = AtomicUsize::new(0);
static PEAK: AtomicUsize = AtomicUsize::new(0);
fn add(n: usize) {
    let live = LIVE.fetch_add(n, SeqCst) + n;
    PEAK.fetch_max(live, SeqCst);
}
// Diagnostic-only allocator. Every pointer and layout is forwarded unchanged to
// System. Reallocation conservatively counts old and new requests concurrently.
unsafe impl GlobalAlloc for Meter {
    unsafe fn alloc(&self, l: Layout) -> *mut u8 {
        let p = unsafe { System.alloc(l) };
        if !p.is_null() {
            add(l.size());
        }
        p
    }
    unsafe fn alloc_zeroed(&self, l: Layout) -> *mut u8 {
        let p = unsafe { System.alloc_zeroed(l) };
        if !p.is_null() {
            add(l.size());
        }
        p
    }
    unsafe fn dealloc(&self, p: *mut u8, l: Layout) {
        unsafe { System.dealloc(p, l) };
        LIVE.fetch_sub(l.size(), SeqCst);
    }
    unsafe fn realloc(&self, p: *mut u8, l: Layout, n: usize) -> *mut u8 {
        add(n);
        let q = unsafe { System.realloc(p, l, n) };
        LIVE.fetch_sub(if q.is_null() { n } else { l.size() }, SeqCst);
        q
    }
}
#[global_allocator]
static ALLOC: Meter = Meter;
pub fn reset() -> usize {
    let baseline = LIVE.load(SeqCst);
    PEAK.store(baseline, SeqCst);
    baseline
}
pub fn peak_since(baseline: usize) -> usize {
    PEAK.load(SeqCst).saturating_sub(baseline)
}
