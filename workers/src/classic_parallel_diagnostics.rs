//! Separate-build operation boundaries for external Linux task CPU observation.
//! No pool binding, spawn hook, codec warmup or estimator lives here.
use serde_json::{Value, json};
use std::{
    collections::BTreeMap,
    io::{BufRead, BufReader, Read, Write},
    os::unix::net::UnixStream,
    time::{Duration, Instant},
};

type Result<T> = std::result::Result<T, String>;
const SCHEMA: &str = "emuella-parallel-diagnostic-v1";
const ACK_LIMIT: u64 = 256;

pub fn admit(operation: &str, codec: &str, workers: u8) -> Result<()> {
    if !matches!(operation, "encode" | "decode") || codec != "emuella" || ![1, 8].contains(&workers)
    {
        return Err(
            "parallel diagnostics require one/eight-worker Emuella encode or decode".into(),
        );
    }
    Ok(())
}

fn thread_id() -> Result<u32> {
    let path = std::fs::read_link("/proc/thread-self").map_err(|e| e.to_string())?;
    path.file_name()
        .and_then(|name| name.to_str())
        .and_then(|name| name.parse().ok())
        .ok_or_else(|| "cannot identify Linux thread".into())
}

fn cpu_snapshot(tids: &[u32]) -> Result<BTreeMap<u32, u64>> {
    tids.iter()
        .map(|&tid| {
            let tid = libc::clockid_t::try_from(tid).map_err(|e| e.to_string())?;
            if tid <= 0 {
                return Err("invalid CPU clock thread identity".into());
            }
            // Linux's per-thread CPUCLOCK_SCHED ABI: MAKE_THREAD_CPUCLOCK(tid, 2).
            // This thread-group-local clock refreshes running-task accounting;
            // external /proc schedstat reads are advisory and can lag execution.
            let clock = ((!tid) << 3) | 6;
            let mut stamp = libc::timespec {
                tv_sec: 0,
                tv_nsec: 0,
            };
            // SAFETY: stamp is writable and correctly aligned; clock_gettime
            // validates the integer clock ID, returning an error for a stale TID.
            if unsafe { libc::clock_gettime(clock, &mut stamp) } != 0 {
                return Err(format!(
                    "thread CPU clock {tid}: {}",
                    std::io::Error::last_os_error()
                ));
            }
            let seconds = u64::try_from(stamp.tv_sec).map_err(|e| e.to_string())?;
            let nanos = u64::try_from(stamp.tv_nsec).map_err(|e| e.to_string())?;
            if nanos >= 1_000_000_000 {
                return Err("invalid thread CPU clock nanoseconds".into());
            }
            let ns = seconds
                .checked_mul(1_000_000_000)
                .and_then(|v| v.checked_add(nanos))
                .ok_or("thread CPU clock overflow")?;
            Ok((tid as u32, ns))
        })
        .collect()
}

struct Session {
    socket: BufReader<UnixStream>,
    metadata: Value,
    thread_ids: Vec<u32>,
}
impl Session {
    fn open(operation: &str, workers: u8) -> Result<Self> {
        let pool_threads = rayon::current_num_threads();
        // Broadcast only discovers existing pool threads. The ordinary caller
        // remains outside the pool, as it is in the production worker.
        let pool_thread_ids = rayon::broadcast(|_| thread_id())
            .into_iter()
            .collect::<Result<Vec<_>>>()?;
        let mut unique = pool_thread_ids.clone();
        unique.sort_unstable();
        unique.dedup();
        if unique.len() != pool_threads
            || pool_threads != usize::from(workers)
            || unique.contains(&std::process::id())
        {
            return Err("parallel diagnostic pool identity mismatch".into());
        }
        let path = std::env::var_os("EMUELLA_PARALLEL_DIAGNOSTIC_SOCKET")
            .ok_or("missing EMUELLA_PARALLEL_DIAGNOSTIC_SOCKET")?;
        let socket = UnixStream::connect(path).map_err(|e| e.to_string())?;
        socket
            .set_read_timeout(Some(Duration::from_secs(120)))
            .map_err(|e| e.to_string())?;
        socket
            .set_write_timeout(Some(Duration::from_secs(120)))
            .map_err(|e| e.to_string())?;
        let thread_ids = std::iter::once(std::process::id())
            .chain(pool_thread_ids.iter().copied())
            .collect();
        Ok(Self {
            thread_ids,
            socket: BufReader::new(socket),
            metadata: json!({"schema":SCHEMA,"pid":std::process::id(),"operation":operation,
                "requested_workers":workers,"pool_threads":pool_threads,"pool_thread_ids":pool_thread_ids}),
        })
    }

    fn exchange(&mut self, event: &str, ns: Option<u64>, cpu: Option<&Value>) -> Result<()> {
        let mut message = self.metadata.clone();
        message["event"] = json!(event);
        if let Some(ns) = ns {
            message["diagnostic_facade_ns"] = json!(ns);
        }
        if let Some(cpu) = cpu {
            for key in [
                "cpu_snapshot_span_ns",
                "thread_cpu_before_ns",
                "thread_cpu_after_ns",
            ] {
                message[key] = cpu[key].clone();
            }
        }
        serde_json::to_writer(self.socket.get_mut(), &message).map_err(|e| e.to_string())?;
        self.socket
            .get_mut()
            .write_all(b"\n")
            .map_err(|e| e.to_string())?;
        self.socket.get_mut().flush().map_err(|e| e.to_string())?;
        let mut line = Vec::new();
        (&mut self.socket)
            .take(ACK_LIMIT)
            .read_until(b'\n', &mut line)
            .map_err(|e| e.to_string())?;
        if line.last() != Some(&b'\n') || line.len() as u64 >= ACK_LIMIT {
            return Err("missing or oversized parallel diagnostic acknowledgement".into());
        }
        let ack: Value = serde_json::from_slice(&line).map_err(|e| e.to_string())?;
        if ack != json!({"ack":event}) {
            return Err("invalid parallel diagnostic acknowledgement".into());
        }
        Ok(())
    }
}

pub fn measure<T>(
    operation: &str,
    workers: u8,
    call: impl FnOnce() -> T,
) -> Result<(T, Value, u64)> {
    measure_session(Session::open(operation, workers)?, operation, call)
}

fn measure_session<T>(
    mut session: Session,
    operation: &str,
    call: impl FnOnce() -> T,
) -> Result<(T, Value, u64)> {
    // The controller snapshots placement while the caller is blocked here.
    session.exchange("begin", None, None)?;
    let cpu_span_start = Instant::now();
    let before = cpu_snapshot(&session.thread_ids)?;
    let start = Instant::now();
    let (result, execution) = if operation == "encode" {
        let (result, observation) = emuella_j2k_codestream::observe_lossless_encode(call);
        (result, Some(observation.execution))
    } else {
        (call(), None)
    };
    let ns = u64::try_from(start.elapsed().as_nanos()).map_err(|e| e.to_string())?;
    let after = cpu_snapshot(&session.thread_ids)?;
    let cpu_span_ns =
        u64::try_from(cpu_span_start.elapsed().as_nanos()).map_err(|e| e.to_string())?;
    if before
        .iter()
        .any(|(tid, ns)| after.get(tid).is_none_or(|end| end < ns))
    {
        return Err("thread CPU clock reversed or disappeared".into());
    }
    let cpu = json!({"cpu_snapshot_span_ns":cpu_span_ns,
        "thread_cpu_before_ns":before,"thread_cpu_after_ns":after});
    // Always close the observed operation, including a returned codec error.
    // Full stream/sample verification happens only after this acknowledgement.
    session.exchange("end", Some(ns), Some(&cpu))?;
    let mut diagnostic = session.metadata;
    for key in [
        "cpu_snapshot_span_ns",
        "thread_cpu_before_ns",
        "thread_cpu_after_ns",
    ] {
        diagnostic[key] = cpu[key].clone();
    }
    diagnostic["effective_workers"] = json!(execution.as_ref().map(|d| d.effective_workers));
    diagnostic["participating_workers"] =
        json!(execution.as_ref().map(|d| d.participating_workers));
    diagnostic["boundary"] = json!("facade_operation_before_exact_verification");
    diagnostic["overhead_note"] = json!(
        "Separate diagnostic process. Pool TID discovery and control handshakes are outside the facade timer. Encode observer clocks and bookkeeping perturb execution. Logical encoder participation does not prove simultaneous CPU execution. Thread CPUCLOCK_SCHED snapshots bracket the facade timer inside a wider measured span; subtract one outside-span allowance per tracked thread for an operation CPU lower bound. External /proc runtime samples are advisory and can lag execution; placement samples are not a strict execution trace. CPU snapshots and handshakes are outside the facade timer. samples_ns remains empty."
    );
    Ok((result, diagnostic, ns))
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::sync::{
        Arc,
        atomic::{AtomicBool, Ordering},
    };

    fn pair() -> (Session, BufReader<UnixStream>) {
        let (worker, controller) = UnixStream::pair().unwrap();
        worker
            .set_read_timeout(Some(Duration::from_secs(2)))
            .unwrap();
        controller
            .set_read_timeout(Some(Duration::from_secs(2)))
            .unwrap();
        (
            Session {
                socket: BufReader::new(worker),
                metadata: json!({"schema":SCHEMA}),
                thread_ids: vec![thread_id().unwrap()],
            },
            BufReader::new(controller),
        )
    }
    fn event(socket: &mut BufReader<UnixStream>) -> Value {
        let mut line = String::new();
        socket.read_line(&mut line).unwrap();
        serde_json::from_str(&line).unwrap()
    }
    fn ack(socket: &mut BufReader<UnixStream>, phase: &str) {
        writeln!(socket.get_mut(), "{}", json!({"ack":phase})).unwrap();
        socket.get_mut().flush().unwrap();
    }

    #[test]
    fn cpu_clock_snapshots_are_monotonic_for_same_thread_group() {
        let caller = thread_id().unwrap();
        let (send, receive) = std::sync::mpsc::channel();
        let (release, block) = std::sync::mpsc::channel();
        let worker = std::thread::spawn(move || {
            send.send(thread_id().unwrap()).unwrap();
            block.recv().unwrap();
        });
        let sibling = receive.recv().unwrap();
        let first = cpu_snapshot(&[caller, sibling]).unwrap();
        let mut total = 0_u64;
        for value in 0..100_000 {
            total = total.wrapping_add(std::hint::black_box(value));
        }
        std::hint::black_box(total);
        let second = cpu_snapshot(&[caller, sibling]).unwrap();
        assert!(second[&caller] > first[&caller]);
        assert!(second[&sibling] >= first[&sibling]);
        assert!(cpu_snapshot(&[0]).is_err());
        assert!(cpu_snapshot(&[u32::MAX]).is_err());
        release.send(()).unwrap();
        worker.join().unwrap();
    }

    #[test]
    fn admission_is_separate_and_bounded() {
        for operation in ["encode", "decode"] {
            for workers in [1, 8] {
                assert!(admit(operation, "emuella", workers).is_ok());
            }
            for workers in [0, 2, 4] {
                assert!(admit(operation, "emuella", workers).is_err());
            }
            assert!(admit(operation, "openjpeg", 1).is_err());
        }
        assert!(admit("prepare", "emuella", 1).is_err());
    }

    #[test]
    fn strict_acknowledgements_fail_closed() {
        for reply in [
            b"".as_slice(),
            b"ack\n",
            b"{\"ack\":\"end\"}\n",
            b"{\"ack\":\"begin\",\"extra\":1}\n",
            &[b'x'; 256],
        ] {
            let (mut session, mut controller) = pair();
            controller.get_mut().write_all(reply).unwrap();
            controller
                .get_mut()
                .shutdown(std::net::Shutdown::Write)
                .unwrap();
            assert!(session.exchange("begin", None, None).is_err());
        }
    }

    #[test]
    fn codec_error_still_closes_operation_before_return() {
        let (session, mut controller) = pair();
        let called = Arc::new(AtomicBool::new(false));
        let controller_called = called.clone();
        let control = std::thread::spawn(move || {
            assert_eq!(event(&mut controller)["event"], "begin");
            assert!(!controller_called.load(Ordering::SeqCst));
            ack(&mut controller, "begin");
            let end = event(&mut controller);
            assert_eq!(end["event"], "end");
            assert!(end["diagnostic_facade_ns"].is_u64());
            assert!(
                end["cpu_snapshot_span_ns"].as_u64().unwrap()
                    >= end["diagnostic_facade_ns"].as_u64().unwrap()
            );
            assert_eq!(end["thread_cpu_before_ns"].as_object().unwrap().len(), 1);
            assert_eq!(end["thread_cpu_after_ns"].as_object().unwrap().len(), 1);
            assert!(controller_called.load(Ordering::SeqCst));
            ack(&mut controller, "end");
        });
        let (result, diagnostic, _) = measure_session(session, "decode", || {
            called.store(true, Ordering::SeqCst);
            Err::<(), _>("codec failure")
        })
        .unwrap();
        assert_eq!(result, Err("codec failure"));
        assert!(diagnostic["effective_workers"].is_null());
        control.join().unwrap();
    }

    #[test]
    fn end_acknowledgement_is_required_before_return() {
        let (session, mut controller) = pair();
        let control = std::thread::spawn(move || {
            assert_eq!(event(&mut controller)["event"], "begin");
            ack(&mut controller, "begin");
            assert_eq!(event(&mut controller)["event"], "end");
            // Closing the controller is not a successful end acknowledgement.
        });
        assert!(measure_session(session, "decode", || ()).is_err());
        control.join().unwrap();
    }
}
