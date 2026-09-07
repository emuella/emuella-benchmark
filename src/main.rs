use emuella_benchmark::{Result, compare, contract::*, read_json, report, runner, series};
use std::{io::Write, path::Path};

fn load_run(path: &str) -> Result<Run> {
    let path = Path::new(path);
    read_json(&if path.is_dir() {
        path.join("run.json")
    } else {
        path.to_owned()
    })
}
fn usage() -> &'static str {
    "Usage:\n  emuella-benchmark run EXPERIMENT.json WORKER.json NEW_OUTPUT_DIR\n  emuella-benchmark pair EXPERIMENT.json BASELINE_WORKER.json CANDIDATE_WORKER.json NEW_OUTPUT_DIR\n  emuella-benchmark compare BASELINE_RUN CANDIDATE_RUN [--json]\n  emuella-benchmark report BASELINE_RUN CANDIDATE_RUN NEW_REPORT.html\n  emuella-benchmark series NEW_REPORT.html RUN...\n  emuella-benchmark points RUN... NEW_POINTS.json\n  emuella-benchmark diagnose EXPERIMENT.json WORKER.json CASE_ID NEW_OUTPUT_DIR\n\nWorker executable, args and artefacts are declared in WORKER.json. Runs never overwrite existing output directories. Compare exit codes: 0 improved/equivalent; 2 regression; 3 inconclusive; 4 invalid/not-comparable. Errors: 1."
}
fn execute() -> Result<i32> {
    let args: Vec<_> = std::env::args().skip(1).collect();
    match args.first().map(String::as_str) {
        Some("run") if args.len() == 4 => {
            let run = runner::run(
                &read_json(Path::new(&args[1]))?,
                &read_json(Path::new(&args[2]))?,
                Path::new(&args[3]),
                false,
            )?;
            println!("{}: {} batches", run.run_id, run.batches.len());
            Ok(if run.batches.iter().all(|b| b.status == BatchStatus::Ok) {
                0
            } else {
                4
            })
        }
        Some("pair") if args.len() == 5 => {
            let (a, b) = runner::run_pair(
                &read_json(Path::new(&args[1]))?,
                &read_json(Path::new(&args[2]))?,
                &read_json(Path::new(&args[3]))?,
                Path::new(&args[4]),
            )?;
            let comparison = compare::compare(&a, &b);
            runner::write_json_new(&Path::new(&args[4]).join("comparison.json"), &comparison)?;
            println!("{}", report::text(&comparison));
            Ok(exit_verdict(&comparison.verdict))
        }
        Some("compare") if args.len() == 3 || (args.len() == 4 && args[3] == "--json") => {
            let comparison = compare::compare(&load_run(&args[1])?, &load_run(&args[2])?);
            if args.len() == 4 {
                println!("{}", serde_json::to_string_pretty(&comparison)?);
            } else {
                print!("{}", report::text(&comparison));
            }
            Ok(exit_verdict(&comparison.verdict))
        }
        Some("report") if args.len() == 4 => {
            let comparison = compare::compare(&load_run(&args[1])?, &load_run(&args[2])?);
            let mut file = std::fs::OpenOptions::new()
                .create_new(true)
                .write(true)
                .open(&args[3])?;
            file.write_all(report::html(&comparison).as_bytes())?;
            file.sync_all()?;
            println!("{}", args[3]);
            Ok(0)
        }
        Some("series") if args.len() >= 3 => {
            let runs = args[2..]
                .iter()
                .map(|path| load_run(path))
                .collect::<Result<Vec<_>>>()?;
            let report = series::extract(&runs)?;
            let mut file = std::fs::OpenOptions::new()
                .create_new(true)
                .write(true)
                .open(&args[1])?;
            file.write_all(series::html(&report).as_bytes())?;
            file.sync_all()?;
            println!("{}", args[1]);
            Ok(0)
        }
        Some("points") if args.len() >= 3 => {
            let output = args.last().expect("points output");
            let runs = args[1..args.len() - 1]
                .iter()
                .map(|path| load_run(path))
                .collect::<Result<Vec<_>>>()?;
            runner::write_json_new(Path::new(output), &series::extract(&runs)?)?;
            println!("{output}");
            Ok(0)
        }
        Some("diagnose") if args.len() == 5 => {
            let mut experiment: Experiment = read_json(Path::new(&args[1]))?;
            experiment.validate()?;
            experiment.cases.retain(|x| x.id == args[3]);
            if experiment.cases.is_empty() {
                return Err("selected case does not exist".into());
            }
            let run = runner::run(
                &experiment,
                &read_json(Path::new(&args[2]))?,
                Path::new(&args[4]),
                true,
            )?;
            println!(
                "{}: diagnostic run; excluded from timing inference",
                run.run_id
            );
            Ok(if run.batches.iter().all(|b| b.status == BatchStatus::Ok) {
                0
            } else {
                4
            })
        }
        Some("--help" | "-h") | None => {
            println!("{}", usage());
            Ok(0)
        }
        _ => Err(usage().into()),
    }
}
fn exit_verdict(verdict: &compare::Verdict) -> i32 {
    use compare::Verdict::*;
    match verdict {
        Improved | Equivalent => 0,
        Regressed => 2,
        Inconclusive => 3,
        Invalid | NotComparable => 4,
    }
}
fn main() {
    match execute() {
        Ok(code) => std::process::exit(code),
        Err(error) => {
            eprintln!("error: {error}");
            std::process::exit(1);
        }
    }
}
