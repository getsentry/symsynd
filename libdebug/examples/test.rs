use std::path::Path;

extern crate libdebug;

fn main() {
    let di = libdebug::DebugInfo::open_path("/tmp/testapp").unwrap();
    println!("{}", di.get_compilation_dir("x86_64", Path::new("/tmp/test.c")).unwrap().display());

    let di = libdebug::DebugInfo::open_path("/Users/mitsuhiko/Library/Developer/Xcode/DerivedData/CrashProbe-cxjvjyopokfehmghwqautqxiotfs/Build/Products/Release-iphoneos/CrashProbeiOS.app.dSYM/Contents/Resources/DWARF/CrashProbeiOS").unwrap();
    println!("{}", di.get_compilation_dir("arm64", Path::new("/Users/mitsuhiko/Development/crashprobe/CrashProbe iOS/main.m")).unwrap().display());
}
