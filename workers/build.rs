fn main() {
    println!("cargo:rerun-if-changed=native/openjpeg.c");
    if std::env::var_os("CARGO_FEATURE_OPENJPEG").is_some() {
        let library = pkg_config::Config::new()
            .atleast_version("2.5")
            .probe("libopenjp2")
            .expect("OpenJPEG development headers and pkg-config libopenjp2 >= 2.5 required");
        let mut build = cc::Build::new();
        for path in &library.link_paths {
            println!("cargo:rustc-link-arg=-Wl,-rpath,{}", path.display());
        }
        build.file("native/openjpeg.c");
        for include in library.include_paths {
            build.include(include);
        }
        build.warnings(true).compile("benchmark_openjpeg");
    }
}
