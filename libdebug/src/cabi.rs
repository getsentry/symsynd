//! Public C ABI
//!
//! This exposes some of the functionality of the crate as a C ABI.
use std::mem;
use std::ptr;
use std::panic;
use std::path::Path;
use std::ffi::{CStr, OsStr};
use std::os::unix::ffi::OsStrExt;
use std::os::raw::{c_int, c_char};
use mach_object::{get_arch_name_from_types, get_arch_from_flag};

use read::DebugInfo;
use error::{Error, Result};

use uuid::Uuid;

#[derive(Debug)]
#[repr(C)]
pub struct CError {
    pub message: *const u8,
    pub failed: c_int,
    pub code: c_int,
}

#[repr(C)]
pub struct StrSlice {
    len: usize,
    buf: *const u8,
}

#[repr(C)]
pub struct CpuType {
    cputype: c_int,
    cpusubtype: c_int,
}

impl StrSlice {
    pub unsafe fn new(s: &str) -> StrSlice {
        StrSlice {
            len: s.len(),
            buf: s.as_ptr(),
        }
    }
}

#[repr(C)]
pub struct CVariant {
    cpu_name: StrSlice,
    uuid: Uuid,
    name: StrSlice,
    vmaddr: u64,
    vmsize: u64,
}

fn get_error_code(err: &Error) -> c_int {
    match err {
        &Error::Internal => 1,
        &Error::NoSuchArch => 2,
        &Error::NoSuchSection => 3,
        &Error::NoSuchAttribute => 4,
        &Error::MachObject(..) => 5,
        &Error::Io(..) => 6,
        &Error::Dwarf(..) => 7,
    }
}

fn resultbox<T>(val: T) -> Result<*mut T> {
    Ok(Box::into_raw(Box::new(val)))
}

unsafe fn notify_err(err: Error, err_out: *mut CError) {
    if !err_out.is_null() {
        let s = format!("{}\x00", err);
        (*err_out).failed = 1;
        (*err_out).message = Box::into_raw(s.into_boxed_str()) as *mut u8;
        (*err_out).code = get_error_code(&err);
    }
}

unsafe fn landingpad<F: FnOnce() -> Result<T> + panic::UnwindSafe, T>(
    f: F, err_out: *mut CError) -> T
{
    if let Ok(rv) = panic::catch_unwind(f) {
        rv.map_err(|err| notify_err(err, err_out)).unwrap_or(mem::zeroed())
    } else {
        notify_err(Error::Internal, err_out);
        mem::zeroed()
    }
}

macro_rules! export (
    (
        $(#[$attr:meta])*
        fn $name:ident($($aname:ident: $aty:ty),*) -> Result<$rv:ty> $body:block
    ) => (
        $(#[$attr])*
        #[no_mangle]
        pub unsafe extern "C" fn $name($($aname: $aty,)* err_out: *mut CError) -> $rv
        {
            landingpad(panic::AssertUnwindSafe(|| $body), err_out)
        }
    );
    (
        $(#[$attr:meta])*
        fn $name:ident($($aname:ident: $aty:ty),*) $body:block
    ) => {
        $(#[$attr])*
        #[no_mangle]
        pub unsafe extern "C" fn $name($($aname: $aty,)*)
        {
            // this silences panics and stuff
            landingpad(panic::AssertUnwindSafe(|| { $body; Ok(0 as c_int)}), ptr::null_mut());
        }
    }
);

export!(
    /// Opens debug info from a given path.
    fn debug_info_open_path(path: *const c_char) -> Result<*mut DebugInfo<'static>>
    {
        resultbox(DebugInfo::open_path(OsStr::from_bytes(CStr::from_ptr(path).to_bytes()))?)
    }
);

export!(
    /// Frees open debug info.
    fn debug_info_free(di: *mut DebugInfo)
    {
        if !di.is_null() {
            Box::from_raw(di);
        }
    }
);

export!(
    /// Gets a compilation dir for a given filename.
    fn debug_info_get_compilation_dir(di: *const DebugInfo,
                                      cpu_name: *const c_char,
                                      filename: *const c_char) -> Result<*const c_char>
    {
        Ok((*di).get_compilation_dir_cstr(
            CStr::from_ptr(cpu_name).to_str().unwrap(),
            Path::new(OsStr::from_bytes(CStr::from_ptr(filename).to_bytes())))?.as_ptr())
    }
);

export!(
    /// Gets the variants in the debug symbol file
    fn debug_info_get_variants(di: *const DebugInfo,
                               variants_count: *mut c_int) -> Result<*mut CVariant>
    {
        let rv: Vec<_> = (*di).get_variants()?.into_iter().map(|var| {
            CVariant {
                cpu_name: StrSlice::new(var.cpu_name),
                uuid: var.uuid,
                name: StrSlice::new(var.name),
                vmaddr: var.vmaddr,
                vmsize: var.vmsize,
            }
        }).collect();
        *variants_count = rv.len() as c_int;
        Ok(Box::into_raw(rv.into_boxed_slice()) as *mut CVariant)
    }
);

export!(
    /// Free allocated variants
    fn debug_free_variants(variants: *mut CVariant) {
        if !variants.is_null() {
            Box::from_raw(variants);
        }
    }
);

export!(
    /// Free an allocated buffer.
    fn debug_buffer_free(buf: *mut u8) {
        if !buf.is_null() {
            Box::from_raw(buf);
        }
    }
);

export!(
    /// Get the CPU name from a type tuple.
    fn debug_get_cpu_name(cputype: c_int, cpusubtype: c_int) -> Result<StrSlice> {
        let arch = get_arch_name_from_types(
            cputype as i32, cpusubtype as i32).ok_or(Error::NoSuchArch)?;
        Ok(StrSlice::new(arch))
    }
);

export!(
    /// Get a type tuple from a CPU name.
    fn debug_get_cpu_type(cpu_name: *const c_char) -> Result<CpuType> {
        if_chain! {
            if let Ok(cpu_name) = CStr::from_ptr(cpu_name).to_str();
            if let Some(tup) = get_arch_from_flag(cpu_name);
            then {
                Ok(CpuType {
                    cputype: tup.0 as c_int,
                    cpusubtype: tup.1 as c_int,
                })
            } else {
                Err(Error::NoSuchArch)
            }
        }
    }
);
