// strap-l1 build script: compiles the C++ PoUW library via cmake

use std::path::PathBuf;

fn main() {
    let dst = cmake::Config::new("src/pouw")
        .build_target("strap-pouw")
        .build();

    let build_dir = dst.join("build");
    let link_path = build_dir.display().to_string();

    println!("cargo:rustc-link-search=native={}", link_path);
    println!("cargo:rustc-link-lib=static=strap-pouw");
    println!("cargo:rustc-link-lib=dylib=ssl");
    println!("cargo:rustc-link-lib=dylib=crypto");

    println!("cargo:rerun-if-changed=src/pouw/strap-pouw.cpp");
    println!("cargo:rerun-if-changed=src/pouw/CMakeLists.txt");
}
